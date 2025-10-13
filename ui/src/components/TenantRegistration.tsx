'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

interface TenantRegistrationProps {
  onRegistrationComplete?: (subdomain: string) => void;
}

interface FormData {
  // Tenant Information
  tenantName: string;
  subdomain: string;
  contactEmail: string;
  contactPhone: string;
  address: string;
  
  // Configuration
  logoUrl: string;
  themeColor: string;
  secondaryColor: string;
  
  // Admin User Information
  adminFirstName: string;
  adminLastName: string;
  adminEmail: string;
}

const TenantRegistration: React.FC<TenantRegistrationProps> = ({ onRegistrationComplete }) => {
  const router = useRouter();
  
  // Auto-detect subdomain and company name from URL
  const getAutoDetectedData = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      console.log('🔍 [TenantRegistration] Current hostname:', hostname);
      
      if (hostname.includes('.localhost')) {
        const subdomain = hostname.split('.')[0];
        const companyName = subdomain.replace('-', ' ').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        console.log('🔍 [TenantRegistration] Auto-detected subdomain:', subdomain);
        console.log('🔍 [TenantRegistration] Auto-generated company name:', companyName);
        return { subdomain, companyName };
      }
    }
    return { subdomain: '', companyName: '' };
  };
  
  const { subdomain: autoSubdomain, companyName: autoCompanyName } = getAutoDetectedData();
  
  const [formData, setFormData] = useState<FormData>({
    tenantName: autoCompanyName,
    subdomain: autoSubdomain,
    contactEmail: '',
    contactPhone: '',
    address: '',
    logoUrl: '',
    themeColor: '#3B82F6',
    secondaryColor: '#1E40AF',
    adminFirstName: '',
    adminLastName: '',
    adminEmail: '',
  });
  
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubdomainChecking, setIsSubdomainChecking] = useState(false);
  const [isSubdomainAvailable, setIsSubdomainAvailable] = useState<boolean | null>(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const handleInputChange = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Auto-generate subdomain from tenant name
    if (field === 'tenantName' && !formData.subdomain) {
      const generatedSubdomain = value
        .toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, '-')
        .substring(0, 20);
      setFormData(prev => ({ ...prev, subdomain: generatedSubdomain }));
    }
  };

  // Validate required fields before submission
  const validateRequiredFields = () => {
    console.log('=== FIELD VALIDATION START ===');
    
    // Check all form data values
    console.log('Current form data:');
    Object.entries(formData).forEach(([key, value]) => {
      console.log(`  ${key}: "${value}" (length: ${value?.length || 0}, trimmed: "${value?.trim() || ''}")`);
    });

    const requiredFields = {
      tenantName: 'Company Name',
      subdomain: 'Subdomain',
      contactEmail: 'Contact Email',
      adminFirstName: 'Admin First Name',
      adminLastName: 'Admin Last Name',
      adminEmail: 'Admin Email'
    };

    const missingFields: string[] = [];
    const emptyFields: string[] = [];
    
    console.log('Checking required fields:');
    Object.entries(requiredFields).forEach(([key, label]) => {
      const value = formData[key as keyof FormData];
      const trimmedValue = value?.trim();
      console.log(`  ${label} (${key}): "${value}" -> trimmed: "${trimmedValue}" -> valid: ${!!trimmedValue}`);
      
      if (!trimmedValue) {
        missingFields.push(label);
        emptyFields.push(key);
      }
    });

    if (missingFields.length > 0) {
      console.log('❌ Validation failed - missing fields:', missingFields);
      console.log('❌ Empty field keys:', emptyFields);
      setError(`Please fill in all required fields: ${missingFields.join(', ')}`);
      return false;
    }

    // Validate email formats
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    console.log('Validating contact email:', formData.contactEmail);
    if (!emailRegex.test(formData.contactEmail)) {
      console.log('❌ Invalid contact email format');
      setError('Please enter a valid contact email address');
      return false;
    }
    
    console.log('Validating admin email:', formData.adminEmail);
    if (!emailRegex.test(formData.adminEmail)) {
      console.log('❌ Invalid admin email format');
      setError('Please enter a valid admin email address');
      return false;
    }

    // Validate subdomain format
    const subdomainRegex = /^[a-z0-9][a-z0-9-_]*[a-z0-9]$/;
    console.log('Validating subdomain:', formData.subdomain, 'Length:', formData.subdomain.length);
    if (formData.subdomain.length < 3) {
      console.log('❌ Subdomain too short');
      setError('Subdomain must be at least 3 characters long');
      return false;
    }
    
    if (!subdomainRegex.test(formData.subdomain)) {
      console.log('❌ Invalid subdomain format');
      setError('Subdomain must contain only lowercase letters, numbers, hyphens, and underscores');
      return false;
    }

    console.log('✅ All validation checks passed');
    console.log('=== FIELD VALIDATION END ===');
    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsRegistering(true);
    setError(null);

    // Validate form data
    if (!validateRequiredFields()) {
        setIsRegistering(false);
        return;
    }

    // Format payload according to JSON:API specification
    const payload = {
        data: {
            type: 'register_tenant',
            attributes: {
                tenant_name: formData.tenantName.trim(),
                subdomain: formData.subdomain.trim(),
                contact_email: formData.contactEmail.trim(),
                admin_first_name: formData.adminFirstName.trim(),
                admin_last_name: formData.adminLastName.trim(),
                admin_email: formData.adminEmail.trim(),
                contact_phone: formData.contactPhone?.trim() || '',
                address: formData.address?.trim() || '',
                logo_url: formData.logoUrl?.trim() || '',
                theme_color: formData.themeColor || '#3B82F6',
                secondary_color: formData.secondaryColor || '#1E40AF'
            }
        }
    };

    console.log('Sending registration payload:', JSON.stringify(payload, null, 2));

    try {
        const response = await fetch('http://localhost:8080/api/v1/tenant/register-tenant', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/vnd.api+json',
                'Accept': 'application/vnd.api+json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            setSuccess(
                data.message || 
                'Tenant created successfully! Please check your email for verification instructions.'
            );
            if (onRegistrationComplete) {
                onRegistrationComplete(formData.subdomain);
            }
        } else {
            const errorMessage = data.errors?.[0]?.detail || 'Failed to create tenant';
            setError(errorMessage);
            console.error('Registration failed:', data);
        }
    } catch (error) {
        console.error('Registration error:', error);
        setError('Network error while creating tenant');
    } finally {
        setIsRegistering(false);
    }
  };

  const nextStep = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Company Information</h3>
      
      <div>
        <label htmlFor="tenantName" className="block text-sm font-medium text-gray-700">
          Company Name *
        </label>
        <input
          type="text"
          id="tenantName"
          value={formData.tenantName}
          onChange={(e) => handleInputChange('tenantName', e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Enter your company name"
          required
        />
        {autoCompanyName && (
          <p className="mt-1 text-sm text-green-600">
            ✅ Auto-detected from subdomain: <strong>{autoCompanyName}</strong>
          </p>
        )}
      </div>
      
      <div>
        <label htmlFor="subdomain" className="block text-sm font-medium text-gray-700">
          Subdomain *
        </label>
        <div className="flex space-x-2">
          <input
            type="text"
            id="subdomain"
            value={formData.subdomain}
            onChange={(e) => handleInputChange('subdomain', e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ''))}
            className="flex-1 mt-1 block px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="your-company"
            required
          />
        </div>
        <div className="mt-1 text-sm text-gray-500">
          Your URL will be: <strong>{formData.subdomain}.localhost:3000</strong>
        </div>
        {autoSubdomain && (
          <p className="mt-1 text-sm text-green-600">
            ✅ Auto-detected from current URL: <strong>{autoSubdomain}</strong>
          </p>
        )}
      </div>
      
      <div>
        <label htmlFor="contactEmail" className="block text-sm font-medium text-gray-700">
          Contact Email *
        </label>
        <input
          type="email"
          id="contactEmail"
          value={formData.contactEmail}
          onChange={(e) => handleInputChange('contactEmail', e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="contact@yourcompany.com"
          required
        />
      </div>
      
      <div>
        <label htmlFor="contactPhone" className="block text-sm font-medium text-gray-700">
          Contact Phone
        </label>
        <input
          type="tel"
          id="contactPhone"
          value={formData.contactPhone}
          onChange={(e) => handleInputChange('contactPhone', e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="+1 (555) 123-4567"
        />
      </div>
      
      <div>
        <label htmlFor="address" className="block text-sm font-medium text-gray-700">
          Company Address
        </label>
        <textarea
          id="address"
          value={formData.address}
          onChange={(e) => handleInputChange('address', e.target.value)}
          rows={3}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="Enter your company address"
        />
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Customization</h3>
      
      <div>
        <label htmlFor="logoUrl" className="block text-sm font-medium text-gray-700">
          Logo URL
        </label>
        <input
          type="url"
          id="logoUrl"
          value={formData.logoUrl}
          onChange={(e) => handleInputChange('logoUrl', e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="https://example.com/logo.png"
        />
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="themeColor" className="block text-sm font-medium text-gray-700">
            Primary Color
          </label>
          <div className="flex space-x-2">
            <input
              type="color"
              id="themeColor"
              value={formData.themeColor}
              onChange={(e) => handleInputChange('themeColor', e.target.value)}
              className="mt-1 h-10 w-16 border border-gray-300 rounded-md"
            />
            <input
              type="text"
              value={formData.themeColor}
              onChange={(e) => handleInputChange('themeColor', e.target.value)}
              className="flex-1 mt-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="secondaryColor" className="block text-sm font-medium text-gray-700">
            Secondary Color
          </label>
          <div className="flex space-x-2">
            <input
              type="color"
              id="secondaryColor"
              value={formData.secondaryColor}
              onChange={(e) => handleInputChange('secondaryColor', e.target.value)}
              className="mt-1 h-10 w-16 border border-gray-300 rounded-md"
            />
            <input
              type="text"
              value={formData.secondaryColor}
              onChange={(e) => handleInputChange('secondaryColor', e.target.value)}
              className="flex-1 mt-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-900">Admin Account</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="adminFirstName" className="block text-sm font-medium text-gray-700">
            First Name *
          </label>
          <input
            type="text"
            id="adminFirstName"
            value={formData.adminFirstName}
            onChange={(e) => handleInputChange('adminFirstName', e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="John"
            required
          />
        </div>
        
        <div>
          <label htmlFor="adminLastName" className="block text-sm font-medium text-gray-700">
            Last Name *
          </label>
          <input
            type="text"
            id="adminLastName"
            value={formData.adminLastName}
            onChange={(e) => handleInputChange('adminLastName', e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Doe"
            required
          />
        </div>
      </div>
      
      <div>
        <label htmlFor="adminEmail" className="block text-sm font-medium text-gray-700">
          Admin Email *
        </label>
        <input
          type="email"
          id="adminEmail"
          value={formData.adminEmail}
          onChange={(e) => handleInputChange('adminEmail', e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
          placeholder="admin@yourcompany.com"
          required
        />
        <p className="mt-1 text-sm text-gray-500">
          This will be your admin account for managing the tenant.
        </p>
      </div>
    </div>
  );

  if (success) {
    return (
      <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
            <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="mt-4 text-lg font-medium text-gray-900">Registration Successful!</h2>
          <p className="mt-2 text-sm text-gray-600">{success}</p>
          <div className="mt-6">
            <button
              onClick={() => router.push('/')}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Return to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center">Create Your Company Account</h2>
      
      {/* Progress indicator */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[1, 2, 3].map((step) => (
            <div key={step} className="flex items-center">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                step <= currentStep ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {step}
              </div>
              {step < 3 && (
                <div className={`w-16 h-1 mx-2 ${
                  step < currentStep ? 'bg-indigo-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2 text-sm text-gray-600">
          <span>Company Info</span>
          <span>Customization</span>
          <span>Admin Account</span>
        </div>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {currentStep === 1 && renderStep1()}
        {currentStep === 2 && renderStep2()}
        {currentStep === 3 && renderStep3()}
        
        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">
            <strong>Error:</strong> {error}
          </div>
        )}
        
        <div className="flex justify-between">
          <button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          
          {currentStep < 3 ? (
            <button
              type="button"
              onClick={nextStep}
              disabled={
                (currentStep === 1 && (!formData.tenantName || !formData.subdomain || !formData.contactEmail)) ||
                (currentStep === 2 && false) // Step 2 has no required fields
              }
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          ) : (
            <button
              type="submit"
              disabled={
                !formData.adminFirstName || 
                !formData.adminLastName || 
                !formData.adminEmail ||
                isRegistering
              }
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRegistering ? 'Creating Account...' : 'Create Account'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

export default TenantRegistration;