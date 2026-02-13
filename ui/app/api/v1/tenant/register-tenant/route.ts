import { NextRequest, NextResponse } from 'next/server';

import { getBackendOrigin } from '@/lib/env';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { 
      company_name, 
      subdomain, 
      admin_email, 
      admin_first_name, 
      admin_last_name, 
      admin_password 
    } = body;

    if (!company_name || !subdomain || !admin_email || !admin_first_name || !admin_last_name || !admin_password) {
      return NextResponse.json({ 
        error: 'Missing required fields' 
      }, { status: 400 });
    }

    const response = await fetch(`${getBackendOrigin()}/api/v1/tenant/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_name,
        subdomain,
        admin_email,
        admin_first_name,
        admin_last_name,
        admin_password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json({ 
        error: data.error || 'Registration failed' 
      }, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error in tenant registration:', error);
    return NextResponse.json({ 
      error: 'Internal server error' 
    }, { status: 500 });
  }
}
