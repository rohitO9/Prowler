import { NextRequest, NextResponse } from 'next/server';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { DEFAULT_DEV_API_BASE_URL } from '@/lib/env';

const API_BASE_URL = process.env.API_BASE_URL || DEFAULT_DEV_API_BASE_URL;

export async function GET(request: NextRequest) {
  try {
    const hostname = request.headers.get('host') || '';
    const subdomain = getSubdomainFromHost(hostname);

    if (!subdomain) {
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }

    // Get authorization header for authenticated requests
    const authHeader = request.headers.get('authorization');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Tenant-Subdomain': subdomain,
    };

    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/sso-config/`, {
      method: 'GET',
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to load SSO config' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error loading SSO config:', error);
    return NextResponse.json({ error: 'Failed to load SSO config' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { azure_tenant_id, client_id, client_secret } = body;

    if (!azure_tenant_id || !client_id || !client_secret) {
      return NextResponse.json({ 
        error: 'Missing required fields: azure_tenant_id, client_id, client_secret' 
      }, { status: 400 });
    }

    const hostname = request.headers.get('host') || '';
    const subdomain = getSubdomainFromHost(hostname);

    if (!subdomain) {
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }

    // Get authorization header for authenticated requests
    const authHeader = request.headers.get('authorization');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Tenant-Subdomain': subdomain,
    };

    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/setup-azure-sso/`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        azure_tenant_id,
        client_id,
        client_secret
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to setup SSO' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error setting up SSO:', error);
    return NextResponse.json({ error: 'Failed to setup SSO' }, { status: 500 });
  }
}
