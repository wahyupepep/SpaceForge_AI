import { apiClient } from "@/services/api-client";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export const authService = {
  me(): Promise<{ user: AuthUser }> {
    return apiClient.request("/auth/me", { cache: "no-store" });
  },
  login(email: string, password: string): Promise<{ user: AuthUser }> {
    return apiClient.request("/auth/login", { method: "POST", body: { email, password } });
  },
  register(displayName: string, email: string, password: string): Promise<{ user: AuthUser }> {
    return apiClient.request("/auth/register", {
      method: "POST",
      body: { display_name: displayName, email, password },
    });
  },
  logout(): Promise<void> {
    return apiClient.request("/auth/logout", { method: "POST" });
  },
};
