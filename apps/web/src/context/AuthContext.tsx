
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  login as loginService,
  getCurrentUser,
  logout as logoutService,
  type User,
} from "../services/auth";
import {
  storeAuthTokens,
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  refreshAccessToken,
  ensureFocusRefreshListener,
} from "../services/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: (allDevices?: boolean) => void;
  hasAccess: (studio: "image" | "audio" | "video") => boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ensureFocusRefreshListener();

    async function initializeAuth() {
      const token = getAccessToken();
      const refresh = getRefreshToken();

      if (!token && !refresh) {
        setLoading(false);
        return;
      }

      try {
        if (!token && refresh) {
          const ok = await refreshAccessToken();
          if (!ok) {
            clearAuthTokens();
            setLoading(false);
            return;
          }
        }
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch {
        // Access may be expired — try refresh once before giving up
        const ok = await refreshAccessToken();
        if (ok) {
          try {
            const currentUser = await getCurrentUser();
            setUser(currentUser);
          } catch {
            await logoutService();
          }
        } else {
          clearAuthTokens();
        }
      }

      setLoading(false);
    }

    void initializeAuth();
  }, []);

  async function handleLogin(email: string, password: string) {
    const result = await loginService(email, password);

    storeAuthTokens({
      access_token: result.access_token,
      refresh_token: result.refresh_token,
      expires_in: result.expires_in,
    });

    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      await logoutService();
      throw error;
    }
  }

  async function handleLogout(allDevices = false) {
    await logoutService(allDevices);
    setUser(null);
    window.location.href = "/login";
  }

  function hasAccess(
    studio: "image" | "audio" | "video"
  ): boolean {
    if (!user) return false;

    if (user.role === "systemadministrator") {
      return true;
    }

    switch (studio) {
      case "image":
        return user.can_access_image;
      case "audio":
        return user.can_access_audio;
      case "video":
        return user.can_access_video;
      default:
        return false;
    }
  }

  const value: AuthContextType = {
    user,
    loading,
    login: handleLogin,
    logout: handleLogout,
    hasAccess,
    isAdmin: user?.role === "systemadministrator",
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
