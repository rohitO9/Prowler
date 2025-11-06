# Generated migration for Azure AD SSO integration

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),  # Replace with your latest migration
    ]

    operations = [
        # Add Azure AD fields to User model
        migrations.AddField(
            model_name='user',
            name='azure_id',
            field=models.CharField(blank=True, db_index=True, help_text='Azure AD User ID', max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='user',
            name='azure_tenant_id',
            field=models.CharField(blank=True, help_text='Azure AD Tenant ID', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='azure_upn',
            field=models.CharField(blank=True, help_text='User Principal Name', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='department',
            field=models.CharField(blank=True, help_text='Department from Azure AD', max_length=255),
        ),
        migrations.AddField(
            model_name='user',
            name='job_title',
            field=models.CharField(blank=True, help_text='Job title from Azure AD', max_length=255),
        ),
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, help_text='Phone number from Azure AD', max_length=50),
        ),
        migrations.AddField(
            model_name='user',
            name='manager_azure_id',
            field=models.CharField(blank=True, help_text="Manager's Azure AD ID", max_length=255),
        ),
        migrations.AddField(
            model_name='user',
            name='is_sso_user',
            field=models.BooleanField(default=False, help_text='Whether user was created via SSO'),
        ),
        migrations.AddField(
            model_name='user',
            name='deactivated_at',
            field=models.DateTimeField(blank=True, help_text='When user was deactivated', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='deactivation_reason',
            field=models.CharField(blank=True, choices=[('REMOVED_FROM_AZURE', 'Removed from Azure'), ('DISABLED_IN_AZURE', 'Disabled in Azure'), ('MANUAL', 'Manual'), ('SUBSCRIPTION_EXPIRED', 'Subscription Expired')], help_text='Reason for deactivation', max_length=50),
        ),
        migrations.AddField(
            model_name='user',
            name='invited_at',
            field=models.DateTimeField(blank=True, help_text='When user was invited', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='accepted_invite_at',
            field=models.DateTimeField(blank=True, help_text='When user accepted invitation', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='first_login_at',
            field=models.DateTimeField(blank=True, help_text='When user first logged in', null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='onboarding_completed_at',
            field=models.DateTimeField(blank=True, help_text='When user completed onboarding', null=True),
        ),
        
        # Update User model indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_azure_id ON users (azure_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_azure_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_user_sso_user ON users (is_sso_user);",
            reverse_sql="DROP INDEX IF EXISTS idx_user_sso_user;"
        ),
        
        # Update TenantMembership model
        migrations.AlterField(
            model_name='tenantmembership',
            name='role',
            field=models.CharField(choices=[('owner', 'Owner'), ('admin', 'Administrator'), ('auditor', 'Auditor'), ('viewer', 'Viewer')], default='member', max_length=50),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='can_run_scans',
            field=models.BooleanField(default=False, help_text='Can run security scans'),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='can_export_reports',
            field=models.BooleanField(default=False, help_text='Can export compliance reports'),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='invited_at',
            field=models.DateTimeField(blank=True, help_text='When user was invited', null=True),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='invite_accepted_at',
            field=models.DateTimeField(blank=True, help_text='When user accepted invitation', null=True),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='invite_token',
            field=models.CharField(blank=True, db_index=True, help_text='JWT invite token', max_length=500),
        ),
        migrations.AddField(
            model_name='tenantmembership',
            name='invite_expires_at',
            field=models.DateTimeField(blank=True, help_text='When invite expires', null=True),
        ),
        
        # Add invite_token index
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_membership_invite_token ON tenant_memberships (invite_token);",
            reverse_sql="DROP INDEX IF EXISTS idx_membership_invite_token;"
        ),
        
        # Create AzureSSOConfig model
        migrations.CreateModel(
            name='AzureSSOConfig',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('azure_tenant_id', models.CharField(db_index=True, help_text='Azure AD Tenant ID', max_length=255)),
                ('client_id', models.CharField(help_text='Azure AD Application Client ID', max_length=255)),
                ('client_secret', models.CharField(help_text='Encrypted Azure AD Client Secret', max_length=500)),
                ('authority', models.URLField(help_text='Azure AD Authority URL')),
                ('authorization_endpoint', models.URLField(help_text='OAuth2 Authorization Endpoint')),
                ('token_endpoint', models.URLField(help_text='OAuth2 Token Endpoint')),
                ('scim_enabled', models.BooleanField(default=True, help_text='Enable SCIM provisioning')),
                ('scim_token', models.CharField(help_text='SCIM Bearer Token', max_length=255, unique=True)),
                ('scim_base_url', models.URLField(help_text='SCIM Base URL')),
                ('auto_provision_users', models.BooleanField(default=True, help_text='Auto-create users from Azure AD')),
                ('auto_deprovision_users', models.BooleanField(default=True, help_text='Auto-deactivate removed users')),
                ('sync_user_attributes', models.BooleanField(default=True, help_text='Sync user profile attributes')),
                ('attribute_mapping', models.JSONField(default=dict, help_text='Azure AD attribute to local field mapping')),
                ('group_role_mapping', models.JSONField(default=dict, help_text='Azure AD group ID to role mapping')),
                ('last_sync_at', models.DateTimeField(blank=True, help_text='Last successful sync', null=True)),
                ('last_sync_status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial Success')], default='success', help_text='Last sync status', max_length=20)),
                ('last_sync_error', models.TextField(blank=True, help_text='Last sync error message')),
                ('is_active', models.BooleanField(default=True, help_text='Whether SSO is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='azure_sso_config', to='api.tenant')),
            ],
            options={
                'db_table': 'azure_sso_config',
                'verbose_name': 'Azure SSO Configuration',
                'verbose_name_plural': 'Azure SSO Configurations',
            },
        ),
        
        # Create AzureUserSync model
        migrations.CreateModel(
            name='AzureUserSync',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('azure_user_id', models.CharField(db_index=True, help_text='Azure AD User ID', max_length=255)),
                ('azure_user_data', models.JSONField(help_text='Full Azure AD user object')),
                ('action', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated'), ('deleted', 'Deleted'), ('disabled', 'Disabled'), ('enabled', 'Enabled')], help_text='Sync action performed', max_length=20)),
                ('changes', models.JSONField(default=dict, help_text='What changed in this sync')),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('skipped', 'Skipped')], help_text='Sync operation status', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Error message if sync failed')),
                ('synced_at', models.DateTimeField(auto_now_add=True, help_text='When sync occurred')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_user_syncs', to='api.tenant')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='azure_syncs', to='api.user')),
            ],
            options={
                'db_table': 'azure_user_sync',
                'verbose_name': 'Azure User Sync',
                'verbose_name_plural': 'Azure User Syncs',
                'ordering': ['-synced_at'],
            },
        ),
        
        # Create AzureADGroupMapping model
        migrations.CreateModel(
            name='AzureADGroupMapping',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('azure_group_id', models.CharField(help_text='Azure AD Group ID', max_length=255)),
                ('azure_group_name', models.CharField(help_text='Azure AD Group Display Name', max_length=255)),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('admin', 'Administrator'), ('auditor', 'Auditor'), ('viewer', 'Viewer')], help_text='Local role to assign', max_length=20)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this mapping is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_group_mappings', to='api.tenant')),
            ],
            options={
                'db_table': 'azure_ad_group_mapping',
                'verbose_name': 'Azure AD Group Mapping',
                'verbose_name_plural': 'Azure AD Group Mappings',
                'ordering': ['azure_group_name'],
            },
        ),
        
        # Create AzureADTokenCache model
        migrations.CreateModel(
            name='AzureADTokenCache',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('token_type', models.CharField(choices=[('access', 'Access Token'), ('refresh', 'Refresh Token'), ('id', 'ID Token')], help_text='Type of token', max_length=20)),
                ('token_value', models.TextField(help_text='Encrypted token value')),
                ('expires_at', models.DateTimeField(help_text='Token expiration time')),
                ('scope', models.CharField(blank=True, help_text='Token scope', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_token_caches', to='api.tenant')),
            ],
            options={
                'db_table': 'azure_ad_token_cache',
                'verbose_name': 'Azure AD Token Cache',
                'verbose_name_plural': 'Azure AD Token Caches',
            },
        ),
        
        # Create AzureADUserProfile model
        migrations.CreateModel(
            name='AzureADUserProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('azure_ad_id', models.CharField(help_text='Azure AD User ID', max_length=255, unique=True)),
                ('azure_ad_object_id', models.CharField(help_text='Azure AD Object ID', max_length=255)),
                ('azure_upn', models.CharField(help_text='User Principal Name', max_length=255)),
                ('job_title', models.CharField(blank=True, help_text='Job title from Azure AD', max_length=255)),
                ('department', models.CharField(blank=True, help_text='Department from Azure AD', max_length=255)),
                ('office_location', models.CharField(blank=True, help_text='Office location', max_length=255)),
                ('business_phones', models.JSONField(default=list, help_text='Business phone numbers')),
                ('mobile_phone', models.CharField(blank=True, help_text='Mobile phone number', max_length=50)),
                ('preferred_language', models.CharField(blank=True, help_text='Preferred language', max_length=10)),
                ('photo_url', models.URLField(blank=True, help_text='Profile photo URL')),
                ('azure_groups', models.JSONField(default=list, help_text='Azure AD groups user belongs to')),
                ('last_synced_at', models.DateTimeField(auto_now=True, help_text='Last sync time')),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial Success')], default='pending', help_text='Sync status', max_length=50)),
                ('sync_error', models.TextField(blank=True, help_text='Last sync error message')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_user_profiles', to='api.tenant')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='azure_profile', to='api.user')),
            ],
            options={
                'db_table': 'azure_ad_user_profile',
                'verbose_name': 'Azure AD User Profile',
                'verbose_name_plural': 'Azure AD User Profiles',
            },
        ),
        
        # Create AzureADAuditLog model
        migrations.CreateModel(
            name='AzureADAuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('event_type', models.CharField(choices=[('TENANT_CREATED', 'Tenant Created'), ('SSO_CONFIGURED', 'SSO Configured'), ('SSO_DISABLED', 'SSO Disabled'), ('USER_INVITED', 'User Invited'), ('USER_ACCEPTED_INVITE', 'User Accepted Invite'), ('USER_DEACTIVATED', 'User Deactivated'), ('AZURE_USER_SYNCED', 'Azure User Synced'), ('AZURE_USER_REMOVED', 'Azure User Removed'), ('ROLE_ASSIGNED', 'Role Assigned'), ('ROLE_CHANGED', 'Role Changed'), ('LOGIN_SUCCESS', 'Login Success'), ('SSO_LOGIN', 'SSO Login'), ('SCIM_SYNC_STARTED', 'SCIM Sync Started'), ('SCIM_SYNC_COMPLETED', 'SCIM Sync Completed'), ('SCIM_SYNC_FAILED', 'SCIM Sync Failed'), ('GROUP_MAPPING_CREATED', 'Group Mapping Created'), ('GROUP_MAPPING_UPDATED', 'Group Mapping Updated'), ('TOKEN_REFRESHED', 'Token Refreshed'), ('TOKEN_EXPIRED', 'Token Expired')], db_index=True, help_text='Type of audit event', max_length=50)),
                ('description', models.TextField(help_text='Human-readable description')),
                ('details', models.JSONField(default=dict, help_text='Additional event details')),
                ('ip_address', models.GenericIPAddressField(blank=True, help_text='Client IP address', null=True)),
                ('user_agent', models.TextField(blank=True, help_text='User agent string')),
                ('request_id', models.CharField(blank=True, help_text='Request ID for tracing', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_audit_logs', to='api.tenant')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='azure_audit_logs', to='api.user')),
            ],
            options={
                'db_table': 'azure_ad_audit_log',
                'verbose_name': 'Azure AD Audit Log',
                'verbose_name_plural': 'Azure AD Audit Logs',
                'ordering': ['-created_at'],
            },
        ),
        
        # Add constraints and indexes
        migrations.AddConstraint(
            model_name='azureadgroupmapping',
            constraint=models.UniqueConstraint(fields=('tenant', 'azure_group_id'), name='unique_tenant_azure_group'),
        ),
        migrations.AddConstraint(
            model_name='azureadtokencache',
            constraint=models.UniqueConstraint(fields=('tenant', 'token_type', 'scope'), name='unique_tenant_token_type_scope'),
        ),
        
        # Add indexes for performance
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_sso_config_tenant_id ON azure_sso_config (azure_tenant_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_sso_config_tenant_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_sso_config_scim_token ON azure_sso_config (scim_token);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_sso_config_scim_token;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_user_sync_tenant_synced ON azure_user_sync (tenant_id, synced_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_user_sync_tenant_synced;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_user_sync_azure_id ON azure_user_sync (azure_user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_user_sync_azure_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_audit_log_tenant_created ON azure_ad_audit_log (tenant_id, created_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_audit_log_tenant_created;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_azure_audit_log_event_type ON azure_ad_audit_log (event_type, created_at);",
            reverse_sql="DROP INDEX IF EXISTS idx_azure_audit_log_event_type;"
        ),
    ]
