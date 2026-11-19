import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Eye,
  Image as ImageIcon,
  Lock,
  Sparkles,
  Upload,
  X,
} from "lucide-react";

import { useAuth } from "../../context/AuthContext";
import { apiRequest, mediaUrl } from "../../services/api";
import VoiceInput from "../../components/VoiceInput";
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

interface PreviewSampleResponse {
  preview_url: string | null;
  key: string;
  photographer?: string;
  source?: string;
  error?: string;
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

function isStudioToolId(value: string | null): value is StudioToolId {
  return CREATE_TOOLS.some((tool) => tool.id === value);
}

export default function ImageStudio() {
  const { user } = useAuth();
  const isLoggedIn = Boolean(user);
  const [searchParams, setSearchParams] = useSearchParams();

  const toolFromUrl = searchParams.get("tool");
  const toolId: StudioToolId = isStudioToolId(toolFromUrl)
    ? toolFromUrl
    : "text_to_image";

  const [prompt, setPrompt] = useState("");
  const [image1, setImage1] = useState<File | null>(null);
  const [image2, setImage2] = useState<File | null>(null);
  const [image1Key, setImage1Key] = useState(0);
  const [image2Key, setImage2Key] = useState(0);
  const [dimensionId, setDimensionId] =
    useState<(typeof DIMENSIONS)[number]["id"]>("3:4");
  const [photoType, setPhotoType] =
    useState<(typeof PHOTO_TYPES)[number]["id"]>("album");
  const [style, setStyle] = useState<(typeof PHOTO_STYLES)[number]>("Realistic");
  const [scene, setScene] = useState<(typeof SCENES)[number]>("Beach");

  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [latest, setLatest] = useState<GeneratedItem | null>(null);
  const [samplePreviewUrl, setSamplePreviewUrl] = useState<string | null>(null);
  const [showMockPreview, setShowMockPreview] = useState(false);
  const [previewPanelOpen, setPreviewPanelOpen] = useState(false);

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

  const composedPrompt = useMemo(
    () => buildToolPrompt(tool.id, prompt, style, scene, photoType),
    [tool.id, prompt, style, scene, photoType]
  );

  // Fetch sample preview URL for mock preview
  useEffect(() => {
    async function fetchSamplePreview() {
      try {
        const params = new URLSearchParams({
          style: style,
          scene: scene,
          photo_type: photoType,
        });
        const response = await apiRequest<PreviewSampleResponse>(
          `/preview/sample?${params}`
        );
        if (response.preview_url) {
          setSamplePreviewUrl(`http://localhost:8000${response.preview_url}`);
        } else {
          setSamplePreviewUrl(null);
        }
      } catch (err) {
        console.warn("Failed to fetch sample preview:", err);
        setSamplePreviewUrl(null);
      }
    }
    
    fetchSamplePreview();
  }, [style, scene, photoType]);
  
  // Clear mock preview and close panel when prompt is cleared
  useEffect(() => {
    if (!prompt.trim()) {
      setShowMockPreview(false);
      setPreviewPanelOpen(false);
    }
  }, [prompt]);

  useEffect(() => {
    if (!isStudioToolId(toolFromUrl)) {
      setSearchParams({ tool: "text_to_image" }, { replace: true });
    }
  }, [toolFromUrl, setSearchParams]);

  useEffect(() => {
    setError("");
    setLatest(null);
    setProgress(0);
    setShowMockPreview(false);
  }, [toolId]);

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

      if (status.status === "completed" && status.result) {
        return status.result;
      }
      if (status.status === "failed") {
        throw new Error(status.error || "Image generation failed.");
      }
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  function handlePreview() {
    // Preview now shows instant mock, no AI generation
    if (!isLoggedIn) {
      setError("Sign in to preview images.");
      return;
    }
    
    if (prompt.trim().length < 3) {
      setError("Enter a prompt to preview.");
      return;
    }
    
    setError("");
    setShowMockPreview(true);
    setPreviewPanelOpen(true);
  }
  
  function closePreview() {
    setPreviewPanelOpen(false);
    setShowMockPreview(false);
  }

  async function runGeneration() {
    if (!isLoggedIn) {
      setError("Sign in to generate images.");
      return;
    }

    const finalPrompt = composedPrompt;
    if (finalPrompt.trim().length < 3) {
      setError("Please enter a prompt describing what you want.");
      return;
    }

    // Generate uses uploads when the selected tool needs them
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
    setError("");
    setLatest(null);
    setShowMockPreview(false);
    setPreviewPanelOpen(true); // Show panel during generation

    try {
      const form = new FormData();
      form.append("prompt", finalPrompt);
      form.append("tool", tool.id);
      form.append("width", String(dimension.width));
      form.append("height", String(dimension.height));
      form.append("photo_type", photoType);
      form.append("photo_style", style);
      form.append("scene", scene);

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

      const result = await pollJob(started.job_id);
      setProgress(100);
      setLatest(result);
      clearForm();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Image generation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerate(event: FormEvent) {
    event.preventDefault();
    await runGeneration();
  }
  
  // Get CSS filter for photo style
  function getStyleFilter(styleName: string): string {
    const filters: Record<string, string> = {
      "Cinematic": "contrast(1.1) saturate(1.2) brightness(0.95)",
      "Vintage": "sepia(0.3) contrast(0.9) brightness(1.05)",
      "Natural": "saturate(0.9) brightness(1.05)",
      "Studio": "contrast(1.15) brightness(1.05)",
      "Wedding": "brightness(1.1) saturate(1.1) contrast(0.95)",
      "Fashion": "contrast(1.2) saturate(1.3)",
      "Headshot": "contrast(1.1) brightness(1.05)",
    };
    return filters[styleName] || "none";
  }

  const aspectPadding = `${(dimension.height / dimension.width) * 100}%`;
  
  // Show generated image or generating state
  const displayImage = latest?.image_url ? latest : null;
  
  // Show mock preview if user clicked Preview and has a prompt
  const showMock = showMockPreview && samplePreviewUrl && prompt.trim().length >= 3 && !loading;
  
  // Get nice status message based on progress
  function getProgressStatus(percent: number): string {
    if (percent < 15) return "Preparing canvas...";
    if (percent < 30) return "Creating composition...";
    if (percent < 50) return "Adding details...";
    if (percent < 70) return "Refining image...";
    if (percent < 90) return "Finishing touches...";
    return "Almost ready...";
  }
  
  const photoTypeLabel =
    PHOTO_TYPES.find((item) => item.id === photoType)?.label || photoType;
  
  const canPreview = isLoggedIn && prompt.trim().length >= 3;

  return (
    <div className="photo-studio">
      <div className="photo-studio-top">
        <div className="studio-heading">
          <ImageIcon size={32} />
          <div>
            <h1>Photo Studio</h1>
            <p>
              {isLoggedIn
                ? "Preview generates from your prompt and settings. Generate uses the full tool flow."
                : "Browse all Photo Studio tools. Sign in to preview and generate."}
            </p>
          </div>
        </div>
        {!isLoggedIn && (
          <Link to="/login" className="primary-button photo-studio-signin">
            Sign in to generate
          </Link>
        )}
      </div>

      <div className="photo-studio-layout photo-studio-layout-wide">
        <section className="photo-workspace">
          <form className="photo-main-card" onSubmit={handleGenerate}>
            <div className="photo-tool-title">
              <Sparkles size={18} />
              <div>
                <h3>{tool.label}</h3>
                <p>{tool.description}</p>
              </div>
            </div>

            {!isLoggedIn && (
              <div className="photo-guest-banner">
                <Lock size={16} />
                <span>
                  Sign in to preview and generate with{" "}
                  <strong>{tool.label}</strong>.
                </span>
                <Link to="/login">Sign in</Link>
              </div>
            )}

            <label>
              Your prompt
              <div className="prompt-with-voice">
                <textarea
                  rows={5}
                  placeholder="Describe the image you want to create..."
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  disabled={loading}
                />
                <VoiceInput
                  onTranscript={(text) => {
                    setPrompt((prev) => (prev ? `${prev} ${text}` : text));
                  }}
                  language="en-IN"
                />
              </div>
            </label>

            {(tool.needsImage1 || tool.id === "text_to_image") && (
              <div className="photo-upload-grid">
                <label className="photo-upload-box">
                  <Upload size={18} />
                  <strong>
                    {tool.needsImage2
                      ? "Upload Image 1 (Person / Scene)"
                      : tool.id === "text_to_image"
                        ? "Reference image (optional for Generate)"
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
              <button
                className="secondary-button"
                type="button"
                disabled={!canPreview || loading}
                onClick={handlePreview}
                title={
                  !isLoggedIn
                    ? "Sign in to preview"
                    : !canPreview
                      ? "Enter a prompt to preview"
                      : "Show instant preview mock with selected format"
                }
              >
                <Eye size={16} />
                Preview
              </button>
              <button
                className="primary-button"
                type="submit"
                disabled={loading || !isLoggedIn}
                title={
                  isLoggedIn
                    ? "Generate final image with AI"
                    : "Sign in to generate images"
                }
              >
                {loading ? "Generating..." : isLoggedIn ? "Generate Image" : "Sign in to Generate"}
              </button>
              <button
                className="secondary-button"
                type="button"
                disabled={loading}
                onClick={() => {
                  clearForm();
                  setShowMockPreview(false);
                  setPreviewPanelOpen(false);
                }}
              >
                Clear
              </button>
            </div>
          </form>

          {previewPanelOpen && (
            <div className="photo-preview-panel photo-preview-panel-open">
              <div className="photo-preview-header">
                <h3>Live Preview</h3>
                <button
                  type="button"
                  className="photo-preview-close"
                  onClick={closePreview}
                  aria-label="Close preview"
                  title="Close preview"
                >
                  <X size={18} />
                </button>
              </div>

              <div
                className={`photo-preview-stage${loading ? " is-generating" : ""}`}
              >
              <div
                className="photo-preview-frame"
                style={{ paddingBottom: aspectPadding }}
              >
                <div className="photo-preview-inner">
                  {loading ? (
                    <div className="photo-generating-frame">
                      <div 
                        className="photo-generating-blur"
                        style={{ 
                          opacity: Math.max(0.2, 1 - (progress / 100)),
                          filter: `blur(${Math.max(2, 20 - (progress / 5))}px)`
                        }}
                      >
                        <div className="photo-generating-shimmer" />
                      </div>
                      {displayImage?.image_url && (
                        <img
                          src={mediaUrl(displayImage.image_url) || ""}
                          alt={displayImage.prompt}
                          className="photo-preview-result photo-generating-reveal"
                          style={{ opacity: progress >= 100 ? 1 : 0 }}
                        />
                      )}
                      <div className="photo-generating-status">
                        <span className="photo-generating-status-text">
                          {getProgressStatus(progress)}
                        </span>
                        <span className="photo-generating-status-percent">
                          {progress}%
                        </span>
                      </div>
                    </div>
                  ) : displayImage?.image_url ? (
                    <img
                      src={mediaUrl(displayImage.image_url) || ""}
                      alt={displayImage.prompt}
                      className="photo-preview-result photo-result-fadein"
                    />
                  ) : showMock ? (
                    <div className="photo-preview-mock">
                      <img
                        src={samplePreviewUrl}
                        alt={`${style} ${scene} preview`}
                        className="photo-preview-result photo-sample-preview"
                        style={{ filter: getStyleFilter(style) }}
                      />
                      <div className="photo-preview-mock-caption">
                        <p><strong>Preview Mock</strong></p>
                        <p>{dimension.label} ({dimension.width}×{dimension.height}) · {photoTypeLabel}</p>
                        <p>{style} · {scene}</p>
                        <p className="photo-preview-mock-prompt">{prompt.substring(0, 100)}{prompt.length > 100 ? "..." : ""}</p>
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="photo-preview-meta">
              <p>
                <strong>Tool:</strong> {tool.label}
                {showMock ? " · Preview mock (instant, not AI-generated)" : ""}
              </p>
              <p>
                <strong>Applied prompt:</strong> {composedPrompt.trim() || "—"}
              </p>
              {displayImage?.generation_time_seconds != null && !loading && (
                <small>
                  Generated in {displayImage.generation_time_seconds} seconds
                </small>
              )}
              </div>
            </div>
          )}
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
                  disabled={loading || !isLoggedIn}
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
                  disabled={loading || !isLoggedIn}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          {!isLoggedIn && (
            <p className="muted-text">
              Sign in to apply Photo Type, Style, and Scene to generation.
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
