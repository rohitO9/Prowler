"""
Django management command to sync Azure AD users
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import requests

from api.v1.models.azure_ad import AzureADUserSync, AzureADUserProfile, AzureADAuditLog
from api.v1.utils.azure_ad_utils import AzureADUtils

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync users from Azure AD to local database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            help='Sync specific user by Azure AD ID'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Sync specific user by email'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sync all users from Azure AD'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing users'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )

    def handle(self, *args, **options):
        if not settings.AZURE_AD_ENABLED:
            raise CommandError('Azure AD is not enabled in settings')

        if not all([
            settings.AZURE_AD_CLIENT_ID,
            settings.AZURE_AD_CLIENT_SECRET,
            settings.AZURE_AD_TENANT_ID
        ]):
            raise CommandError('Azure AD configuration is incomplete')

        # Get access token for Microsoft Graph API
        access_token = self._get_access_token()
        if not access_token:
            raise CommandError('Failed to obtain access token for Microsoft Graph API')

        if options['user_id']:
            self._sync_specific_user(access_token, options['user_id'], options['force'], options['dry_run'])
        elif options['email']:
            self._sync_user_by_email(access_token, options['email'], options['force'], options['dry_run'])
        elif options['all']:
            self._sync_all_users(access_token, options['force'], options['dry_run'])
        else:
            self.stdout.write(
                self.style.WARNING('Please specify --user-id, --email, or --all')
            )

    def _get_access_token(self):
        """Get access token for Microsoft Graph API"""
        try:
            token_url = f"https://login.microsoftonline.com/{settings.AZURE_AD_TENANT_ID}/oauth2/v2.0/token"
            
            data = {
                'client_id': settings.AZURE_AD_CLIENT_ID,
                'client_secret': settings.AZURE_AD_CLIENT_SECRET,
                'grant_type': 'client_credentials',
                'scope': 'https://graph.microsoft.com/.default'
            }

            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            return token_data.get('access_token')
            
        except requests.RequestException as e:
            logger.error(f"Failed to get access token: {str(e)}")
            return None

    def _sync_specific_user(self, access_token, user_id, force=False, dry_run=False):
        """Sync a specific user by Azure AD ID"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'https://graph.microsoft.com/v1.0/users/{user_id}',
                headers=headers
            )
            response.raise_for_status()
            
            user_info = response.json()
            self._process_user(user_info, force, dry_run)
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            raise CommandError(f"Failed to get user {user_id}")

    def _sync_user_by_email(self, access_token, email, force=False, dry_run=False):
        """Sync a specific user by email"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                f'https://graph.microsoft.com/v1.0/users?$filter=mail eq \'{email}\'',
                headers=headers
            )
            response.raise_for_status()
            
            users_data = response.json()
            users = users_data.get('value', [])
            
            if not users:
                raise CommandError(f"No user found with email {email}")
            
            user_info = users[0]
            self._process_user(user_info, force, dry_run)
            
        except requests.RequestException as e:
            logger.error(f"Failed to get user by email {email}: {str(e)}")
            raise CommandError(f"Failed to get user by email {email}")

    def _sync_all_users(self, access_token, force=False, dry_run=False):
        """Sync all users from Azure AD"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(
                'https://graph.microsoft.com/v1.0/users',
                headers=headers
            )
            response.raise_for_status()
            
            users_data = response.json()
            users = users_data.get('value', [])
            
            self.stdout.write(f"Found {len(users)} users in Azure AD")
            
            for user_info in users:
                self._process_user(user_info, force, dry_run)
                
        except requests.RequestException as e:
            logger.error(f"Failed to get users: {str(e)}")
            raise CommandError("Failed to get users from Azure AD")

    def _process_user(self, user_info, force=False, dry_run=False):
        """Process a single user from Azure AD"""
        azure_id = user_info.get('id')
        email = user_info.get('mail') or user_info.get('userPrincipalName')
        
        if not email:
            self.stdout.write(
                self.style.WARNING(f"Skipping user {azure_id}: No email found")
            )
            return
        
        # Check if user already exists
        user = User.objects.filter(
            azure_ad_id=azure_id
        ).first() or User.objects.filter(
            email=email
        ).first()
        
        if user and not force:
            self.stdout.write(
                self.style.WARNING(f"User {email} already exists (use --force to update)")
            )
            return
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would sync user: {email} ({azure_id})")
            )
            return
        
        # Create or update user
        try:
            if user:
                # Update existing user
                user.azure_ad_id = azure_id
                user.first_name = user_info.get('givenName', user.first_name)
                user.last_name = user_info.get('surname', user.last_name)
                user.email_verified = True
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f"Updated user: {email}")
                )
            else:
                # Create new user
                user = User.objects.create(
                    email=email,
                    azure_ad_id=azure_id,
                    first_name=user_info.get('givenName', ''),
                    last_name=user_info.get('surname', ''),
                    is_active=True,
                    email_verified=True
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f"Created user: {email}")
                )
            
            # Create or update Azure AD profile
            profile, created = AzureADUserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'azure_ad_id': azure_id,
                    'job_title': user_info.get('jobTitle', ''),
                    'department': user_info.get('department', ''),
                    'office_location': user_info.get('officeLocation', ''),
                    'company_name': user_info.get('companyName', ''),
                    'business_phones': user_info.get('businessPhones', []),
                    'mobile_phone': user_info.get('mobilePhone', ''),
                    'preferred_language': user_info.get('preferredLanguage', ''),
                }
            )
            
            if not created:
                # Update existing profile
                profile.job_title = user_info.get('jobTitle', profile.job_title)
                profile.department = user_info.get('department', profile.department)
                profile.office_location = user_info.get('officeLocation', profile.office_location)
                profile.company_name = user_info.get('companyName', profile.company_name)
                profile.business_phones = user_info.get('businessPhones', profile.business_phones)
                profile.mobile_phone = user_info.get('mobilePhone', profile.mobile_phone)
                profile.preferred_language = user_info.get('preferredLanguage', profile.preferred_language)
                profile.save()
            
            # Create sync record
            AzureADUserSync.objects.create(
                user=user,
                azure_user_id=azure_id,
                sync_type='profile',
                status='success',
                sync_data=user_info
            )
            
        except Exception as e:
            logger.error(f"Failed to process user {email}: {str(e)}")
            self.stdout.write(
                self.style.ERROR(f"Failed to process user {email}: {str(e)}")
            ) 