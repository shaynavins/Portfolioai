const FALLBACK_API_URL = "http://localhost:8000";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || FALLBACK_API_URL
).replace(/\/$/, "");

export const APP_BASE_URL = (
  process.env.NEXT_PUBLIC_APP_URL || ""
).replace(/\/$/, "");

export function buildApiUrl(path: string): string {
  if (!path) {
    return API_BASE_URL;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function buildAppUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (APP_BASE_URL) {
    return `${APP_BASE_URL}${normalizedPath}`;
  }
  if (typeof window !== "undefined") {
    return new URL(normalizedPath, window.location.origin).toString();
  }
  return normalizedPath;
}

export function buildGithubAuthUrl(token?: string): string {
  const url = new URL(buildApiUrl("/api/auth/github"));
  if (token) {
    url.searchParams.set("connect", "1");
    url.searchParams.set("token", token);
  }
  return url.toString();
}
