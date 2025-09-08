"""
Database migrations for Azure AD RBAC system
"""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('api', '0041_remove_complianceoverview_rls_on_complianceoverview_and_more'),
    ]

    operations = [
        # Create Company table
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Company name', max_length=255)),
                ('domain', models.CharField(help_text='Primary email domain', max_length=255, unique=True)),
                ('azure_tenant_id', models.CharField(help_text='Azure AD Tenant ID', max_length=255, unique=True)),
                ('azure_client_id', models.CharField(help_text='Azure AD Application Client ID', max_length=255)),
                ('azure_client_secret', models.BinaryField(db_column='azure_client_secret', help_text='Encrypted Azure AD Client Secret')),
                ('azure_redirect_uri', models.URLField(help_text='Azure AD Redirect URI')),
                ('azure_scopes', models.JSONField(default=list, help_text='Azure AD OAuth Scopes')),
                ('azure_allowed_domains', models.JSONField(default=list, help_text='Allowed email domains')),
                ('is_active', models.BooleanField(default=True, help_text='Whether the company is active')),
                ('trial_start', models.DateTimeField(blank=True, help_text='Trial start date', null=True)),
                ('trial_end', models.DateTimeField(blank=True, help_text='Trial end date', null=True)),
                ('subscription_tier', models.CharField(choices=[('trial', 'Trial'), ('basic', 'Basic'), ('professional', 'Professional'), ('enterprise', 'Enterprise')], default='trial', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_companies', to='api.user')),
            ],
            options={
                'verbose_name': 'Company',
                'verbose_name_plural': 'Companies',
                'db_table': 'companies',
                'ordering': ['name'],
            },
        ),
        
        # Create Permission table
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="Permission name (e.g., 'users.create')", max_length=100, unique=True)),
                ('display_name', models.CharField(help_text='Human-readable permission name', max_length=255)),
                ('description', models.TextField(help_text='Permission description')),
                ('category', models.CharField(choices=[('user_management', 'User Management'), ('company_management', 'Company Management'), ('provider_management', 'Provider Management'), ('scan_management', 'Scan Management'), ('compliance_management', 'Compliance Management'), ('integration_management', 'Integration Management'), ('audit_access', 'Audit Access'), ('billing_management', 'Billing Management'), ('system_admin', 'System Administration')], max_length=50)),
                ('resource_type', models.CharField(blank=True, help_text='Resource type this permission applies to', max_length=100)),
                ('action', models.CharField(help_text='Action (create, read, update, delete, execute)', max_length=50)),
                ('is_system_permission', models.BooleanField(default=False, help_text='System-level permission')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this permission is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Permission',
                'verbose_name_plural': 'Permissions',
                'db_table': 'permissions',
                'ordering': ['category', 'name'],
            },
        ),
        
        # Create EnhancedRole table
        migrations.CreateModel(
            name='EnhancedRole',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Role name', max_length=255)),
                ('display_name', models.CharField(help_text='Human-readable role name', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Role description')),
                ('role_type', models.CharField(choices=[('system', 'System Role'), ('company', 'Company Role'), ('azure_sync', 'Azure AD Synced Role'), ('custom', 'Custom Role')], default='company', max_length=50)),
                ('manage_users', models.BooleanField(default=False, help_text='Can manage users')),
                ('manage_account', models.BooleanField(default=False, help_text='Can manage account settings')),
                ('manage_billing', models.BooleanField(default=False, help_text='Can manage billing')),
                ('manage_providers', models.BooleanField(default=False, help_text='Can manage providers')),
                ('manage_integrations', models.BooleanField(default=False, help_text='Can manage integrations')),
                ('manage_scans', models.BooleanField(default=False, help_text='Can manage scans')),
                ('unlimited_visibility', models.BooleanField(default=False, help_text='Has unlimited visibility')),
                ('azure_group_id', models.CharField(blank=True, help_text='Azure AD Group ID', max_length=255)),
                ('azure_group_name', models.CharField(blank=True, help_text='Azure AD Group Name', max_length=255)),
                ('auto_sync_from_azure', models.BooleanField(default=False, help_text='Auto-sync from Azure AD')),
                ('is_system_role', models.BooleanField(default=False, help_text='System-level role')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this role is active')),
                ('is_default', models.BooleanField(default=False, help_text='Default role for new users')),
                ('priority', models.IntegerField(default=0, help_text='Role priority (higher = more important)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_roles', to='api.user')),
                ('tenant_id', models.UUIDField()),
            ],
            options={
                'verbose_name': 'Enhanced Role',
                'verbose_name_plural': 'Enhanced Roles',
                'db_table': 'enhanced_roles',
                'ordering': ['-priority', 'name'],
            },
        ),
        
        # Create AzureADGroupMapping table
        migrations.CreateModel(
            name='AzureADGroupMapping',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('azure_group_id', models.CharField(help_text='Azure AD Group ID', max_length=255)),
                ('azure_group_name', models.CharField(help_text='Azure AD Group Display Name', max_length=255)),
                ('azure_group_description', models.TextField(blank=True, help_text='Azure AD Group Description')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this mapping is active')),
                ('auto_sync', models.BooleanField(default=True, help_text='Automatically sync group members')),
                ('sync_frequency', models.IntegerField(default=3600, help_text='Sync frequency in seconds')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_synced_at', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_group_mappings', to='api.company')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_group_mappings', to='api.enhancedrole')),
            ],
            options={
                'verbose_name': 'Azure AD Group Mapping',
                'verbose_name_plural': 'Azure AD Group Mappings',
                'db_table': 'azure_ad_group_mappings',
                'ordering': ['azure_group_name'],
            },
        ),
        
        # Create AzureADUserProfile table
        migrations.CreateModel(
            name='AzureADUserProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('azure_ad_id', models.CharField(help_text='Azure AD User ID', max_length=255)),
                ('azure_ad_object_id', models.CharField(help_text='Azure AD Object ID', max_length=255)),
                ('job_title', models.CharField(blank=True, help_text='Job title from Azure AD', max_length=255)),
                ('department', models.CharField(blank=True, help_text='Department from Azure AD', max_length=255)),
                ('office_location', models.CharField(blank=True, help_text='Office location from Azure AD', max_length=255)),
                ('business_phones', models.JSONField(default=list, help_text='Business phone numbers')),
                ('mobile_phone', models.CharField(blank=True, help_text='Mobile phone number', max_length=50)),
                ('preferred_language', models.CharField(blank=True, help_text='Preferred language', max_length=10)),
                ('photo_url', models.URLField(blank=True, help_text='Profile photo URL')),
                ('azure_groups', models.JSONField(default=list, help_text='Azure AD groups user belongs to')),
                ('last_synced_at', models.DateTimeField(auto_now=True)),
                ('sync_status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed'), ('partial', 'Partial Success')], default='pending', max_length=50)),
                ('sync_error', models.TextField(blank=True, help_text='Last sync error message')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_users', to='api.company')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='azure_profile', to='api.user')),
            ],
            options={
                'verbose_name': 'Azure AD User Profile',
                'verbose_name_plural': 'Azure AD User Profiles',
                'db_table': 'azure_ad_user_profiles',
            },
        ),
        
        # Create AzureADTokenCache table
        migrations.CreateModel(
            name='AzureADTokenCache',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('access_token', models.TextField(help_text='Azure AD access token')),
                ('refresh_token', models.TextField(help_text='Azure AD refresh token')),
                ('id_token', models.TextField(help_text='Azure AD ID token')),
                ('token_type', models.CharField(default='Bearer', max_length=50)),
                ('scope', models.TextField(help_text='Token scope')),
                ('expires_at', models.DateTimeField(help_text='Token expiration time')),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_tokens', to='api.company')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='azure_token_cache', to='api.user')),
            ],
            options={
                'verbose_name': 'Azure AD Token Cache',
                'verbose_name_plural': 'Azure AD Token Caches',
                'db_table': 'azure_ad_token_cache',
                'ordering': ['-created_at'],
            },
        ),
        
        # Create UserRoleAssignment table
        migrations.CreateModel(
            name='UserRoleAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('assignment_source', models.CharField(choices=[('direct', 'Direct Assignment'), ('azure_group', 'Azure AD Group'), ('custom_group', 'Custom Group'), ('inherited', 'Inherited'), ('default', 'Default Role')], default='direct', help_text='How this role was assigned', max_length=50)),
                ('source_reference', models.CharField(blank=True, help_text='Reference to source (e.g., Azure group ID)', max_length=255)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Role expiration date', null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this assignment is active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_roles', to='api.user')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_role_assignments', to='api.company')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_assignments', to='api.enhancedrole')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_assignments', to='api.user')),
            ],
            options={
                'verbose_name': 'User Role Assignment',
                'verbose_name_plural': 'User Role Assignments',
                'db_table': 'user_role_assignments',
                'ordering': ['-assigned_at'],
            },
        ),
        
        # Create RolePermission table
        migrations.CreateModel(
            name='RolePermission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('granted', models.BooleanField(default=True, help_text='Whether this permission is granted')),
                ('conditions', models.JSONField(default=dict, help_text='Additional conditions for this permission')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('permission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='api.permission')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_permissions', to='api.enhancedrole')),
            ],
            options={
                'verbose_name': 'Role Permission',
                'verbose_name_plural': 'Role Permissions',
                'db_table': 'role_permissions',
            },
        ),
        
        # Create AuditLog table
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action_type', models.CharField(choices=[('login', 'User Login'), ('logout', 'User Logout'), ('role_assigned', 'Role Assigned'), ('role_removed', 'Role Removed'), ('permission_granted', 'Permission Granted'), ('permission_denied', 'Permission Denied'), ('data_access', 'Data Access'), ('data_modified', 'Data Modified'), ('azure_sync', 'Azure AD Sync'), ('group_sync', 'Group Sync'), ('token_refresh', 'Token Refresh'), ('profile_update', 'Profile Update'), ('company_created', 'Company Created'), ('company_updated', 'Company Updated'), ('error', 'Error'), ('security_event', 'Security Event')], max_length=50)),
                ('action_description', models.TextField(help_text='Human-readable description of the action')),
                ('resource_type', models.CharField(blank=True, help_text='Type of resource affected', max_length=100)),
                ('resource_id', models.CharField(blank=True, help_text='ID of resource affected', max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('request_method', models.CharField(blank=True, max_length=10)),
                ('request_path', models.CharField(blank=True, max_length=500)),
                ('details', models.JSONField(default=dict, help_text='Additional action details')),
                ('metadata', models.JSONField(default=dict, help_text='System metadata')),
                ('success', models.BooleanField(default=True)),
                ('error_message', models.TextField(blank=True, help_text='Error message if action failed')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='api.company')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='api.user')),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'db_table': 'audit_logs',
                'ordering': ['-created_at'],
            },
        ),
        
        # Add constraints
        migrations.AddConstraint(
            model_name='enhancedrole',
            constraint=models.UniqueConstraint(fields=['tenant_id', 'name'], name='unique_enhanced_role_per_tenant'),
        ),
        migrations.AddConstraint(
            model_name='enhancedrole',
            constraint=models.UniqueConstraint(condition=models.Q(azure_group_id__isnull=False), fields=['tenant_id', 'azure_group_id'], name='unique_azure_group_per_tenant'),
        ),
        migrations.AddConstraint(
            model_name='azureadgroupmapping',
            constraint=models.UniqueConstraint(fields=['company', 'azure_group_id'], name='unique_company_azure_group'),
        ),
        migrations.AddConstraint(
            model_name='azureaduserprofile',
            constraint=models.UniqueConstraint(fields=['company', 'azure_ad_id'], name='unique_company_azure_user'),
        ),
        migrations.AddConstraint(
            model_name='azureadtokencache',
            constraint=models.UniqueConstraint(fields=['user', 'company'], name='unique_user_company_token'),
        ),
        migrations.AddConstraint(
            model_name='userroleassignment',
            constraint=models.UniqueConstraint(fields=['user', 'role', 'company'], name='unique_user_role_company'),
        ),
        migrations.AddConstraint(
            model_name='rolepermission',
            constraint=models.UniqueConstraint(fields=['role', 'permission'], name='unique_role_permission'),
        ),
        
        # Add indexes
        migrations.RunSQL(
            "CREATE INDEX idx_audit_logs_user_created ON audit_logs (user_id, created_at);",
            reverse_sql="DROP INDEX idx_audit_logs_user_created;"
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_audit_logs_company_created ON audit_logs (company_id, created_at);",
            reverse_sql="DROP INDEX idx_audit_logs_company_created;"
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_audit_logs_action_created ON audit_logs (action_type, created_at);",
            reverse_sql="DROP INDEX idx_audit_logs_action_created;"
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_audit_logs_success_created ON audit_logs (success, created_at);",
            reverse_sql="DROP INDEX idx_audit_logs_success_created;"
        ),
    ]
