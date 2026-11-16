
const API_BASE_URL = "http://localhost:8000/api/v1";
export const MEDIA_BASE_URL = "http://localhost:8000";

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

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");

  const headers = new Headers(options.headers);

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(readErrorMessage(error, response.status));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${MEDIA_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}
