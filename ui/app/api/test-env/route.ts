import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({ AUTH_URL: process.env.AUTH_URL });
}
