import { Link } from "react-router-dom";

export default function AuthFooter() {
  const year = new Date().getFullYear();

  return (
    <footer className="auth-site-footer">
      <div className="auth-site-footer-links">
        <Link to="/">Home</Link>
        <Link to="/studios/image">Photo Studio</Link>
        <Link to="/register">Create account</Link>
        <Link to="/login">Sign in</Link>
      </div>
      <p>© {year} AI Creative Studio. All rights reserved.</p>
    </footer>
  );
}
