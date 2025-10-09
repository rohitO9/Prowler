import { NextRequest, NextResponse } from 'next/server';
import { getApiBaseUrl } from '@/lib/helper';

/**
 * Azure AD Configuration API Route
 * 
 * This route handles Azure AD configuration management for tenants.
 * Only tenant administrators can configure Azure AD settings.
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

    // Get authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Forward the request to the backend
    const response = await fetch(`${apiBaseUrl}/tenant/azure/config`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': host.split('.')[0] || '',
        'Authorization': authHeader,
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to fetch Azure configuration' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Get Azure config error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const host = request.headers.get('host') || '';
    let apiBaseUrl = getApiBaseUrl();
    
    // For subdomain requests, ensure we're calling the correct backend
    if (host.includes('.localhost')) {
      const subdomain = host.split('.')[0];
      apiBaseUrl = `http://${subdomain}.localhost:8080/api/v1`;
    }

    // Get authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Get request body
    const body = await request.json();

    // Forward the request to the backend
    const response = await fetch(`${apiBaseUrl}/tenant/azure/config`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': host.split('.')[0] || '',
        'Authorization': authHeader,
      },
      body: JSON.stringify(body)
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to update Azure configuration' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Update Azure config error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const host = request.headers.get('host') || '';
    let apiBaseUrl = getApiBaseUrl();
    
    // For subdomain requests, ensure we're calling the correct backend
    if (host.includes('.localhost')) {
      const subdomain = host.split('.')[0];
      apiBaseUrl = `http://${subdomain}.localhost:8080/api/v1`;
    }

    // Get authorization header
    const authHeader = request.headers.get('authorization');
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Authorization required' },
        { status: 401 }
      );
    }

    // Forward the request to the backend
    const response = await fetch(`${apiBaseUrl}/tenant/azure/config`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'x-tenant-subdomain': host.split('.')[0] || '',
        'Authorization': authHeader,
      }
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(
        { error: errorData.error || 'Failed to delete Azure configuration' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Delete Azure config error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
