import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { isDevHost, getDevTenantApiBaseUrl } from '@/lib/env';

/**
 * Authenticated Tenant Information API Route
 * 
 * This route returns detailed tenant information for authenticated users,
 * including their membership details and permissions.
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

    // Forward the request to the backend with proper headers
    const response = await fetch(`${apiBaseUrl}/tenant/info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': request.headers.get('authorization') || '',
        'x-tenant-subdomain': subdomain || '',
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to fetch tenant information' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Tenant info fetch error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}