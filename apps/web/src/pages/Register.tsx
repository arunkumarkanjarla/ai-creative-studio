
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sparkles,
  User,
  Mail,
  Phone,
  Lock,
  Eye,
  EyeOff,
} from "lucide-react";

export default function Register() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      const response = await fetch(
        "http://localhost:8000/api/v1/auth/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            email,
            mobile: mobile || null,
            password,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Registration failed.");
      }

      navigate("/login", {
        state: {
          successMessage:
            "Account created successfully. Please sign in.",
        },
      });

    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to create account."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <Link to="/" className="auth-brand">
        <Sparkles size={30} />
        <span>AI Creative Studio</span>
      </Link>

      <div className="auth-card">
        <div className="auth-heading">
          <div className="auth-icon">
            <Sparkles size={30} />
          </div>

          <h1>Create Account</h1>
          <p>Join AI Creative Studio and start creating</p>
        </div>

        <form onSubmit={handleSubmit}>
          <label>Full Name</label>
          <div className="input-with-icon">
            <User size={18} />
            <input
              type="text"
              placeholder="Enter your full name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              minLength={2}
              maxLength={150}
              required
            />
          </div>

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

          <label>Mobile Number (Optional)</label>
          <div className="input-with-icon">
            <Phone size={18} />
            <input
              type="tel"
              placeholder="Enter your mobile number"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              maxLength={20}
            />
          </div>

          <label>Password</label>
          <div className="input-with-icon">
            <Lock size={18} />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Minimum 12 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={12}
              maxLength={128}
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

          <label>Confirm Password</label>
          <div className="input-with-icon">
            <Lock size={18} />
            <input
              type="password"
              placeholder="Re-enter your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div className="error-message">{error}</div>
          )}

          <button
            type="submit"
            className="primary-button full-width"
            disabled={submitting}
          >
            {submitting ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <p className="auth-footer">
          Already have an account?{" "}
          <Link to="/login">Sign In</Link>
        </p>

        <Link to="/" className="login-home-link">
          ← Back to Home
        </Link>
      </div>
    </div>
  );
}
