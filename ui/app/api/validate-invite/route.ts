import { NextRequest, NextResponse } from 'next/server';

import { DEFAULT_DEV_API_BASE_URL } from '@/lib/env';
const API_BASE_URL = process.env.API_BASE_URL || DEFAULT_DEV_API_BASE_URL;

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const token = searchParams.get('token');

  if (!token) {
    return NextResponse.json({ error: 'Token is required' }, { status: 400 });
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/validate-invite/?token=${token}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Get response as text first to check content
    const responseText = await response.text();
    console.log('Validate invite - Status:', response.status);
    console.log('Validate invite - Headers:', Object.fromEntries(response.headers.entries()));
    console.log('Validate invite - Body (first 500 chars):', responseText.substring(0, 500));

    // Try to parse as JSON (regardless of content-type header)
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error('Failed to parse response as JSON:', parseError);
      console.error('Full response text:', responseText);
      return NextResponse.json({ 
        error: 'Invalid response from server',
        details: responseText.substring(0, 500)
      }, { status: 500 });
    }

    if (!response.ok) {
      // Handle error responses - unwrap if needed
      const errorData = data.data || data;
      return NextResponse.json({ 
        error: errorData.error || errorData.message || 'Invalid invitation',
        details: errorData
      }, { status: response.status });
    }

    // Unwrap JSON API format: {data: {...}} -> {...}
    // DRF JSON API wraps responses in a 'data' object
    const unwrappedData = data.data || data;
    return NextResponse.json(unwrappedData);
  } catch (error) {
    console.error('Error validating invite token:', error);
    return NextResponse.json({ 
      error: 'Failed to validate invitation',
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}
