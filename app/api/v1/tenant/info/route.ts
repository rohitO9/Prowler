import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Get the subdomain from the request
    const host = request.headers.get('host') || '';
    
    // Get authorization header from the request
    const authHeader = request.headers.get('authorization');
    
    // Extract subdomain and construct the correct API URL
    let apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8080/api/v1';
    
    // If we have a subdomain, use it for the API call
    if (host.includes('.localhost')) {
      const subdomain = host.split('.')[0];
      apiBaseUrl = `http://${subdomain}.localhost:8080/api/v1`;
    }
    
    // Forward the request to Django API with the subdomain
    const djangoUrl = `${apiBaseUrl}/tenant/info`;
    
    console.log('Proxying request to:', djangoUrl);
    console.log('Original host:', host);
    
    const response = await fetch(djangoUrl, {
      method: 'GET',
      headers: {
        'Host': host, // Forward the original host with subdomain
        'Accept': 'application/vnd.api+json',
        'Content-Type': 'application/vnd.api+json',
        ...(authHeader && { 'Authorization': authHeader }),
      },
    });

    const data = await response.json();
    
    return NextResponse.json(data, { 
      status: response.status,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      }
    });
  } catch (error) {
    console.error('API proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}