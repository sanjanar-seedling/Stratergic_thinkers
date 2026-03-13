import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import api from "@/services/api";

interface User {
  id: string;
  email: string;
  display_name: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    localStorage.getItem("seedlings_token")
  );
  const [isLoading, setIsLoading] = useState(true);

  // On mount, check if we have a valid token
  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem("seedlings_token");
      if (storedToken) {
        try {
          const response = await api.get("/auth/me");
          setUser(response.data);
          setToken(storedToken);
        } catch {
          localStorage.removeItem("seedlings_token");
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await api.post("/auth/login", { email, password });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("seedlings_token", access_token);
    setToken(access_token);
    setUser(userData);
  };

  const signup = async (email: string, password: string, displayName: string) => {
    const response = await api.post("/auth/signup", {
      email,
      password,
      display_name: displayName,
    });
    const { access_token, user: userData } = response.data;
    localStorage.setItem("seedlings_token", access_token);
    setToken(access_token);
    setUser(userData);
  };

  const logout = () => {
    localStorage.removeItem("seedlings_token");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
