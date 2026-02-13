import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { isDevHost, getDevTenantApiBaseUrl } from '@/lib/env';

/**
 * Tenant Access Validation API Route
 * 
 * This route validates that the current user has access to the specified tenant.
 * It's called by the frontend to ensure proper tenant isolation.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { tenant_subdomain } = body;
    
    if (!tenant_subdomain) {
      return NextResponse.json(
        { error: 'Tenant subdomain required' },
        { status: 400 }
      );
    }

    const host = request.headers.get('host') || '';
    const subdomainFromHost = getSubdomainFromHost(host);
    let apiBaseUrl = getApiBaseUrl();

    if (isDevHost(host) && subdomainFromHost) {
      apiBaseUrl = getDevTenantApiBaseUrl(subdomainFromHost);
    }

    // Forward the request to the backend with proper headers
    const response = await fetch(`${apiBaseUrl}/tenant/validate-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'x-tenant-subdomain': tenant_subdomain,
      },
      body: JSON.stringify({
        tenant_subdomain
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Tenant access validation failed' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Tenant access validation error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
