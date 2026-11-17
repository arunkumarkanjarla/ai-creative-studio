import { useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  Outlet,
  Link,
} from "react-router-dom";
import { Sparkles } from "lucide-react";

import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";

import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import ThemePicker from "./components/ThemePicker";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";

import UserList from "./pages/Users/UserList";
import CreateUser from "./pages/Users/CreateUser";
import EditUser from "./pages/Users/EditUser";

import ImageStudio from "./pages/Studios/ImageStudio";
import AudioStudio from "./pages/Studios/AudioStudio";
import VideoStudio from "./pages/Studios/VideoStudio";

import Register from "./pages/Register";

import AIAccessSettings from "./pages/Admin/AIAccessSettings";
import ImageHistory from "./pages/Admin/ImageHistory";
import ReferenceList from "./pages/Admin/ReferenceList";

import "./App.css";

const SIDEBAR_COLLAPSED_KEY = "acs_sidebar_collapsed";

function MainLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  });

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className={`app-layout${collapsed ? " is-sidebar-collapsed" : ""}`}>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />

      <div className="main-area">
        <Navbar />

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function GuestStudioLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1";
  });

  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className={`app-layout${collapsed ? " is-sidebar-collapsed" : ""}`}>
      <Sidebar
        guestMode
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />

      <div className="main-area">
        <header className="app-navbar">
          <div className="navbar-actions">
            <Link to="/" className="navbar-title-link">
              <Sparkles size={20} />
              <span className="navbar-title">AI Creative Studio</span>
            </Link>
          </div>
          <div className="navbar-actions">
            <ThemePicker />
            <Link to="/login" className="primary-button">
              Sign In
            </Link>
          </div>
        </header>

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function StudioLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="page-loader">Loading...</div>;
  }

  if (user) {
    return <MainLayout />;
  }

  return <GuestStudioLayout />;
}

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route element={<StudioLayout />}>
              <Route path="/studios/image" element={<ImageStudio />} />
              <Route path="/studios/audio" element={<AudioStudio />} />
              <Route path="/studios/video" element={<VideoStudio />} />
            </Route>

            <Route element={<ProtectedRoute />}>
              <Route element={<MainLayout />}>
                <Route path="/dashboard" element={<Dashboard />} />

                <Route element={<AdminRoute />}>
                  <Route path="/users" element={<UserList />} />
                  <Route path="/users/create" element={<CreateUser />} />
                  <Route path="/users/:id/edit" element={<EditUser />} />
                  <Route path="/admin/ai-access" element={<AIAccessSettings />} />
                  <Route path="/admin/images" element={<ImageHistory />} />
                  <Route path="/admin/references" element={<ReferenceList />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

export default App;
