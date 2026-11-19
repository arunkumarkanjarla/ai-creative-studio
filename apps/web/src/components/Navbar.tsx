import { LogOut, Menu, UserCircle } from "lucide-react";

import { useAuth } from "../context/AuthContext";
import ThemePicker from "./ThemePicker";

interface NavbarProps {
  onMobileMenuToggle?: () => void;
}

export default function Navbar({ onMobileMenuToggle }: NavbarProps) {
  const { user, logout } = useAuth();

  return (
    <header className="app-navbar">
      <div className="navbar-actions">
        {onMobileMenuToggle && (
          <button 
            type="button"
            className="mobile-menu-toggle" 
            onClick={onMobileMenuToggle}
            aria-label="Toggle menu"
          >
            <Menu size={20} />
          </button>
        )}
        <span className="navbar-title">AI Creative Studio</span>
      </div>

      <div className="navbar-actions">
        <ThemePicker />

        <div className="navbar-user">
          <UserCircle size={22} />

          <div>
            <strong>{user?.name}</strong>
            <small>
              {user?.role === "systemadministrator"
                ? "System Administrator"
                : "Normal User"}
            </small>
          </div>

          <button onClick={logout} className="logout-button" type="button">
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
