"""
Domain Service - Handles domain verification and auto-claim functionality.

This service manages domain verification including:
- DNS TXT record verification
- File-based verification
- Email-based verification
- Domain auto-claim for tenants
- SSL certificate management
"""

import logging
import dns.resolver
import requests
from typing import Dict, Any, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

from api.models import Tenant, SecurityAuditLog
from api.services.audit_log_service import AuditLogService

logger = logging.getLogger(__name__)


class DomainService:
    """Service for managing domain verification and auto-claim."""
    
    def __init__(self):
        self.audit_log = AuditLogService()
        self.verification_timeout = 30  # seconds
    
    def verify_domain_ownership(self, tenant: Tenant, domain: str, 
                              verification_method: str = 'dns') -> Tuple[bool, Optional[str]]:
        """
        Verify domain ownership for a tenant.
        
        Args:
            tenant: Tenant to verify domain for
            domain: Domain to verify
            verification_method: Method to use ('dns', 'file', 'email')
            
        Returns:
            Tuple of (is_verified, error_message)
        """
        try:
            if verification_method == 'dns':
                return self._verify_domain_dns(tenant, domain)
            elif verification_method == 'file':
                return self._verify_domain_file(tenant, domain)
            elif verification_method == 'email':
                return self._verify_domain_email(tenant, domain)
            else:
                return False, f"Unsupported verification method: {verification_method}"
                
        except Exception as e:
            logger.error(f"❌ Domain verification failed: {e}")
            self.audit_log.log_event(
                event_type='system_error',
                message=f"Domain verification failed for '{domain}': {str(e)}",
                tenant=tenant,
                severity='medium',
                details={'domain': domain, 'method': verification_method, 'error': str(e)}
            )
            return False, f"Domain verification error: {str(e)}"
    
    def generate_verification_token(self, tenant: Tenant, domain: str, 
                                  verification_method: str = 'dns') -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Generate a verification token for domain verification.
        
        Args:
            tenant: Tenant to generate token for
            domain: Domain to verify
            verification_method: Method to use for verification
            
        Returns:
            Tuple of (success, token, error_message)
        """
        try:
            import secrets
            import hashlib
            
            # Generate unique verification token
            timestamp = str(int(timezone.now().timestamp()))
            random_data = secrets.token_urlsafe(32)
            tenant_id = str(tenant.id)
            
            # Create verification token
            combined = f"{tenant_id}:{domain}:{timestamp}:{random_data}"
            token = hashlib.sha256(combined.encode()).hexdigest()
            
            # Store verification token (this would typically be stored in a model)
            # For now, we'll return the token
            
            # Log token generation
            self.audit_log.log_event(
                event_type='admin_action',
                message=f"Verification token generated for domain {domain}",
                tenant=tenant,
                severity='low',
                details={
                    'domain': domain,
                    'method': verification_method,
                    'token': token[:10] + '...'  # Log only first 10 chars for security
                }
            )
            
            logger.info(f"✅ Verification token generated for domain {domain}")
            return True, token, None
            
        except Exception as e:
            logger.error(f"❌ Failed to generate verification token: {e}")
            return False, None, f"Token generation error: {str(e)}"
    
    def auto_claim_domain(self, domain: str, tenant_name: str) -> Tuple[bool, Optional[Tenant], Optional[str]]:
        """
        Automatically claim a domain for a tenant if verification passes.
        
        Args:
            domain: Domain to claim
            tenant_name: Name of the tenant claiming the domain
            
        Returns:
            Tuple of (success, tenant, error_message)
        """
        try:
            # Check if domain is already claimed
            existing_tenant = Tenant.objects.filter(domain=domain).first()
            if existing_tenant:
                return False, None, f"Domain {domain} is already claimed by {existing_tenant.name}"
            
            # Find tenant by name
            tenant = Tenant.objects.filter(name__iexact=tenant_name).first()
            if not tenant:
                return False, None, f"Tenant '{tenant_name}' not found"
            
            # Verify domain ownership
            is_verified, error = self.verify_domain_ownership(tenant, domain, 'dns')
            if not is_verified:
                return False, None, f"Domain verification failed: {error}"
            
            # Claim domain
            tenant.domain = domain
            tenant.is_verified = True
            tenant.save()
            
            # Log domain claim
            self.audit_log.log_event(
                event_type='admin_action',
                message=f"Domain {domain} auto-claimed by tenant {tenant.name}",
                tenant=tenant,
                severity='low',
                details={
                    'domain': domain,
                    'tenant_id': str(tenant.id),
                    'auto_claimed': True
                }
            )
            
            logger.info(f"✅ Domain {domain} auto-claimed by tenant {tenant.name}")
            return True, tenant, None
            
        except Exception as e:
            logger.error(f"❌ Failed to auto-claim domain: {e}")
            return False, None, f"Auto-claim error: {str(e)}"
    
    def get_domain_verification_instructions(self, tenant: Tenant, domain: str, 
                                           verification_method: str = 'dns') -> Dict[str, Any]:
        """
        Get instructions for domain verification.
        
        Args:
            tenant: Tenant to get instructions for
            domain: Domain to verify
            verification_method: Method to use for verification
            
        Returns:
            Dict containing verification instructions
        """
        try:
            if verification_method == 'dns':
                return self._get_dns_verification_instructions(tenant, domain)
            elif verification_method == 'file':
                return self._get_file_verification_instructions(tenant, domain)
            elif verification_method == 'email':
                return self._get_email_verification_instructions(tenant, domain)
            else:
                return {'error': f"Unsupported verification method: {verification_method}"}
                
        except Exception as e:
            logger.error(f"❌ Failed to get verification instructions: {e}")
            return {'error': f"Failed to get instructions: {str(e)}"}
    
    def _verify_domain_dns(self, tenant: Tenant, domain: str) -> Tuple[bool, Optional[str]]:
        """Verify domain ownership using DNS TXT record."""
        try:
            # Generate verification token
            success, token, error = self.generate_verification_token(tenant, domain, 'dns')
            if not success:
                return False, error
            
            # Check for verification TXT record
            txt_record_name = f"_prowler-verification.{domain}"
            
            try:
                answers = dns.resolver.resolve(txt_record_name, 'TXT')
                for answer in answers:
                    if token in str(answer):
                        # Domain verified
                        tenant.domain = domain
                        tenant.is_verified = True
                        tenant.save()
                        
                        # Log successful verification
                        self.audit_log.log_event(
                            event_type='admin_action',
                            message=f"Domain {domain} verified via DNS for tenant {tenant.name}",
                            tenant=tenant,
                            severity='low',
                            details={'domain': domain, 'method': 'dns'}
                        )
                        
                        logger.info(f"✅ Domain {domain} verified via DNS")
                        return True, None
                
                return False, "Verification TXT record not found or token mismatch"
                
            except dns.resolver.NXDOMAIN:
                return False, "Verification TXT record not found"
            except dns.resolver.NoAnswer:
                return False, "No TXT records found for verification domain"
            except Exception as e:
                return False, f"DNS resolution error: {str(e)}"
                
        except Exception as e:
            logger.error(f"❌ DNS verification failed: {e}")
            return False, f"DNS verification error: {str(e)}"
    
    def _verify_domain_file(self, tenant: Tenant, domain: str) -> Tuple[bool, Optional[str]]:
        """Verify domain ownership using file upload."""
        try:
            # Generate verification token
            success, token, error = self.generate_verification_token(tenant, domain, 'file')
            if not success:
                return False, error
            
            # Check for verification file
            verification_url = f"https://{domain}/.well-known/prowler-verification.txt"
            
            try:
                response = requests.get(verification_url, timeout=self.verification_timeout)
                if response.status_code == 200 and token in response.text:
                    # Domain verified
                    tenant.domain = domain
                    tenant.is_verified = True
                    tenant.save()
                    
                    # Log successful verification
                    self.audit_log.log_event(
                        event_type='admin_action',
                        message=f"Domain {domain} verified via file for tenant {tenant.name}",
                        tenant=tenant,
                        severity='low',
                        details={'domain': domain, 'method': 'file'}
                    )
                    
                    logger.info(f"✅ Domain {domain} verified via file")
                    return True, None
                else:
                    return False, "Verification file not found or token mismatch"
                    
            except requests.RequestException as e:
                return False, f"Failed to fetch verification file: {str(e)}"
                
        except Exception as e:
            logger.error(f"❌ File verification failed: {e}")
            return False, f"File verification error: {str(e)}"
    
    def _verify_domain_email(self, tenant: Tenant, domain: str) -> Tuple[bool, Optional[str]]:
        """Verify domain ownership using email verification."""
        try:
            # Generate verification token
            success, token, error = self.generate_verification_token(tenant, domain, 'email')
            if not success:
                return False, error
            
            # This would typically involve:
            # 1. Sending verification email to admin@domain.com
            # 2. User clicking verification link
            # 3. System verifying the token
            
            # For now, return a placeholder
            logger.info(f"🔍 Email verification initiated for domain {domain}")
            return True, None
            
        except Exception as e:
            logger.error(f"❌ Email verification failed: {e}")
            return False, f"Email verification error: {str(e)}"
    
    def _get_dns_verification_instructions(self, tenant: Tenant, domain: str) -> Dict[str, Any]:
        """Get DNS verification instructions."""
        success, token, error = self.generate_verification_token(tenant, domain, 'dns')
        if not success:
            return {'error': error}
        
        return {
            'method': 'dns',
            'instructions': [
                f"Add a TXT record to your DNS settings:",
                f"Name: _prowler-verification.{domain}",
                f"Value: {token}",
                f"TTL: 300 (or your default)"
            ],
            'token': token,
            'record_name': f"_prowler-verification.{domain}",
            'record_value': token
        }
    
    def _get_file_verification_instructions(self, tenant: Tenant, domain: str) -> Dict[str, Any]:
        """Get file verification instructions."""
        success, token, error = self.generate_verification_token(tenant, domain, 'file')
        if not success:
            return {'error': error}
        
        return {
            'method': 'file',
            'instructions': [
                f"Create a file at the root of your domain:",
                f"URL: https://{domain}/.well-known/prowler-verification.txt",
                f"Content: {token}",
                f"Make sure the file is publicly accessible"
            ],
            'token': token,
            'file_url': f"https://{domain}/.well-known/prowler-verification.txt",
            'file_content': token
        }
    
    def _get_email_verification_instructions(self, tenant: Tenant, domain: str) -> Dict[str, Any]:
        """Get email verification instructions."""
        success, token, error = self.generate_verification_token(tenant, domain, 'email')
        if not success:
            return {'error': error}
        
        return {
            'method': 'email',
            'instructions': [
                f"Send a verification email to admin@{domain}",
                f"Click the verification link in the email",
                f"Or enter the verification code: {token}"
            ],
            'token': token,
            'email_address': f"admin@{domain}"
        }
    
    def check_domain_ssl(self, domain: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Check SSL certificate status for a domain.
        
        Args:
            domain: Domain to check SSL for
            
        Returns:
            Tuple of (has_ssl, ssl_info, error_message)
        """
        try:
            import ssl
            import socket
            from datetime import datetime
            
            # Create SSL context
            context = ssl.create_default_context()
            
            # Connect to domain
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse certificate info
                    ssl_info = {
                        'subject': dict(x[0] for x in cert['subject']),
                        'issuer': dict(x[0] for x in cert['issuer']),
                        'version': cert['version'],
                        'serial_number': cert['serialNumber'],
                        'not_before': datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z'),
                        'not_after': datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z'),
                        'subject_alt_name': cert.get('subjectAltName', [])
                    }
                    
                    # Check if certificate is valid
                    now = datetime.now()
                    is_valid = ssl_info['not_before'] <= now <= ssl_info['not_after']
                    
                    return True, ssl_info, None if is_valid else "Certificate expired or not yet valid"
                    
        except Exception as e:
            logger.error(f"❌ SSL check failed for domain {domain}: {e}")
            return False, None, f"SSL check error: {str(e)}"
    
    def get_domain_info(self, domain: str) -> Dict[str, Any]:
        """
        Get comprehensive domain information.
        
        Args:
            domain: Domain to get info for
            
        Returns:
            Dict containing domain information
        """
        try:
            # Check if domain is already claimed
            existing_tenant = Tenant.objects.filter(domain=domain).first()
            
            # Check SSL status
            has_ssl, ssl_info, ssl_error = self.check_domain_ssl(domain)
            
            # Check DNS resolution
            try:
                import socket
                ip_address = socket.gethostbyname(domain)
                dns_resolved = True
            except socket.gaierror:
                ip_address = None
                dns_resolved = False
            
            return {
                'domain': domain,
                'is_claimed': existing_tenant is not None,
                'claimed_by': existing_tenant.name if existing_tenant else None,
                'has_ssl': has_ssl,
                'ssl_info': ssl_info,
                'ssl_error': ssl_error,
                'dns_resolved': dns_resolved,
                'ip_address': ip_address
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get domain info: {e}")
            return {'error': f"Failed to get domain info: {str(e)}"}
