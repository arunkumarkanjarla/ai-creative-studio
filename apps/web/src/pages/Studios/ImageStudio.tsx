import { useEffect, useState, type FormEvent } from "react";
import { Image } from "lucide-react";

import { apiRequest, mediaUrl, MEDIA_BASE_URL } from "../../services/api";

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

interface PromptPack {
  prompt_id: string;
  title: string;
  description: string;
  base_prompt: string;
  reference_url: string | null;
}

const NEW_STYLE_VALUE = "__new__";
const NO_REFERENCE = "";

export default function ImageStudio() {
  const [prompt, setPrompt] = useState(
    "a peaceful mountain landscape at sunrise, clear sky, realistic photo"
  );
  const [packs, setPacks] = useState<PromptPack[]>([]);
  const [selectedReferenceId, setSelectedReferenceId] = useState(NO_REFERENCE);
  const [styleTitle, setStyleTitle] = useState(NEW_STYLE_VALUE);
  const [customTitle, setCustomTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [latest, setLatest] = useState<GeneratedItem | null>(null);
  const [history, setHistory] = useState<GeneratedItem[]>([]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  async function loadHistory() {
    try {
      const data = await apiRequest<HistoryResponse>(
        "/images/history?page=1&page_size=12"
      );
      setHistory(data.items);
    } catch {
      // ignore for first-time guests
    }
  }

  async function loadPacks() {
    try {
      const data = await apiRequest<PromptPack[]>("/images/prompts");
      setPacks(data);
    } catch {
      // optional for guests
    }
  }

  useEffect(() => {
    loadPacks();
    loadHistory();
  }, []);

  const selectedPack =
    styleTitle !== NEW_STYLE_VALUE
      ? packs.find((pack) => pack.prompt_id === styleTitle)
      : undefined;

  async function handleUpload(event: FormEvent) {
    event.preventDefault();

    const title =
      styleTitle === NEW_STYLE_VALUE
        ? customTitle.trim()
        : selectedPack?.title || "";

    if (!uploadFile || !title) {
      setUploadError("Please choose a style title and a reference image.");
      return;
    }

    setUploading(true);
    setUploadError("");

    try {
      const form = new FormData();
      form.append("title", title);
      form.append(
        "description",
        selectedPack?.description ||
          "User uploaded reference for text-to-image style"
      );
      form.append("reference", uploadFile);

      const created = await apiRequest<PromptPack>("/images/prompts", {
        method: "POST",
        body: form,
      });

      setCustomTitle("");
      setUploadFile(null);
      await loadPacks();
      setStyleTitle(created.prompt_id);
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Unable to upload reference."
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleGenerate(event: FormEvent) {
    event.preventDefault();

    const text = prompt.trim();
    if (text.length < 3) {
      setError("Please enter a longer description.");
      return;
    }

    setLoading(true);
    setError("");
    setLatest(null);

    try {
      const result = await apiRequest<GeneratedItem>("/images/generate", {
        method: "POST",
        body: JSON.stringify({
          prompt: text,
          // Optional: only send when user picks a reference style
          prompt_id: selectedReferenceId || null,
        }),
      });

      setLatest(result);
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
    <div className="content-page">
      <div className="studio-heading">
        <Image size={36} />
        <div>
          <h1>Image Studio</h1>
          <p>Create images and manage face/style references.</p>
        </div>
      </div>

      <div className="studio-panels">
        <form className="generation-card" onSubmit={handleGenerate}>
          <h3>Text to Image</h3>

          <label>
            Reference style (optional)
            <select
              value={selectedReferenceId}
              onChange={(e) => setSelectedReferenceId(e.target.value)}
              disabled={loading}
            >
              <option value={NO_REFERENCE}>None — use prompt only</option>
              {packs.map((pack) => (
                <option key={pack.prompt_id} value={pack.prompt_id}>
                  {pack.title}
                </option>
              ))}
            </select>
          </label>

          <label>
            Your prompt
            <textarea
              placeholder="Describe any image you want to create..."
              rows={6}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
            />
          </label>

          {error && <div className="error-message">{error}</div>}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Generating... please wait" : "Generate Image"}
          </button>

          {loading && (
            <p className="generation-hint">
              First run may take longer while the model loads into memory.
            </p>
          )}
        </form>

        <form className="generation-card" onSubmit={handleUpload}>
          <h3>Add reference style</h3>
          <p className="muted-text">
            Upload a face/style reference. Saved under
            reference_images/&lt;prompt_id&gt;/.
          </p>

          <label>
            Style title
            <select
              value={styleTitle}
              onChange={(e) => setStyleTitle(e.target.value)}
              disabled={uploading}
            >
              <option value={NEW_STYLE_VALUE}>Create new style...</option>
              {packs.map((pack) => (
                <option key={pack.prompt_id} value={pack.prompt_id}>
                  {pack.title}
                </option>
              ))}
            </select>
          </label>

          {styleTitle === NEW_STYLE_VALUE && (
            <label>
              New style name
              <input
                type="text"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="Example: Soft smile saree face"
                disabled={uploading}
              />
            </label>
          )}

          {selectedPack?.reference_url && (
            <div className="reference-preview">
              <img
                src={`${MEDIA_BASE_URL}${selectedPack.reference_url}`}
                alt={selectedPack.title}
              />
              <small>{selectedPack.description}</small>
            </div>
          )}

          <label>
            Reference image
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
              disabled={uploading}
            />
          </label>

          {uploadError && <div className="error-message">{uploadError}</div>}

          <button
            className="secondary-button"
            type="submit"
            disabled={uploading}
          >
            {uploading ? "Saving..." : "Save Reference Style"}
          </button>
        </form>
      </div>

      {latest?.image_url && (
        <div className="generation-result">
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
        <h3>Your recent images</h3>

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
    </div>
  );
}
