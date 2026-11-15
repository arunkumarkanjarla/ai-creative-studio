
import { Link } from "react-router-dom";
import {
  Sparkles,
  Image,
  AudioLines,
  Video,
  ArrowRight,
  WandSparkles,
  ShieldCheck,
  Zap,
} from "lucide-react";

export default function Home() {
  return (
    <div className="landing-page">
      <header className="landing-header">
        <Link to="/" className="landing-logo">
          <Sparkles size={28} />
          <span>AI Creative Studio</span>
        </Link>

        <nav className="landing-nav">
          <a href="#features">Features</a>
          <a href="#about">About</a>
          <Link to="/login" className="landing-login">
            Sign In <ArrowRight size={16} />
          </Link>
        </nav>
      </header>

      <main>
        <section className="landing-hero">
          <div className="hero-content">
            <div className="hero-badge">
              <Sparkles size={15} />
              Your AI-powered creative workspace
            </div>

            <h1>
              Create Anything.
              <br />
              <span>Imagine Everything.</span>
            </h1>

            <p>
              Bring your ideas to life with AI-powered image, audio
              and video creation. One creative platform for all
              your imagination.
            </p>

            <div className="hero-actions">
              <Link to="/login" className="hero-primary-button">
                Get Started <ArrowRight size={18} />
              </Link>

              <a href="#features" className="hero-secondary-button">
                Explore Features
              </a>
            </div>

            <div className="hero-trust">
              <ShieldCheck size={17} />
              Secure workspace with administrator-managed access
            </div>
          </div>

          <div className="hero-visual">
            <div className="visual-glow"></div>

            <div className="visual-card">
              <div className="visual-card-header">
                <Sparkles size={20} />
                <span>Creative Studio</span>
                <span className="visual-status">Ready</span>
              </div>

              <div className="visual-grid">
                <div className="visual-tile image-tile">
                  <Image size={34} />
                  <span>AI Image</span>
                  <small>Create stunning visuals</small>
                </div>

                <div className="visual-tile audio-tile">
                  <AudioLines size={34} />
                  <span>AI Audio</span>
                  <small>Generate creative sounds</small>
                </div>

                <div className="visual-tile video-tile">
                  <Video size={34} />
                  <span>AI Video</span>
                  <small>Bring stories to life</small>
                </div>

                <div className="visual-tile magic-tile">
                  <WandSparkles size={34} />
                  <span>Unlimited Ideas</span>
                  <small>Your creativity starts here</small>
                </div>
              </div>

              <div className="visual-footer">
                <Zap size={16} />
                Powered by open-source AI technology
              </div>
            </div>
          </div>
        </section>

        <section className="landing-features" id="features">
          <div className="section-heading">
            <span>WHAT YOU CAN CREATE</span>
            <h2>Everything You Need to Create</h2>
            <p>
              Explore creative tools designed to turn your ideas
              into reality.
            </p>
          </div>

          <div className="feature-grid">
            <div className="feature-card">
              <div className="feature-icon image-icon">
                <Image size={27} />
              </div>
              <h3>AI Image Generation</h3>
              <p>
                Transform text descriptions into creative images
                and visual artwork.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon audio-icon">
                <AudioLines size={27} />
              </div>
              <h3>AI Audio Generation</h3>
              <p>
                Create audio content using intelligent
                text-to-audio tools.
              </p>
            </div>

            <div className="feature-card">
              <div className="feature-icon video-icon">
                <Video size={27} />
              </div>
              <h3>AI Video Generation</h3>
              <p>
                Turn your creative concepts into engaging
                AI-generated videos.
              </p>
            </div>
          </div>
        </section>

        <section className="landing-about" id="about">
          <Sparkles size={25} />
          <h2>Your Ideas. Your Creativity. One Studio.</h2>
          <p>
            A unified creative workspace for image, audio and
            video generation, with secure user access.
          </p>
          <Link to="/login" className="hero-primary-button">
            Enter Creative Studio <ArrowRight size={18} />
          </Link>
        </section>
      </main>

      <footer className="landing-footer">
        <span>© 2026 AI Creative Studio</span>
        <span>Create Without Limits.</span>
      </footer>
    </div>
  );
}
