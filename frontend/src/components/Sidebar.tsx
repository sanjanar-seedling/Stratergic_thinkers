import { NavLink } from "react-router-dom";
import {
  BookOpen,
  BarChart3,
  Target,
  Shield,
  Sprout,
  MessageSquare,
  Settings,
  LogOut,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

const navItems = [
  { to: "/", icon: BookOpen, label: "Journal" },
  { to: "/decisions", icon: Target, label: "Decisions" },
  { to: "/sparring", icon: MessageSquare, label: "Sparring" },
  { to: "/dashboard", icon: BarChart3, label: "Dashboard" },
  { to: "/privacy", icon: Shield, label: "Privacy" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function Sidebar() {
  const { user, logout } = useAuth();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-border bg-sidebar-background">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <Sprout className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-tight gradient-text">
            Seedlings
          </h1>
          <p className="text-[10px] text-muted-foreground tracking-wide uppercase">
            Co-Founder for the Mind
          </p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-smooth",
                isActive
                  ? "bg-sidebar-accent text-sidebar-primary"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User + Footer */}
      <div className="border-t border-border px-4 py-3 space-y-3">
        {/* User info */}
        {user && (
          <div className="flex items-center gap-3 px-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
              <User className="h-4 w-4 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user.display_name}
              </p>
              <p className="text-[10px] text-muted-foreground truncate">
                {user.email}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={logout}
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              id="logout-btn"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Theme Toggle */}
        <div className="px-1 py-2 border-t border-border border-dashed mt-2">
          <ThemeToggle />
        </div>

        {/* Encryption indicator */}
        <div className="glass rounded-lg px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-muted-foreground">
              End-to-end encrypted
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
