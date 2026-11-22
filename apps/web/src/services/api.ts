import { getVisitorId } from "../utils/visitor";

const API_BASE_URL = "http://localhost:8000/api/v1";
export const MEDIA_BASE_URL = "http://localhost:8000";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const ACCESS_EXPIRES_AT_KEY = "access_token_expires_at";

/** Seconds before access expiry to proactively refresh */
const PROACTIVE_REFRESH_SKEW_MS = 90_000;

type RefreshListener = (ok: boolean) => void;

let refreshPromise: Promise<boolean> | null = null;
let refreshListeners: RefreshListener[] = [];
let proactiveTimer: number | null = null;

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getAccessExpiresAt(): number | null {
  const raw = localStorage.getItem(ACCESS_EXPIRES_AT_KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function storeAuthTokens(params: {
  access_token: string;
  refresh_token?: string | null;
  expires_in?: number | null;
}): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, params.access_token);
  if (params.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, params.refresh_token);
  }
  const expiresIn = params.expires_in ?? 45 * 60;
  const expiresAt = Date.now() + expiresIn * 1000;
  localStorage.setItem(ACCESS_EXPIRES_AT_KEY, String(expiresAt));
  scheduleProactiveRefresh();
}

export function clearAuthTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
  if (proactiveTimer != null) {
    window.clearTimeout(proactiveTimer);
    proactiveTimer = null;
  }
}

function readErrorMessage(error: unknown, status: number): string {
  if (!error || typeof error !== "object") {
    return `Request failed: ${status}`;
  }

  const detail = (error as { detail?: unknown }).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object" && "message" in detail) {
    const info = detail as {
      message: string;
      limit?: number;
      used?: number;
      login_required?: boolean;
    };

    let message = String(info.message);
    if (info.limit != null && info.used != null) {
      message += ` (${info.used}/${info.limit} used)`;
    }
    if (info.login_required) {
      message += " Please sign in, or ask admin to increase guest limit.";
    }
    return message;
  }

  return `Request failed: ${status}`;
}

function notifyRefreshListeners(ok: boolean) {
  const listeners = refreshListeners;
  refreshListeners = [];
  listeners.forEach((fn) => fn(ok));
}

/**
 * Single-flight refresh: concurrent 401s share one /auth/refresh call.
 */
export async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) {
    return refreshPromise;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return false;
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        credentials: "include",
      });

      if (!response.ok) {
        clearAuthTokens();
        notifyRefreshListeners(false);
        return false;
      }

      const data = (await response.json()) as {
        access_token: string;
        refresh_token?: string;
        expires_in?: number;
      };

      storeAuthTokens({
        access_token: data.access_token,
        refresh_token: data.refresh_token ?? refreshToken,
        expires_in: data.expires_in,
      });
      notifyRefreshListeners(true);
      return true;
    } catch {
      clearAuthTokens();
      notifyRefreshListeners(false);
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/** Wait if a refresh is already in flight (used by concurrent callers). */
export function waitForRefresh(): Promise<boolean> {
  if (!refreshPromise) {
    return Promise.resolve(Boolean(getAccessToken()));
  }
  return new Promise((resolve) => {
    refreshListeners.push(resolve);
  });
}

export function scheduleProactiveRefresh(): void {
  if (typeof window === "undefined") return;
  if (proactiveTimer != null) {
    window.clearTimeout(proactiveTimer);
    proactiveTimer = null;
  }
  const expiresAt = getAccessExpiresAt();
  if (!expiresAt || !getRefreshToken()) return;

  const delay = Math.max(5_000, expiresAt - Date.now() - PROACTIVE_REFRESH_SKEW_MS);
  proactiveTimer = window.setTimeout(() => {
    void refreshAccessToken();
  }, delay);
}

let focusListenerAttached = false;

/** Refresh on tab focus when access token is near expiry or already expired. */
export function ensureFocusRefreshListener(): void {
  if (typeof window === "undefined" || focusListenerAttached) return;
  focusListenerAttached = true;
  window.addEventListener("focus", () => {
    const expiresAt = getAccessExpiresAt();
    if (!getRefreshToken()) return;
    if (!expiresAt || expiresAt - Date.now() < PROACTIVE_REFRESH_SKEW_MS) {
      void refreshAccessToken();
    }
  });
  // Kick off scheduling for an already-stored session
  scheduleProactiveRefresh();
}

function redirectToLogin(): void {
  clearAuthTokens();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

function applyAuthHeaders(headers: Headers, token: string | null): void {
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.delete("Authorization");
  }
  headers.set("X-Visitor-Id", getVisitorId());
}

export type ApiFetchOptions = RequestInit & {
  /** Skip 401→refresh→retry (used for login/refresh themselves). */
  skipAuthRefresh?: boolean;
  /** Absolute URL; when set, endpoint is ignored. */
  absoluteUrl?: string;
};

/**
 * Central fetch wrapper: attaches auth, on 401 refreshes once, queues
 * concurrent callers, retries the original request, redirects only if refresh fails.
 */
export async function apiFetch(
  endpointOrUrl: string,
  options: ApiFetchOptions = {}
): Promise<Response> {
  const { skipAuthRefresh, absoluteUrl, ...init } = options;
  const url =
    absoluteUrl ??
    (endpointOrUrl.startsWith("http")
      ? endpointOrUrl
      : `${API_BASE_URL}${endpointOrUrl}`);

  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    // Only set JSON content-type when we have a body that looks like JSON
    if (init.body && typeof init.body === "string") {
      headers.set("Content-Type", "application/json");
    } else if (!init.body) {
      // leave unset for GET
    } else if (!(init.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
  }

  applyAuthHeaders(headers, getAccessToken());

  const doFetch = () =>
    fetch(url, {
      ...init,
      headers,
      credentials: "include",
    });

  let response = await doFetch();

  if (response.status !== 401 || skipAuthRefresh) {
    return response;
  }

  // If another refresh is in flight, wait; otherwise start one
  const refreshed = refreshPromise ? await waitForRefresh() : await refreshAccessToken();
  if (!refreshed) {
    redirectToLogin();
    return response;
  }

  applyAuthHeaders(headers, getAccessToken());
  response = await doFetch();
  if (response.status === 401) {
    redirectToLogin();
  }
  return response;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  const response = await apiFetch(endpoint, { ...options, headers });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(readErrorMessage(error, response.status));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/**
 * Authenticated media/blob fetch against MEDIA_BASE_URL (or absolute path).
 */
export async function apiFetchBlob(path: string): Promise<Blob> {
  const absoluteUrl = path.startsWith("http")
    ? path
    : `${MEDIA_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await apiFetch(absoluteUrl, { absoluteUrl });
  if (!response.ok) {
    throw new Error(`Failed to fetch media: ${response.status}`);
  }
  return response.blob();
}

export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${MEDIA_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
