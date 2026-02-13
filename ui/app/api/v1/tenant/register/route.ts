import { NextRequest, NextResponse } from 'next/server';

import { DEFAULT_DEV_API_BASE_URL } from '@/lib/env';
const API_BASE_URL = process.env.API_BASE_URL || DEFAULT_DEV_API_BASE_URL;

export async function POST(request: NextRequest) {
  console.log('🚀 [API] Tenant register route called');
  
  try {
    const body = await request.json();
    console.log('📝 [API] Request body:', body);
    
    const { 
      company_name, 
      subdomain, 
      admin_email, 
      admin_first_name, 
      admin_last_name, 
      admin_password 
    } = body;

    if (!company_name || !subdomain || !admin_email || !admin_first_name || !admin_last_name || !admin_password) {
      console.log('❌ [API] Missing required fields');
      return NextResponse.json({ 
        error: 'Missing required fields' 
      }, { status: 400 });
    }

    console.log('🔄 [API] Forwarding to backend:', `${API_BASE_URL}/api/v1/tenant/register`);
    
    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/register`, {
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

    console.log('📡 [API] Backend response status:', response.status);
    
    const data = await response.json();
    console.log('📊 [API] Backend response data:', data);

    if (!response.ok) {
      console.log('❌ [API] Backend error:', data.error);
      return NextResponse.json({ 
        error: data.error || 'Registration failed' 
      }, { status: response.status });
    }

    console.log('✅ [API] Registration successful');
    return NextResponse.json(data);
  } catch (error) {
    console.error('💥 [API] Error in tenant registration:', error);
    return NextResponse.json({ 
      error: 'Internal server error' 
    }, { status: 500 });
  }
}
