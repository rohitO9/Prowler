import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';

/**
 * Azure AD Login Initiation API Route
 * 
 * This route initiates Azure AD login for the current tenant.
 * It generates the authorization URL and handles the OAuth flow.
 */

export async function GET(request: NextRequest) {
  try {
    const host = request.headers.get('host') || '';
    let apiBaseUrl = getApiBaseUrl();
    
    // For subdomain requests, ensure we're calling the correct backend
    if (host.includes('.localhost')) {
      const subdomain = host.split('.')[0];
      apiBaseUrl = `http://${subdomain}.localhost:8080/api/v1`;
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
        'x-tenant-subdomain': host.split('.')[0] || '',
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
