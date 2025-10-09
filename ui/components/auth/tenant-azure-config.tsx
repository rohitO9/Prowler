'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card/card';
import { Input } from '@/components/ui/input/input';
import { Label } from '@/components/ui/label/label';
import { Switch } from '@/components/ui/switch/switch';
import { Alert, AlertDescription } from '@/components/ui/alert/alert';
import { Badge } from '@/components/ui/badge/badge';
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogHeader, 
  DialogTitle,
  DialogTrigger 
} from '@/components/ui/dialog/dialog';
import { 
  Loader2, 
  Shield, 
  Settings, 
  Save, 
  Trash2, 
  Eye, 
  EyeOff,
  CheckCircle,
  AlertCircle,
  Info
} from 'lucide-react';
import { useTenant } from '@/hooks/use-tenant';
import { 
  getAzureConfig, 
  updateAzureConfig, 
  deleteAzureConfig 
} from '@/actions/auth/tenant-azure-auth';

interface TenantAzureConfigProps {
  onConfigUpdate?: (config: any) => void;
  onConfigDelete?: () => void;
  className?: string;
}

const TenantAzureConfig: React.FC<TenantAzureConfigProps> = ({
  onConfigUpdate,
  onConfigDelete,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [azureConfig, setAzureConfig] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showSecrets, setShowSecrets] = useState(false);

  const { tenant, hasPermission } = useTenant();

  // Form state
  const [formData, setFormData] = useState({
    client_id: '',
    client_secret: '',
    azure_tenant_id: '',
    scopes: ['openid', 'profile', 'email', 'User.Read'],
    allowed_domains: [],
    auto_create_users: true,
    require_email_verification: false,
  });

  // Load existing configuration
  useEffect(() => {
    if (isOpen) {
      loadAzureConfig();
    }
  }, [isOpen]);

  const loadAzureConfig = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const config = await getAzureConfig();
      setAzureConfig(config);
      
      if (config.configured) {
        setFormData({
          client_id: config.client_id || '',
          client_secret: '', // Never show existing secret
          azure_tenant_id: config.azure_tenant_id || '',
          scopes: config.scopes || ['openid', 'profile', 'email', 'User.Read'],
          allowed_domains: config.allowed_domains || [],
          auto_create_users: config.auto_create_users ?? true,
          require_email_verification: config.require_email_verification ?? false,
        });
      }
    } catch (error) {
      console.error('Load Azure config error:', error);
      setError('Failed to load Azure configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await updateAzureConfig({}, formData);
      
      if (result.message === 'Azure AD configuration updated successfully') {
        setSuccess('Azure AD configuration updated successfully');
        setAzureConfig(result.config);
        onConfigUpdate?.(result.config);
        
        // Close dialog after successful save
        setTimeout(() => {
          setIsOpen(false);
        }, 1500);
      } else {
        setError(result.message || 'Failed to update configuration');
      }
    } catch (error) {
      console.error('Update Azure config error:', error);
      setError('Failed to update Azure configuration');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete the Azure AD configuration? This will disable Azure AD login for all users.')) {
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      await deleteAzureConfig();
      setAzureConfig(null);
      setFormData({
        client_id: '',
        client_secret: '',
        azure_tenant_id: '',
        scopes: ['openid', 'profile', 'email', 'User.Read'],
        allowed_domains: [],
        auto_create_users: true,
        require_email_verification: false,
      });
      onConfigDelete?.();
      setIsOpen(false);
    } catch (error) {
      console.error('Delete Azure config error:', error);
      setError('Failed to delete Azure configuration');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleDomainChange = (value: string) => {
    const domains = value.split(',').map(d => d.trim()).filter(d => d);
    handleInputChange('allowed_domains', domains);
  };

  const handleScopeChange = (value: string) => {
    const scopes = value.split(',').map(s => s.trim()).filter(s => s);
    handleInputChange('scopes', scopes);
  };

  if (!hasPermission('can_manage_settings')) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" className={className}>
          <Settings className="mr-2 h-4 w-4" />
          Azure AD Settings
        </Button>
      </DialogTrigger>
      
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center">
            <Shield className="mr-2 h-5 w-5" />
            Azure AD Configuration
          </DialogTitle>
          <DialogDescription>
            Configure Azure AD authentication for {tenant?.name || 'this organization'}.
            Users will be able to sign in using their organization's Azure AD accounts.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {isLoading && !azureConfig && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span className="ml-2">Loading configuration...</span>
            </div>
          )}

          {!isLoading && (
            <div className="space-y-4">
              {/* Azure AD App Registration Details */}
              <div className="space-y-4">
                <div>
                  <Label htmlFor="client_id">Client ID</Label>
                  <Input
                    id="client_id"
                    value={formData.client_id}
                    onChange={(e) => handleInputChange('client_id', e.target.value)}
                    placeholder="Enter your Azure AD Application Client ID"
                  />
                </div>

                <div>
                  <Label htmlFor="client_secret">Client Secret</Label>
                  <div className="relative">
                    <Input
                      id="client_secret"
                      type={showSecrets ? 'text' : 'password'}
                      value={formData.client_secret}
                      onChange={(e) => handleInputChange('client_secret', e.target.value)}
                      placeholder="Enter your Azure AD Application Client Secret"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => setShowSecrets(!showSecrets)}
                    >
                      {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>

                <div>
                  <Label htmlFor="azure_tenant_id">Azure Tenant ID (Optional)</Label>
                  <Input
                    id="azure_tenant_id"
                    value={formData.azure_tenant_id}
                    onChange={(e) => handleInputChange('azure_tenant_id', e.target.value)}
                    placeholder="Enter your Azure AD Tenant ID (optional)"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Leave empty to allow any Azure AD tenant
                  </p>
                </div>
              </div>

              {/* OAuth Scopes */}
              <div>
                <Label htmlFor="scopes">OAuth Scopes</Label>
                <Input
                  id="scopes"
                  value={formData.scopes.join(', ')}
                  onChange={(e) => handleScopeChange(e.target.value)}
                  placeholder="openid, profile, email, User.Read"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Comma-separated list of OAuth scopes to request
                </p>
              </div>

              {/* Allowed Domains */}
              <div>
                <Label htmlFor="allowed_domains">Allowed Email Domains (Optional)</Label>
                <Input
                  id="allowed_domains"
                  value={formData.allowed_domains.join(', ')}
                  onChange={(e) => handleDomainChange(e.target.value)}
                  placeholder="company.com, example.org"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Restrict login to specific email domains (leave empty to allow all)
                </p>
              </div>

              {/* User Creation Settings */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto-create Users</Label>
                    <p className="text-xs text-gray-500">
                      Automatically create new users on first login
                    </p>
                  </div>
                  <Switch
                    checked={formData.auto_create_users}
                    onCheckedChange={(checked) => handleInputChange('auto_create_users', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Require Email Verification</Label>
                    <p className="text-xs text-gray-500">
                      Require email verification for new users
                    </p>
                  </div>
                  <Switch
                    checked={formData.require_email_verification}
                    onCheckedChange={(checked) => handleInputChange('require_email_verification', checked)}
                  />
                </div>
              </div>

              {/* Current Configuration Status */}
              {azureConfig?.configured && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Current Configuration</h4>
                    <Badge variant="secondary">Active</Badge>
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>Client ID:</strong> {azureConfig.client_id}</p>
                    <p><strong>Azure Tenant ID:</strong> {azureConfig.azure_tenant_id || 'Any tenant'}</p>
                    <p><strong>Scopes:</strong> {azureConfig.scopes?.join(', ')}</p>
                    <p><strong>Auto-create Users:</strong> {azureConfig.auto_create_users ? 'Yes' : 'No'}</p>
                    {azureConfig.last_used && (
                      <p><strong>Last Used:</strong> {new Date(azureConfig.last_used).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Info Alert */}
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  <strong>Redirect URI:</strong> https://{tenant?.subdomain}.yourdomain.com/api/auth/azure/callback
                  <br />
                  Make sure to add this redirect URI to your Azure AD application registration.
                </AlertDescription>
              </Alert>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-between pt-4 border-t">
            <div>
              {azureConfig?.configured && (
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete Configuration
                    </>
                  )}
                </Button>
              )}
            </div>
            
            <div className="space-x-2">
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Configuration
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TenantAzureConfig;
