import { NextRequest, NextResponse } from 'next/server';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { getBackendOrigin } from '@/lib/env';

export async function POST(request: NextRequest) {
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

    // Get the request body
    const body = await request.json();

    const response = await fetch(`${getBackendOrigin()}/api/v1/tenant/invite-user/`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to invite user' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error inviting user:', error);
    return NextResponse.json({ error: 'Failed to invite user' }, { status: 500 });
  }
}
