import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8080';

export async function PATCH(
  request: NextRequest,
  { params }: { params: { userId: string } }
) {
  try {
    const hostname = request.headers.get('host') || '';
    const subdomain = hostname.split('.')[0];

    if (subdomain === 'localhost' || subdomain === '127.0.0.1') {
      return NextResponse.json({ error: 'Invalid tenant context' }, { status: 400 });
    }

    const authHeader = request.headers.get('authorization');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Tenant-Subdomain': subdomain,
    };

    if (authHeader) {
      headers['Authorization'] = authHeader;
    }

    const body = await request.json();

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/users/${params.userId}/permissions/`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ error: data.error || 'Failed to update permissions' }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error updating permissions:', error);
    return NextResponse.json({ error: 'Failed to update permissions' }, { status: 500 });
  }
}

