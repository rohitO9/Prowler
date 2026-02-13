/**
 * Central env-based config for dev/production URLs.
 * Use these instead of hardcoding localhost, ports, or domains.
 */

/** Dev domain (hostname) for "is this a dev request?" and building dev URLs. Default: localhost */
export const DEV_DOMAIN =
  process.env.NEXT_PUBLIC_DEV_DOMAIN || process.env.DEV_DOMAIN || "localhost";

/** Backend API port in dev. Default: 8080 */
export const DEV_API_PORT =
  process.env.NEXT_PUBLIC_DEV_API_PORT || process.env.DEV_API_PORT || "8080";

/** Frontend app port in dev (for display/redirects). Default: 3000 */
export const DEV_APP_PORT =
  process.env.NEXT_PUBLIC_DEV_APP_PORT || process.env.DEV_APP_PORT || "3000";

/** Dev app host for display (e.g. "localhost:3000"). */
export const DEV_APP_HOST_DISPLAY = `${DEV_DOMAIN}:${DEV_APP_PORT}`;

/** Whether the given host string is the dev domain (e.g. localhost, tenant1.localhost:3000). */
export function isDevHost(host: string): boolean {
  if (!host) return false;
  const h = host.split(":")[0].toLowerCase();
  return (
    h === DEV_DOMAIN ||
    h.endsWith("." + DEV_DOMAIN) ||
    h === "127.0.0.1" ||
    h === "localhost"
  );
}

/** Default backend API origin in dev (no path). Routes append /api/v1/... Use API_BASE_URL from .env when set. */
export const DEFAULT_DEV_API_BASE_URL = `http://${DEV_DOMAIN}:${DEV_API_PORT}`;

/** Build backend API base URL for a tenant subdomain in dev (e.g. http://tenant1.localhost:8080/api/v1). */
export function getDevTenantApiBaseUrl(subdomain: string): string {
  return `http://${subdomain}.${DEV_DOMAIN}:${DEV_API_PORT}/api/v1`;
}
