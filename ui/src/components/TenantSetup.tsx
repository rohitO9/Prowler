import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface TenantSetupProps {
  onSetupComplete?: (subdomain: string) => void;
}

const TenantSetup: React.FC<TenantSetupProps> = ({ onSetupComplete }) => {
  const [companyName, setCompanyName] = useState('');
  const [subdomain, setSubdomain] = useState('');
  const [isCheckingAvailability, setIsCheckingAvailability] = useState(false);
  const [isSubdomainAvailable, setIsSubdomainAvailable] = useState<boolean | null>(null);
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const navigate = useNavigate();

  const checkSubdomainAvailability = async () => {
    if (!subdomain) return;
    
    setIsCheckingAvailability(true);
    try {
      const response = await fetch(`/api/v1/tenant/check-subdomain?subdomain=${subdomain}`);
      const data = await response.json();
      
      if (response.ok) {
        setIsSubdomainAvailable(data.data.attributes.available);
      } else {
        setError(data.errors?.[0]?.detail || 'Failed to check subdomain availability');
      }
    } catch (err) {
      setError('Network error while checking subdomain');
    } finally {
      setIsCheckingAvailability(false);
    }
  };

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!companyName || !subdomain) {
      setError('Please fill in all fields');
      return;
    }
    
    if (isSubdomainAvailable === false) {
      setError('Subdomain is not available');
      return;
    }
    
    setIsSettingUp(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/tenant/setup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/vnd.api+json',
        },
        body: JSON.stringify({
          data: {
            type: 'tenants',
            attributes: {
              name: companyName,
              subdomain: subdomain,
            },
          },
        }),
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // Redirect to the new subdomain
        const newUrl = `http://${subdomain}.localhost:3000`;
        if (onSetupComplete) {
          onSetupComplete(subdomain);
        } else {
          window.location.href = newUrl;
        }
      } else {
        setError(data.errors?.[0]?.detail || 'Failed to setup tenant');
      }
    } catch (err) {
      setError('Network error while setting up tenant');
    } finally {
      setIsSettingUp(false);
    }
  };

  return (
    <div className="max-w-md mx-auto mt-8 p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6 text-center">Setup Your Company</h2>
      
      <form onSubmit={handleSetup} className="space-y-4">
        <div>
          <label htmlFor="companyName" className="block text-sm font-medium text-gray-700">
            Company Name
          </label>
          <input
            type="text"
            id="companyName"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Enter your company name"
            required
          />
        </div>
        
        <div>
          <label htmlFor="subdomain" className="block text-sm font-medium text-gray-700">
            Subdomain
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              id="subdomain"
              value={subdomain}
              onChange={(e) => {
                setSubdomain(e.target.value.toLowerCase().replace(/[^a-z0-9-_]/g, ''));
                setIsSubdomainAvailable(null);
              }}
              className="flex-1 mt-1 block px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="your-company"
              required
            />
            <button
              type="button"
              onClick={checkSubdomainAvailability}
              disabled={!subdomain || isCheckingAvailability}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
            >
              {isCheckingAvailability ? 'Checking...' : 'Check'}
            </button>
          </div>
          <div className="mt-1 text-sm text-gray-500">
            Your URL will be: <strong>{subdomain}.localhost:3000</strong>
          </div>
          {isSubdomainAvailable !== null && (
            <div className={`mt-1 text-sm ${
              isSubdomainAvailable ? 'text-green-600' : 'text-red-600'
            }`}>
              {isSubdomainAvailable ? '✓ Available' : '✗ Not available'}
            </div>
          )}
        </div>
        
        {error && (
          <div className="text-red-600 text-sm">{error}</div>
        )}
        
        <button
          type="submit"
          disabled={!companyName || !subdomain || isSubdomainAvailable === false || isSettingUp}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
        >
          {isSettingUp ? 'Setting up...' : 'Setup Company'}
        </button>
      </form>
    </div>
  );
};

export default TenantSetup;
