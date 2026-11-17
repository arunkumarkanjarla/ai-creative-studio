
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AuthFooter from "../components/AuthFooter";
import ThemePicker from "../components/ThemePicker";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Login failed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <header className="auth-topbar">
        <Link to="/" className="auth-brand">
          <Sparkles size={28} />
          <span>AI Creative Studio</span>
        </Link>
        <ThemePicker />
      </header>

      <div className="auth-page-body">
        <div className="auth-card">
          <div className="auth-heading">
            <div className="auth-icon">
              <Sparkles size={30} />
            </div>

            <h1>Welcome Back</h1>
            <p>Sign in to your creative workspace</p>
          </div>

          <form onSubmit={handleSubmit}>
            <label>Email Address</label>

            <div className="input-with-icon">
              <Mail size={18} />
              <input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <label>Password</label>

            <div className="input-with-icon">
              <Lock size={18} />
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {error && <div className="error-message">{error}</div>}

            <button
              type="submit"
              className="primary-button full-width"
              disabled={submitting}
            >
              {submitting ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="auth-footer">
            Don't have an account? <Link to="/register">Sign Up</Link>
          </p>

          <Link to="/" className="login-home-link">
            ← Back to Home
          </Link>
        </div>
      </div>

      <AuthFooter />
    </div>
  );
}
