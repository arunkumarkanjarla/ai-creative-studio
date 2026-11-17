import { Link } from "react-router-dom";
import {
  Image,
  AudioLines,
  Video,
  Users,
  Sparkles,
  Settings2,
  Images,
  FileImage,
  ArrowRight,
  Wand2,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import { CREATE_TOOLS } from "./Studios/photoStudioConfig";

export default function Dashboard() {
  const { user, hasAccess, isAdmin } = useAuth();

  const studios = [
    {
      name: "Photo Studio",
      description: "Generate and edit photos with AI tools.",
      path: "/studios/image?tool=text_to_image",
      icon: Image,
      enabled: hasAccess("image"),
      tools: CREATE_TOOLS.slice(0, 4).map((tool) => tool.label),
    },
    {
      name: "Audio Studio",
      description: "Create music, speech and audio.",
      path: "/studios/audio",
      icon: AudioLines,
      enabled: hasAccess("audio"),
      tools: ["Speech", "Music", "Sound FX"],
    },
    {
      name: "Video Studio",
      description: "Transform your ideas into videos.",
      path: "/studios/video",
      icon: Video,
      enabled: hasAccess("video"),
      tools: ["Text to Video", "Clip Edit", "Enhance"],
    },
  ];

  const adminCards = [
    {
      name: "User Management",
      description: "Create and manage user access.",
      path: "/users",
      icon: Users,
    },
    {
      name: "AI Access Settings",
      description: "Control studio permissions.",
      path: "/admin/ai-access",
      icon: Settings2,
    },
    {
      name: "Generated Images",
      description: "Review image history and filters.",
      path: "/admin/images",
      icon: Images,
    },
    {
      name: "Reference Styles",
      description: "Manage saved style references.",
      path: "/admin/references",
      icon: FileImage,
    },
  ];

  const quickActions = CREATE_TOOLS.slice(0, 6).map((tool) => ({
    id: tool.id,
    label: tool.label,
    path: `/studios/image?tool=${tool.id}`,
    badge: tool.badge,
  }));

  return (
    <div className="dashboard-page">
      <section className="dashboard-hero-card">
        <div className="dashboard-welcome">
          <div>
            <h1>Hello, {user?.name}</h1>
            <p>Welcome to your AI Creative Studio workspace.</p>
          </div>
          <span className="role-badge">
            {isAdmin ? "System Administrator" : "Normal User"}
          </span>
        </div>
        <div className="dashboard-hero-actions">
          {hasAccess("image") && (
            <Link
              to="/studios/image?tool=text_to_image"
              className="primary-button"
            >
              <Wand2 size={16} />
              Open Photo Studio
            </Link>
          )}
          {isAdmin && (
            <Link to="/users" className="secondary-button">
              <Users size={16} />
              Manage Users
            </Link>
          )}
        </div>
      </section>

      {hasAccess("image") && (
        <section className="dashboard-section-card">
          <div className="dashboard-section-head">
            <h2>Quick Photo Tools</h2>
            <p>Jump into a Create & Edit tool</p>
          </div>
          <div className="dashboard-mini-grid">
            {quickActions.map((action) => (
              <Link
                key={action.id}
                to={action.path}
                className="dashboard-mini-card"
              >
                <span>{action.label}</span>
                {action.badge && <em>{action.badge}</em>}
                <ArrowRight size={14} />
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="dashboard-section-card">
        <div className="dashboard-section-head">
          <h2>Your Creative Studios</h2>
          <p>Open a studio and start creating</p>
        </div>

        <div className="studio-grid">
          {studios.map((studio) => {
            const Icon = studio.icon;

            return (
              <article className="studio-card dashboard-studio-card" key={studio.name}>
                <div className="studio-card-top">
                  <div className="studio-icon">
                    <Icon size={28} />
                  </div>
                  <h3>{studio.name}</h3>
                </div>
                <p>{studio.description}</p>

                <div className="dashboard-nested-cards">
                  {studio.tools.map((tool) => (
                    <div className="dashboard-nested-card" key={tool}>
                      {tool}
                    </div>
                  ))}
                </div>

                {studio.enabled ? (
                  <Link to={studio.path} className="studio-link">
                    Open Studio →
                  </Link>
                ) : (
                  <span className="restricted-label">Access not assigned</span>
                )}
              </article>
            );
          })}
        </div>
      </section>

      {isAdmin && (
        <section className="dashboard-section-card">
          <div className="dashboard-section-head">
            <h2>Admin</h2>
            <p>Manage users, access, and generated assets</p>
          </div>
          <div className="dashboard-admin-grid">
            {adminCards.map((card) => {
              const Icon = card.icon;
              return (
                <Link
                  key={card.path}
                  to={card.path}
                  className="dashboard-admin-card"
                >
                  <div className="studio-icon">
                    <Icon size={22} />
                  </div>
                  <div>
                    <h3>{card.name}</h3>
                    <p>{card.description}</p>
                  </div>
                  <ArrowRight size={16} />
                </Link>
              );
            })}
          </div>
        </section>
      )}

      <div className="dashboard-bottom">
        <Sparkles size={20} />
        Create something amazing today.
      </div>
    </div>
  );
}
