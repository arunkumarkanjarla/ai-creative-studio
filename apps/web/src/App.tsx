
import {
  ArrowRight,
  AudioLines,
  Image as ImageIcon,
  Video,
  Sparkles,
  ShieldCheck,
  Zap,
  Menu,
} from "lucide-react";

import "./App.css";

const studios = [
  {
    title: "Image Studio",
    description:
      "Transform your imagination into beautiful images using AI.",
    icon: ImageIcon,
    label: "AI IMAGE GENERATION",
  },
  {
    title: "Audio Studio",
    description:
      "Create voiceovers, music and sound effects from text.",
    icon: AudioLines,
    label: "AI AUDIO GENERATION",
  },
  {
    title: "Video Studio",
    description:
      "Bring your stories to life with video and animation.",
    icon: Video,
    label: "AI VIDEO CREATION",
  },
];

function App() {
  return (
    <div className="app">
      <header className="navbar">
        <a href="#home" className="brand">
          <span className="brand-symbol">
            <Sparkles size={23} />
          </span>
          <span>AI Creative Studio</span>
        </a>

        <nav className="nav-links">
          <a href="#home">Home</a>
          <a href="#studios">Studios</a>
          <a href="#features">Features</a>
        </nav>

        <a href="#studios" className="nav-button">
          Get Started <ArrowRight size={16} />
        </a>

        <button className="mobile-menu" aria-label="Menu">
          <Menu />
        </button>
      </header>

      <main>
        <section className="hero" id="home">
          <div className="hero-content">
            <div className="hero-tag">
              <Sparkles size={14} />
              YOUR ALL-IN-ONE AI CREATIVE WORKSPACE
            </div>

            <h1>
              Imagine It.
              <br />
              <span>Create It With AI.</span>
            </h1>

            <p className="hero-description">
              Unleash your creativity with one powerful platform.
              Generate stunning images, create amazing audio and
              transform ideas into videos — all in one place.
            </p>

            <div className="hero-actions">
              <a href="#studios" className="primary-button">
                Explore Studios <ArrowRight size={18} />
              </a>

              <a href="#features" className="secondary-button">
                Discover Features
              </a>
            </div>

            <div className="hero-trust">
              <span>
                <ShieldCheck size={16} /> Open Source
              </span>
              <span>
                <Zap size={16} /> Local AI
              </span>
              <span>
                <Sparkles size={16} /> Creative Freedom
              </span>
            </div>
          </div>

          <div className="hero-art">
            <div className="art-glow" />

            <div className="art-main">
              <Sparkles size={76} strokeWidth={1.2} />
              <span>CREATE</span>
              <small>WITHOUT LIMITS</small>
            </div>

            <div className="floating-card image-float">
              <ImageIcon size={25} />
              <span>Images</span>
            </div>

            <div className="floating-card audio-float">
              <AudioLines size={25} />
              <span>Audio</span>
            </div>

            <div className="floating-card video-float">
              <Video size={25} />
              <span>Video</span>
            </div>
          </div>
        </section>

        <section className="studios-section" id="studios">
          <div className="section-heading">
            <span className="section-label">YOUR CREATIVE TOOLS</span>
            <h2>Explore Your Studios</h2>
            <p>
              Everything you need to turn your ideas into creative content.
            </p>
          </div>

          <div className="studio-grid">
            {studios.map((studio) => {
              const Icon = studio.icon;

              return (
                <article className="studio-card" key={studio.title}>
                  <div className="studio-card-top">
                    <div className="studio-icon">
                      <Icon size={28} />
                    </div>
                    <span className="coming-soon">Coming Soon</span>
                  </div>

                  <span className="studio-label">{studio.label}</span>
                  <h3>{studio.title}</h3>
                  <p>{studio.description}</p>

                  <a href="#studios" className="studio-link">
                    Explore Studio <ArrowRight size={16} />
                  </a>
                </article>
              );
            })}
          </div>
        </section>

        <section className="features-section" id="features">
          <div>
            <span className="section-label">ONE PLATFORM</span>
            <h2>Your Ideas. Your Creativity. Your Studio.</h2>
            <p>
              A unified creative workspace designed for web and Android,
              powered by open-source AI technologies.
            </p>
          </div>

          <div className="feature-points">
            <div><ShieldCheck /> Privacy-focused architecture</div>
            <div><Zap /> Local AI processing</div>
            <div><Sparkles /> Image, audio and video tools</div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <a href="#home" className="brand">
          <span className="brand-symbol">
            <Sparkles size={20} />
          </span>
          AI Creative Studio
        </a>
        <span>Built with open-source technology.</span>
        <span>© 2026 AI Creative Studio</span>
      </footer>
    </div>
  );
}

export default App;
