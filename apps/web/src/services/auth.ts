
import {
  apiRequest,
  apiFetch,
  storeAuthTokens,
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  ensureFocusRefreshListener,
} from "./api";

export interface User {
  id: number;
  name: string;
  email: string;
  mobile?: string | null;
  role: "systemadministrator" | "user";
  can_access_image: boolean;
  can_access_audio: boolean;
  can_access_video: boolean;
  is_active: boolean;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
  expires_in?: number;
}

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await apiFetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData,
    skipAuthRefresh: true,
  });

  if (!response.ok) {
    throw new Error("Invalid email or password");
  }

  return response.json();
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export async function logout(allDevices = false): Promise<void> {
  const token = getAccessToken();
  const refreshToken = getRefreshToken();

  if (token || refreshToken) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          refresh_token: refreshToken,
          all_devices: allDevices,
        }),
        skipAuthRefresh: true,
      });
    } catch (error) {
      console.error("Logout API call failed:", error);
    }
  }

  clearAuthTokens();
}

// Attach proactive / focus refresh for long-lived sessions
ensureFocusRefreshListener();
