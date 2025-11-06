import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { token, user_data } = body;

    if (!token) {
      return NextResponse.json({ error: 'Token is required' }, { status: 400 });
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/tenant/accept-invite/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token,
        user_data: user_data || {}
      }),
    });

    // Get response as text first (can only read once)
    const responseText = await response.text();
    
    // Try to parse as JSON
    let data;
    try {
      data = JSON.parse(responseText);
    } catch (parseError) {
      console.error('Failed to parse accept invite response:', parseError);
      console.error('Response text:', responseText);
      return NextResponse.json({ 
        error: 'Invalid response from server',
        details: responseText.substring(0, 500)
      }, { status: 500 });
    }

    if (!response.ok) {
      // Handle error responses - unwrap if needed
      const errorData = data.data || data;
      return NextResponse.json({ 
        error: errorData.error || errorData.message || 'Failed to accept invitation',
        details: errorData
      }, { status: response.status });
    }

    // Unwrap JSON API format: {data: {...}} -> {...}
    const unwrappedData = data.data || data;
    return NextResponse.json(unwrappedData);
  } catch (error) {
    console.error('Error accepting invite:', error);
    return NextResponse.json({ error: 'Failed to accept invitation' }, { status: 500 });
  }
}
