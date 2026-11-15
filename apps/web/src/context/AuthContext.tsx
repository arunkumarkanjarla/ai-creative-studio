
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
  
  interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
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
      async function initializeAuth() {
        const token = localStorage.getItem("access_token");
  
        if (token) {
          try {
            const currentUser = await getCurrentUser();
            setUser(currentUser);
          } catch {
            logoutService();
          }
        }
  
        setLoading(false);
      }
  
      initializeAuth();
    }, []);
  
    async function handleLogin(email: string, password: string) {
      const result = await loginService(email, password);
  
      localStorage.setItem("access_token", result.access_token);
  
      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
      } catch (error) {
        logoutService();
        throw error;
      }
    }
  
    function handleLogout() {
      logoutService();
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
  