import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { isDevHost, getDevTenantApiBaseUrl } from '@/lib/env';

/**
 * Azure AD Login Initiation API Route
 * 
 * This route initiates Azure AD login for the current tenant.
 * It generates the authorization URL and handles the OAuth flow.
 */

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const host = request.headers.get('host') || '';
    const subdomain = getSubdomainFromHost(host);
    let apiBaseUrl = getApiBaseUrl();

    if (isDevHost(host) && subdomain) {
      apiBaseUrl = getDevTenantApiBaseUrl(subdomain);
    }

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const domainHint = searchParams.get('domain_hint');
    const loginHint = searchParams.get('login_hint');

    // Build query parameters for backend
    const queryParams = new URLSearchParams();
    if (domainHint) queryParams.set('domain_hint', domainHint);
    if (loginHint) queryParams.set('login_hint', loginHint);

    const backendUrl = `${apiBaseUrl}/tenant/azure/init${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

    // Forward the request to the backend
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': subdomain || '',
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to initialize Azure login' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Azure init error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
