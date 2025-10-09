import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';

/**
 * Azure AD Callback API Route
 * 
 * This route handles the Azure AD OAuth callback and completes authentication.
 * It exchanges the authorization code for tokens and creates/links the user.
 */

export async function POST(request: NextRequest) {
  try {
    const host = request.headers.get('host') || '';
    let apiBaseUrl = getApiBaseUrl();
    
    // For subdomain requests, ensure we're calling the correct backend
    if (host.includes('.localhost')) {
      const subdomain = host.split('.')[0];
      apiBaseUrl = `http://${subdomain}.localhost:8080/api/v1`;
    }

    // Get request body
    const body = await request.json();
    const { code, state } = body;

    if (!code) {
      return NextResponse.json(
        { error: 'Authorization code is required' },
        { status: 400 }
      );
    }

    // Forward the request to the backend
    const response = await fetch(`${apiBaseUrl}/tenant/azure/callback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': host.split('.')[0] || '',
      },
      body: JSON.stringify({ code, state })
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Authentication failed' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Azure callback error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
