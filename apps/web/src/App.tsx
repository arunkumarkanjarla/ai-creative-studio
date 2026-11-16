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

import ProtectedRoute from "./components/ProtectedRoute";
import AdminRoute from "./components/AdminRoute";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";

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

function MainLayout() {
  return (
    <div className="app-layout">
      <Sidebar />

      <div className="main-area">
        <Navbar />

        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

/* Studios are open to guests and logged-in users. */
function StudioLayout() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="page-loader">Loading...</div>;
  }

  if (user) {
    return <MainLayout />;
  }

  return (
    <div className="public-studio-page">
      <header className="public-studio-header">
        <Link to="/" className="landing-logo">
          <Sparkles size={24} />
          <span>AI Creative Studio</span>
        </Link>

        <Link to="/login" className="landing-login">
          Sign In
        </Link>
      </header>

      <main className="public-studio-content">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Public + logged-in studio pages with text prompt */}
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
    </BrowserRouter>
  );
}

export default App;
