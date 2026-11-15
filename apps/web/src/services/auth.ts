
import { apiRequest } from "./api";

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
}

export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const formData = new URLSearchParams();

  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(
    "http://localhost:8000/api/v1/auth/login",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error("Invalid email or password");
  }

  return response.json();
}

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export function logout(): void {
  localStorage.removeItem("access_token");
}
