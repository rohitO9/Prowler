import { jwtDecode, JwtPayload } from "jwt-decode";
import NextAuth, { type NextAuthConfig, User } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import AzureAD from "next-auth/providers/azure-ad";
import { z } from "zod";

import { getToken, getUserByMe } from "./actions/auth";
import { apiBaseUrl } from "./lib";

interface CustomJwtPayload extends JwtPayload {
  user_id: string;
  tenant_id: string;
  tenant_name?: string;
  tenant_prefix?: string;
  tenant_suffix?: string;
}

const refreshAccessToken = async (token: JwtPayload) => {
  const url = new URL(`${apiBaseUrl}/tenant/refresh-token`);

  const bodyData = {
    data: {
      type: "tokens-refresh",
      attributes: {
        refresh: (token as any).refreshToken,
      },
    },
  };

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/vnd.api+json",
        Accept: "application/vnd.api+json",
      },
      body: JSON.stringify(bodyData),
    });
    const newTokens = await response.json();

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return {
      ...token,
      accessToken: newTokens.data.attributes.access,
      refreshToken: newTokens.data.attributes.refresh,
    };
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Error refreshing access token:", error);
    return {
      error: "RefreshAccessTokenError",
    };
  }
};

export const authConfig = {
  trustHost: true,
  secret: process.env.NEXTAUTH_SECRET || "development-secret-key-change-in-production",
  session: {
    strategy: "jwt",
    // The session will be valid for 24 hours
    maxAge: 24 * 60 * 60,
  },
  pages: {
    signIn: "/sign-in",
    newUser: "/sign-up",
  },
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "email", type: "text" },
        password: { label: "password", type: "password" },
      },
      async authorize(credentials, req) {
        const parsedCredentials = z
          .object({
            email: z.string().email(),
            password: z.string().min(8), // Reduced from 12 to 8 to match user's password
            tenant_name: z.string().optional(),
          })
          .safeParse(credentials);

        if (!parsedCredentials.success) {
          console.error("🔍 [NextAuth] Credentials validation failed:", parsedCredentials.error);
          return null;
        }

        console.log("NextAuth authorize called with:", {
          email: parsedCredentials.data.email,
          password: "***",
          tenant_name: parsedCredentials.data.tenant_name
        });

        // Forward optional tenant_name to backend for enterprise multi-tenant login
        // Try to get host from request context if available
        const host = req?.headers?.get?.('host') || req?.headers?.host;
        console.log("🔍 [NextAuth] Host from request:", host);
        
        let tokenResponse;
        try {
          tokenResponse = await getToken(parsedCredentials.data as any, host);
          console.log("🔍 [NextAuth] Token response:", tokenResponse ? "SUCCESS" : "FAILED");
          if (!tokenResponse) {
            console.error("🔍 [NextAuth] getToken returned null");
            return null;
          }
        } catch (error) {
          console.error("🔍 [NextAuth] getToken error:", error);
          return null;
        }

        const userMeResponse = await getUserByMe(tokenResponse.accessToken, host);

        const user = {
          name: userMeResponse.name,
          email: userMeResponse.email,
          company: userMeResponse?.company,
          dateJoined: userMeResponse.dateJoined,
        };

        return {
          ...user,
          accessToken: tokenResponse.accessToken,
          refreshToken: tokenResponse.refreshToken,
        };
      },
    }),
    AzureAD({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
      authorization: {
        params: {
          scope: "openid profile email User.Read",
        },
      },
    }),
    Credentials({
      id: "social-oauth",
      name: "social-oauth",
      credentials: {
        accessToken: { label: "Access Token", type: "text" },
        refreshToken: { label: "Refresh Token", type: "text" },
      },
      async authorize(credentials) {
        const accessToken = credentials?.accessToken;

        if (!accessToken) {
          return null;
        }

        try {
          const userMeResponse = await getUserByMe(accessToken as string);

          const user = {
            name: userMeResponse.name,
            email: userMeResponse.email,
            company: userMeResponse?.company,
            dateJoined: userMeResponse.dateJoined,
          };

          return {
            ...user,
            accessToken: credentials.accessToken,
            refreshToken: credentials.refreshToken,
          };
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error("Error in authorize:", error);
          return null;
        }
      },
    }),
  ],
  callbacks: {
    redirect({ url, baseUrl }) {
      // If it's a relative URL, make it absolute
      if (url.startsWith("/")) {
        return `${baseUrl}${url}`;
      }
      // If it's the same origin, allow it
      else if (new URL(url).origin === baseUrl) {
        return url;
      }
      // Otherwise redirect to home (authenticated dashboard)
      return `${baseUrl}/home`;
    },

    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const pathname = nextUrl.pathname;
      
      // Public routes that don't require authentication
      const publicRoutes = ['/register', '/verify-tenant', '/sign-up', '/azure', '/sign-in'];
      const isPublicRoute = publicRoutes.some(route => pathname.startsWith(route));
      
      // Allow access to public routes
      if (isPublicRoute) return true;
      
      // For root path, allow access (landing page)
      if (pathname === '/') return true;
      
      // For all other routes, require authentication
      if (isLoggedIn) return true;
      return false; // Redirect users who are not logged in to the login page
    },

    jwt: async ({ token, account, user }) => {
      if (token?.accessToken) {
        const decodedToken = jwtDecode(
          token.accessToken as string,
        ) as CustomJwtPayload;
        // eslint-disable-next-line no-console
        // console.log("decodedToken", decodedToken);
        token.accessTokenExpires = (decodedToken.exp as number) * 1000;
        token.user_id = decodedToken.user_id;
        token.tenant_id = decodedToken.tenant_id;
        token.tenant_name = decodedToken.tenant_name;
        token.tenant_prefix = decodedToken.tenant_prefix;
        token.tenant_suffix = decodedToken.tenant_suffix;
      }

      const userInfo = {
        name: user?.name,
        companyName: user?.company,
        email: user?.email,
        dateJoined: user?.dateJoined,
      };

      if (account && user) {
        return {
          ...token,
          userId: token.user_id,
          tenantId: token.tenant_id,
          tenantName: (token as any).tenant_name,
          tenantPrefix: (token as any).tenant_prefix,
          tenantSuffix: (token as any).tenant_suffix,
          accessToken: (user as User & { accessToken: JwtPayload }).accessToken,
          refreshToken: (user as User & { refreshToken: JwtPayload })
            .refreshToken,
          user: userInfo,
        };
      }

      // eslint-disable-next-line no-console
      // console.log(
      //   "Access token expires",
      //   token.accessTokenExpires,
      //   new Date(Number(token.accessTokenExpires)),
      // );

      // If the access token is not expired, return the token
      if (
        typeof token.accessTokenExpires === "number" &&
        Date.now() < token.accessTokenExpires
      )
        return token;

      // If the access token is expired, try to refresh it
      return refreshAccessToken(token as JwtPayload);
    },

    session: async ({ session, token }) => {
      if (token) {
        session.userId = token?.user_id as string;
        session.tenantId = token?.tenant_id as string;
        session.accessToken = token?.accessToken as string;
        session.refreshToken = token?.refreshToken as string;
        session.user = token.user as any;
        (session as any).tenantName = (token as any).tenant_name;
        (session as any).tenantPrefix = (token as any).tenant_prefix;
        (session as any).tenantSuffix = (token as any).tenant_suffix;
      }

      // console.log("session", session);
      return session;
    },
  },
} satisfies NextAuthConfig;

export const { signIn, signOut, auth, handlers } = NextAuth(authConfig);
