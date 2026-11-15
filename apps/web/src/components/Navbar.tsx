
import { LogOut, UserCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="app-navbar">
      <div>
        <span className="navbar-title">AI Creative Studio</span>
      </div>

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

        <button onClick={logout} className="logout-button">
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </header>
  );
}
