
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Image,
  AudioLines,
  Video,
  Sparkles,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";

export default function Sidebar() {
  const { hasAccess, isAdmin } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Sparkles size={25} />
        AI Creative Studio
      </div>

      <nav>
        <NavLink to="/dashboard">
          <LayoutDashboard size={19} />
          Dashboard
        </NavLink>

        {isAdmin && (
          <NavLink to="/users">
            <Users size={19} />
            User Management
          </NavLink>
        )}

        {hasAccess("image") && (
          <NavLink to="/studios/image">
            <Image size={19} />
            Image Studio
          </NavLink>
        )}

        {hasAccess("audio") && (
          <NavLink to="/studios/audio">
            <AudioLines size={19} />
            Audio Studio
          </NavLink>
        )}

        {hasAccess("video") && (
          <NavLink to="/studios/video">
            <Video size={19} />
            Video Studio
          </NavLink>
        )}
      </nav>
    </aside>
  );
}
