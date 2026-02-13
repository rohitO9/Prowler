import { NextRequest, NextResponse } from 'next/server';
import { getSubdomainFromHost } from '@/src/utils/subdomain';
import { DEFAULT_DEV_API_BASE_URL } from '@/lib/env';

const API_BASE_URL = process.env.API_BASE_URL || DEFAULT_DEV_API_BASE_URL;

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const hostname = request.headers.get('host') || '';
    const subdomain = getSubdomainFromHost(hostname);

    if (!subdomain) {
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/public-info`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Subdomain': subdomain,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to load tenant info' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error loading tenant info:', error);
    return NextResponse.json({ error: 'Failed to load tenant info' }, { status: 500 });
  }
}
