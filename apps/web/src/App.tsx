
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  Outlet,
} from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";

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

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>

          {/* Public Landing Page */}
          <Route path="/" element={<Home />} />

          {/* Login */}
          <Route path="/login" element={<Login />} />

          {/* Register */}
          <Route path="/register" element={<Register />} />

          {/* Protected Application */}
          <Route element={<ProtectedRoute />}>
            <Route element={<MainLayout />}>

              <Route path="/dashboard" element={<Dashboard />} />

              {/* Administrator Only */}
              <Route element={<AdminRoute />}>
                <Route path="/users" element={<UserList />} />
                <Route path="/users/create" element={<CreateUser />} />
                <Route path="/users/:id/edit" element={<EditUser />} />
              </Route>

              {/* Permission Protected Studios */}
              <Route path="/studios/image" element={<ImageStudio />} />
              <Route path="/studios/audio" element={<AudioStudio />} />
              <Route path="/studios/video" element={<VideoStudio />} />

            </Route>
          </Route>

          {/* Unknown URLs */}
          <Route path="*" element={<Navigate to="/" replace />} />

        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
