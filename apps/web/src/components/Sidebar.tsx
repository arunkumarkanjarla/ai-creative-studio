import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, useLocation, useSearchParams } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Image,
  Images,
  FileImage,
  AudioLines,
  Video,
  Sparkles,
  Settings2,
  Search,
  Star,
  Pin,
  PanelLeftClose,
  PanelLeftOpen,
  Lock,
  type LucideIcon,
} from "lucide-react";

import { useAuth } from "../context/AuthContext";
import {
  CREATE_TOOLS,
  type StudioToolId,
} from "../pages/Studios/photoStudioConfig";

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
  guestMode?: boolean;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface MenuItem {
  id: string;
  to: string;
  label: string;
  icon: LucideIcon;
  visible: boolean;
}

const FAV_KEY = "acs_menu_favorites";
const PIN_KEY = "acs_menu_pins";

function readIdList(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

function writeIdList(key: string, ids: string[]) {
  localStorage.setItem(key, JSON.stringify(ids));
}

function toolPath(toolId: StudioToolId) {
  return `/studios/image?tool=${toolId}`;
}

export default function Sidebar({
  collapsed = false,
  onToggleCollapsed,
  guestMode = false,
  mobileOpen = false,
  onMobileClose,
}: SidebarProps) {
  const { hasAccess, isAdmin, user } = useAuth();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [favorites, setFavorites] = useState<string[]>(() => readIdList(FAV_KEY));
  const [pins, setPins] = useState<string[]>(() => readIdList(PIN_KEY));
  const [photoOpen, setPhotoOpen] = useState(true);

  const isLoggedIn = Boolean(user);
  const activeTool = (searchParams.get("tool") || "text_to_image") as StudioToolId;
  const onPhotoStudio = location.pathname.startsWith("/studios/image");

  useEffect(() => {
    writeIdList(FAV_KEY, favorites);
  }, [favorites]);

  useEffect(() => {
    writeIdList(PIN_KEY, pins);
  }, [pins]);

  useEffect(() => {
    if (onPhotoStudio) setPhotoOpen(true);
  }, [onPhotoStudio]);

  const items = useMemo<MenuItem[]>(
    () => [
      {
        id: "dashboard",
        to: "/dashboard",
        label: "Dashboard",
        icon: LayoutDashboard,
        visible: !guestMode,
      },
      {
        id: "users",
        to: "/users",
        label: "User Management",
        icon: Users,
        visible: !guestMode && isAdmin,
      },
      {
        id: "ai-access",
        to: "/admin/ai-access",
        label: "AI Access Settings",
        icon: Settings2,
        visible: !guestMode && isAdmin,
      },
      {
        id: "images",
        to: "/admin/images",
        label: "Generated Images",
        icon: Images,
        visible: !guestMode && isAdmin,
      },
      {
        id: "references",
        to: "/admin/references",
        label: "Reference Styles",
        icon: FileImage,
        visible: !guestMode && isAdmin,
      },
      {
        id: "photo",
        to: toolPath("text_to_image"),
        label: "Photo Studio",
        icon: Image,
        visible: guestMode || hasAccess("image"),
      },
      {
        id: "audio",
        to: "/studios/audio",
        label: "Audio Studio",
        icon: AudioLines,
        visible: !guestMode && hasAccess("audio"),
      },
      {
        id: "video",
        to: "/studios/video",
        label: "Video Studio",
        icon: Video,
        visible: !guestMode && hasAccess("video"),
      },
    ],
    [guestMode, hasAccess, isAdmin]
  );

  const visibleItems = items.filter((item) => item.visible);

  const filtered = visibleItems.filter((item) =>
    item.label.toLowerCase().includes(query.trim().toLowerCase())
  );

  const photoTools = CREATE_TOOLS.filter((tool) =>
    tool.label.toLowerCase().includes(query.trim().toLowerCase())
  );

  const pinnedItems = filtered.filter((item) => pins.includes(item.id));
  const favoriteItems = filtered.filter(
    (item) => favorites.includes(item.id) && !pins.includes(item.id)
  );
  const otherItems = filtered.filter(
    (item) => !pins.includes(item.id) && !favorites.includes(item.id)
  );

  function toggleFavorite(id: string) {
    setFavorites((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  }

  function togglePin(id: string) {
    setPins((current) =>
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    );
  }

  function renderPhotoTools() {
    if (!photoOpen && !onPhotoStudio) return null;
    if (collapsed) return null;

    return (
      <div className="sidebar-subnav" aria-label="Photo Studio tools">
        {!query.trim() && (
          <div className="sidebar-group-title">Create & Edit</div>
        )}
        {photoTools.map((tool) => {
          const locked = !isLoggedIn;
          const isActive = onPhotoStudio && activeTool === tool.id;
          return (
            <Link
              key={tool.id}
              to={toolPath(tool.id)}
              title={
                locked
                  ? `${tool.label} (sign in to use)`
                  : tool.label
              }
              aria-current={isActive ? "page" : undefined}
              className={`sidebar-sublink${isActive ? " active" : ""}${
                locked ? " is-locked" : ""
              }`}
              onClick={handleLinkClick}
            >
              <span className="sidebar-sublink-label">{tool.label}</span>
              {tool.badge && <em className="sidebar-badge">{tool.badge}</em>}
              {locked && <Lock size={12} />}
            </Link>
          );
        })}
      </div>
    );
  }

  function renderGroup(title: string, group: MenuItem[]) {
    if (group.length === 0) return null;

    return (
      <div className="sidebar-group">
        {!collapsed && <div className="sidebar-group-title">{title}</div>}
        <div className="sidebar-group-list">
          {group.map((item) => {
            const Icon = item.icon;
            const isFav = favorites.includes(item.id);
            const isPinned = pins.includes(item.id);
            const isPhoto = item.id === "photo";

            return (
              <div className="sidebar-item-stack" key={item.id}>
                <div className="sidebar-item">
                  <NavLink
                    to={item.to}
                    title={item.label}
                    className={({ isActive }) =>
                      `sidebar-link${
                        isPhoto
                          ? onPhotoStudio
                            ? " active"
                            : ""
                          : isActive
                            ? " active"
                            : ""
                      }`
                    }
                    onClick={() => {
                      if (isPhoto) setPhotoOpen(true);
                      handleLinkClick();
                    }}
                  >
                    <Icon size={19} />
                    <span className="sidebar-link-label">{item.label}</span>
                  </NavLink>

                  {!guestMode && (
                    <div className="sidebar-item-actions">
                      <button
                        type="button"
                        className={`sidebar-action${isPinned ? " is-on" : ""}`}
                        title={isPinned ? "Unpin from top" : "Pin to top"}
                        onClick={() => togglePin(item.id)}
                      >
                        <Pin size={14} />
                      </button>
                      <button
                        type="button"
                        className={`sidebar-action${isFav ? " is-on" : ""}`}
                        title={isFav ? "Remove favourite" : "Add to favourites"}
                        onClick={() => toggleFavorite(item.id)}
                      >
                        <Star size={14} fill={isFav ? "currentColor" : "none"} />
                      </button>
                    </div>
                  )}
                </div>
                {isPhoto && renderPhotoTools()}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  const showPhotoInSearch =
    query.trim().length > 0 &&
    photoTools.length > 0 &&
    !filtered.some((item) => item.id === "photo");

  // Close mobile menu when navigating
  const handleLinkClick = () => {
    if (onMobileClose) {
      onMobileClose();
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="mobile-menu-overlay is-open" 
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}
      
      <aside className={`sidebar${collapsed ? " is-collapsed" : ""}${mobileOpen ? " is-open" : ""}`}>
      <div className="sidebar-top">
        <div className="sidebar-brand">
          <Sparkles size={22} />
          <span className="sidebar-brand-text">AI Creative Studio</span>
        </div>

        {onToggleCollapsed && (
          <button
            type="button"
            className="sidebar-collapse-btn"
            title={collapsed ? "Expand menu" : "Collapse menu"}
            aria-label={collapsed ? "Expand menu" : "Collapse menu"}
            onClick={onToggleCollapsed}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        )}
      </div>

      <div className="sidebar-search">
        <Search size={16} />
        <input
          type="search"
          placeholder={collapsed ? "Search" : "Search menus..."}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search menus"
        />
      </div>

      <nav className="sidebar-nav">
        {filtered.length === 0 && photoTools.length === 0 ? (
          <p className="sidebar-empty">No menus found</p>
        ) : (
          <>
            {renderGroup("Pinned", pinnedItems)}
            {renderGroup("Favourites", favoriteItems)}
            {renderGroup(
              pins.length || favorites.length ? "All menus" : "Menus",
              otherItems
            )}
            {showPhotoInSearch && (
              <div className="sidebar-group">
                {!collapsed && (
                  <div className="sidebar-group-title">Photo Studio</div>
                )}
                {renderPhotoTools()}
              </div>
            )}
          </>
        )}
      </nav>
      </aside>
    </>
  );
}
