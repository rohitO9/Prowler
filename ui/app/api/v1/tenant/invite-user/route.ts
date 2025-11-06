import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    // Get the hostname to determine the tenant
    const hostname = request.headers.get('host') || '';
    console.log('🔍 [invite-user POST] Hostname:', hostname);
    
    // Extract subdomain from hostname like "company1.localhost:3000"
    const subdomain = hostname.split('.')[0];
    console.log('🔍 [invite-user POST] Extracted subdomain:', subdomain);

    // Only reject if it's exactly "localhost" or "127.0.0.1" (main domain)
    if (subdomain === 'localhost' || subdomain === '127.0.0.1') {
      console.log('🔍 [invite-user POST] Rejecting main domain access');
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }
    
    console.log('🔍 [invite-user POST] Using tenant:', subdomain);

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

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/invite-user/`, {
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
