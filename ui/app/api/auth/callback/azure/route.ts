"use server";

import { NextResponse } from "next/server";

import { signIn } from "@/auth.config";
import { apiBaseUrl, baseUrl } from "@/lib/helper";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);

  const code = searchParams?.get("code");

  const params = new URLSearchParams();
  params.append("code", code || "");

  if (!code) {
    return NextResponse.json(
      { error: "Authorization code is missing" },
      { status: 400 },
    );
  }

  try {
    const response = await fetch(`${apiBaseUrl}/tokens/azure`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    if (!response.ok) {
      throw new Error("Failed to exchange code for tokens");
    }

    const data = await response.json();
    console.log("data", data);
    
    // Fix: The tokens are in data.data, not data.data.attributes
    const { access, refresh } = data?.data;

    // Add validation to ensure tokens exist
    if (!access || !refresh) {
      throw new Error("Access token or refresh token is missing from response");
    }

    // Validate token format (JWT tokens should have 3 parts separated by dots)
    if (!access.includes('.') || access.split('.').length !== 3) {
      throw new Error("Invalid access token format");
    }

    if (!refresh.includes('.') || refresh.split('.').length !== 3) {
      throw new Error("Invalid refresh token format");
    }

    console.log("Tokens appear to have valid JWT format, proceeding with authentication...");

    try {
      console.log("Attempting to sign in with tokens:", { 
        accessTokenLength: access?.length, 
        refreshTokenLength: refresh?.length 
      });

      const result = await signIn("social-oauth", {
        accessToken: access,
        refreshToken: refresh,
        redirect: false,
        callbackUrl: `${baseUrl}/`,
      });

      console.log("SignIn result:", result);

      if (result?.error) {
        console.error("SignIn result error:", result.error);
        throw new Error(result.error);
      }

      return NextResponse.redirect(new URL("/", baseUrl));
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error("SignIn error details:", {
        message: (error as Error).message,
        stack: (error as Error).stack,
        error
      });
      return NextResponse.redirect(
        new URL(`/sign-in?error=AuthenticationFailed&details=${encodeURIComponent((error as Error).message)}`, baseUrl),
      );
    }
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Error in Azure callback:", error);
    return NextResponse.json(
      { error: (error as Error).message },
      { status: 500 },
    );
  }
}