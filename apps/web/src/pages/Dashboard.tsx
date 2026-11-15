
import { Link } from "react-router-dom";
import {
  Image,
  AudioLines,
  Video,
  Users,
  Sparkles,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const { user, hasAccess, isAdmin } = useAuth();

  const studios = [
    {
      name: "Image Studio",
      description: "Generate stunning images using AI.",
      path: "/studios/image",
      icon: Image,
      enabled: hasAccess("image"),
    },
    {
      name: "Audio Studio",
      description: "Create music, speech and audio.",
      path: "/studios/audio",
      icon: AudioLines,
      enabled: hasAccess("audio"),
    },
    {
      name: "Video Studio",
      description: "Transform your ideas into videos.",
      path: "/studios/video",
      icon: Video,
      enabled: hasAccess("video"),
    },
  ];

  return (
    <div className="dashboard-page">
      <div className="dashboard-welcome">
        <div>
          <h1>Hello, {user?.name} 👋</h1>
          <p>Welcome to your AI Creative Studio workspace.</p>
        </div>

        <span className="role-badge">
          {isAdmin ? "System Administrator" : "Normal User"}
        </span>
      </div>

      {isAdmin && (
        <Link to="/users" className="admin-link">
          <Users size={20} />
          Manage Users
        </Link>
      )}

      <h2>Your Creative Studios</h2>

      <div className="studio-grid">
        {studios.map((studio) => {
          const Icon = studio.icon;

          return (
            <div className="studio-card" key={studio.name}>
              <div className="studio-icon">
                <Icon size={30} />
              </div>

              <h3>{studio.name}</h3>
              <p>{studio.description}</p>

              {studio.enabled ? (
                <Link to={studio.path} className="studio-link">
                  Open Studio →
                </Link>
              ) : (
                <span className="restricted-label">
                  Access not assigned
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="dashboard-bottom">
        <Sparkles size={20} />
        Create something amazing today.
      </div>
    </div>
  );
}
