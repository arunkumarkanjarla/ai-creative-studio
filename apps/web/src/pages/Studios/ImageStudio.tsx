import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  Image as ImageIcon,
  Lock,
  Sparkles,
  Upload,
} from "lucide-react";

import GenerationProgress from "../../components/GenerationProgress";
import { useAuth } from "../../context/AuthContext";
import { apiRequest, mediaUrl } from "../../services/api";
import {
  CREATE_TOOLS,
  DIMENSIONS,
  PHOTO_STYLES,
  PHOTO_TYPES,
  SCENES,
  buildToolPrompt,
  type StudioToolId,
} from "./photoStudioConfig";

interface GeneratedItem {
  id: number;
  prompt: string;
  status: string;
  image_url: string | null;
  generation_time_seconds: number | null;
  created_at: string;
  error_message: string | null;
}

interface HistoryResponse {
  total: number;
  items: GeneratedItem[];
}

interface JobStartResponse {
  job_id: number;
  status: string;
  progress: number;
  message: string;
}

interface JobStatusResponse {
  job_id: number;
  status: string;
  progress: number;
  message: string;
  image_url: string | null;
  error: string | null;
  result: GeneratedItem | null;
}

function useObjectUrl(file: File | null) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file) {
      setUrl(null);
      return;
    }
    const next = URL.createObjectURL(file);
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);
  return url;
}

export default function ImageStudio() {
  const { user } = useAuth();
  const isLoggedIn = Boolean(user);

  const [toolId, setToolId] = useState<StudioToolId>("text_to_image");
  const [prompt, setPrompt] = useState("");
  const [image1, setImage1] = useState<File | null>(null);
  const [image2, setImage2] = useState<File | null>(null);
  const [image1Key, setImage1Key] = useState(0);
  const [image2Key, setImage2Key] = useState(0);
  const [dimensionId, setDimensionId] = useState<(typeof DIMENSIONS)[number]["id"]>("3:4");
  const [photoType, setPhotoType] = useState<(typeof PHOTO_TYPES)[number]["id"]>("album");
  const [style, setStyle] = useState<(typeof PHOTO_STYLES)[number]>("Realistic");
  const [scene, setScene] = useState<(typeof SCENES)[number]>("Beach");

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState("");
  const [latest, setLatest] = useState<GeneratedItem | null>(null);
  const [history, setHistory] = useState<GeneratedItem[]>([]);

  const image1Preview = useObjectUrl(image1);
  const image2Preview = useObjectUrl(image2);

  const tool = useMemo(
    () => CREATE_TOOLS.find((item) => item.id === toolId) || CREATE_TOOLS[0],
    [toolId]
  );

  const dimension = useMemo(
    () => DIMENSIONS.find((item) => item.id === dimensionId) || DIMENSIONS[1],
    [dimensionId]
  );

  async function loadHistory() {
    try {
      const data = await apiRequest<HistoryResponse>(
        "/images/history?page=1&page_size=12"
      );
      setHistory(data.items);
    } catch {
      // guests may have empty history
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  function selectTool(next: StudioToolId) {
    const selected = CREATE_TOOLS.find((item) => item.id === next);
    if (!selected) return;
    if (!selected.guestAllowed && !isLoggedIn) {
      setError("Sign in to use this Photo Studio feature.");
      return;
    }
    setError("");
    setToolId(next);
  }

  function clearForm() {
    setPrompt("");
    setImage1(null);
    setImage2(null);
    setImage1Key((k) => k + 1);
    setImage2Key((k) => k + 1);
  }

  async function pollJob(jobId: number): Promise<GeneratedItem> {
    for (;;) {
      const status = await apiRequest<JobStatusResponse>(
        `/images/jobs/${jobId}`
      );
      setProgress(status.progress);
      setProgressMessage(status.message || "Generating...");

      if (status.status === "completed" && status.result) {
        return status.result;
      }
      if (status.status === "failed") {
        throw new Error(status.error || "Image generation failed.");
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  async function handleGenerate(event: FormEvent) {
    event.preventDefault();

    if (!tool.guestAllowed && !isLoggedIn) {
      setError("Sign in to use this Photo Studio feature.");
      return;
    }

    const finalPrompt = buildToolPrompt(tool.id, prompt, style, scene);
    if (finalPrompt.trim().length < 3) {
      setError("Please enter a prompt describing what you want.");
      return;
    }

    if (tool.needsImage1 && !image1) {
      setError("Upload Image 1 to continue.");
      return;
    }
    if (tool.needsImage2 && !image2) {
      setError("Upload Image 2 to continue.");
      return;
    }

    setLoading(true);
    setProgress(1);
    setProgressMessage("Starting...");
    setError("");
    setLatest(null);

    try {
      const form = new FormData();
      form.append("prompt", finalPrompt);
      form.append("tool", tool.id);
      form.append("width", String(dimension.width));
      form.append("height", String(dimension.height));
      form.append("photo_type", photoType);
      form.append("photo_style", style);
      form.append("scene", scene);

      // Primary reference is Image 1; for text-to-image optional Image 1 works as style ref
      const reference = image1 || image2;
      if (reference) {
        form.append("reference", reference);
      }
      if (image2 && tool.needsImage2) {
        form.append("reference_secondary", image2);
      }

      const started = await apiRequest<JobStartResponse>("/images/generate", {
        method: "POST",
        body: form,
      });

      setProgress(started.progress || 1);
      setProgressMessage(started.message || "Queued...");

      const result = await pollJob(started.job_id);
      setLatest(result);
      setProgress(100);
      setProgressMessage("Done");
      clearForm();
      await loadHistory();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Image generation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="photo-studio">
      <div className="photo-studio-top">
        <div className="studio-heading">
          <ImageIcon size={32} />
          <div>
            <h1>Photo Studio</h1>
            <p>
              {isLoggedIn
                ? "Full AI photo editing and generation tools."
                : "Guests can use Text to Image. Sign in for the full Photo Studio."}
            </p>
          </div>
        </div>
        {!isLoggedIn && (
          <Link to="/login" className="primary-button photo-studio-signin">
            Sign in for all features
          </Link>
        )}
      </div>

      <div className="photo-studio-layout">
        <aside className="photo-tool-nav">
          <h4>Create & Edit</h4>
          <ul>
            {CREATE_TOOLS.map((item) => {
              const locked = !item.guestAllowed && !isLoggedIn;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`photo-tool-btn${
                      toolId === item.id ? " is-active" : ""
                    }${locked ? " is-locked" : ""}`}
                    onClick={() => selectTool(item.id)}
                  >
                    <span>{item.label}</span>
                    {item.badge && <em>{item.badge}</em>}
                    {locked && <Lock size={14} />}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <section className="photo-workspace">
          <div className="photo-quick-tabs">
            {CREATE_TOOLS.slice(0, 4).map((item) => (
              <button
                key={item.id}
                type="button"
                className={`photo-chip${toolId === item.id ? " is-active" : ""}`}
                onClick={() => selectTool(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <form className="photo-main-card" onSubmit={handleGenerate}>
            <div className="photo-tool-title">
              <Sparkles size={18} />
              <div>
                <h3>{tool.label}</h3>
                <p>{tool.description}</p>
              </div>
            </div>

            <label>
              Your prompt
              <textarea
                rows={5}
                placeholder="Describe the image you want to create..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={loading}
              />
            </label>

            {(tool.needsImage1 || tool.id === "text_to_image") && (
              <div className="photo-upload-grid">
                <label className="photo-upload-box">
                  <Upload size={18} />
                  <strong>
                    {tool.needsImage2
                      ? "Upload Image 1 (Person / Scene)"
                      : tool.id === "text_to_image"
                        ? "Reference image (optional)"
                        : "Upload Image 1"}
                  </strong>
                  <input
                    key={image1Key}
                    type="file"
                    accept="image/*"
                    disabled={loading}
                    onChange={(e) => setImage1(e.target.files?.[0] || null)}
                  />
                  {image1Preview && (
                    <img src={image1Preview} alt="Image 1 preview" />
                  )}
                </label>

                {tool.needsImage2 && (
                  <label className="photo-upload-box">
                    <Upload size={18} />
                    <strong>Upload Image 2 (Person / Face)</strong>
                    <input
                      key={image2Key}
                      type="file"
                      accept="image/*"
                      disabled={loading}
                      onChange={(e) => setImage2(e.target.files?.[0] || null)}
                    />
                    {image2Preview && (
                      <img src={image2Preview} alt="Image 2 preview" />
                    )}
                  </label>
                )}
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            <div className="photo-actions">
              <button className="primary-button" type="submit" disabled={loading}>
                {loading ? "Generating..." : "Generate Image"}
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={loading}
                onClick={clearForm}
              >
                Clear
              </button>
            </div>

            {loading && (
              <GenerationProgress
                progress={progress}
                message={progressMessage || "Generating..."}
              />
            )}
          </form>

          {latest?.image_url && !loading && (
            <div className="photo-result">
              <h3>Latest result</h3>
              <img src={mediaUrl(latest.image_url) || ""} alt={latest.prompt} />
              <p>{latest.prompt}</p>
              {latest.generation_time_seconds != null && (
                <small>
                  Generated in {latest.generation_time_seconds} seconds
                </small>
              )}
            </div>
          )}

          <div className="history-section">
            <h3>Gallery</h3>
            {history.length === 0 ? (
              <p className="muted-text">No images yet. Generate your first one.</p>
            ) : (
              <div className="history-grid">
                {history.map((item) => (
                  <article className="history-card" key={item.id}>
                    {item.image_url ? (
                      <img
                        src={mediaUrl(item.image_url) || ""}
                        alt={item.prompt}
                      />
                    ) : (
                      <div className="history-empty">{item.status}</div>
                    )}
                    <p>{item.prompt}</p>
                    <small>{new Date(item.created_at).toLocaleString()}</small>
                  </article>
                ))}
              </div>
            )}
          </div>
        </section>

        <aside className="photo-settings">
          <div className="photo-settings-block">
            <h4>Image Dimensions</h4>
            <div className="photo-option-grid">
              {DIMENSIONS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`photo-option${
                    dimensionId === item.id ? " is-active" : ""
                  }`}
                  onClick={() => setDimensionId(item.id)}
                  disabled={loading}
                >
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="photo-settings-block">
            <h4>Photo Type</h4>
            <div className="photo-option-grid">
              {PHOTO_TYPES.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className={`photo-option${
                    photoType === item.id ? " is-active" : ""
                  }`}
                  onClick={() => setPhotoType(item.id)}
                  disabled={loading || !isLoggedIn}
                >
                  <strong>{item.label}</strong>
                  <span>{item.hint}</span>
                </button>
              ))}
            </div>
            {!isLoggedIn && (
              <p className="muted-text">Sign in to use photo type presets.</p>
            )}
          </div>

          <div className="photo-settings-block">
            <h4>Photo Style</h4>
            <div className="photo-chip-wrap">
              {PHOTO_STYLES.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`photo-chip${style === item ? " is-active" : ""}`}
                  onClick={() => setStyle(item)}
                  disabled={loading}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="photo-settings-block">
            <h4>Scene & Theme</h4>
            <div className="photo-chip-wrap">
              {SCENES.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`photo-chip${scene === item ? " is-active" : ""}`}
                  onClick={() => setScene(item)}
                  disabled={loading || (!isLoggedIn && toolId !== "text_to_image")}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
