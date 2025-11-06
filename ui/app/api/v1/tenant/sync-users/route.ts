import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    // Get the hostname to determine the tenant
    const hostname = request.headers.get('host') || '';
    console.log('🔍 [sync-users POST] Hostname:', hostname);
    
    // Extract subdomain from hostname like "company1.localhost:3000"
    const subdomain = hostname.split('.')[0];
    console.log('🔍 [sync-users POST] Extracted subdomain:', subdomain);

    // Only reject if it's exactly "localhost" or "127.0.0.1" (main domain)
    if (subdomain === 'localhost' || subdomain === '127.0.0.1') {
      console.log('🔍 [sync-users POST] Rejecting main domain access');
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }
    
    console.log('🔍 [sync-users POST] Using tenant:', subdomain);

    // Get authorization header for authenticated requests
    const authHeader = request.headers.get('authorization');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Tenant-Subdomain': subdomain,
    };

    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/sync-users/`, {
      method: 'POST',
      headers,
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to sync users' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error syncing users:', error);
    return NextResponse.json({ error: 'Failed to sync users' }, { status: 500 });
  }
}