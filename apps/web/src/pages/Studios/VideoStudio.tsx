import { useEffect, useRef, useState } from "react";
import {
  Video,
  Plus,
  Trash2,
  Download,
  Play,
  Pause,
  Upload,
  Clapperboard,
  LogIn,
} from "lucide-react";
import VoiceInput from "../../components/VoiceInput";
import { apiRequest } from "../../services/api";
import { useAuth } from "../../context/AuthContext";

type Tab = "create" | "gallery" | "details";

interface Voice {
  voice_id: string;
  name: string;
  gender?: string;
  language?: string;
}

interface CharacterDraft {
  name: string;
  voice_id: string;
  file: File | null;
  previewUrl: string | null;
}

interface SceneDraft {
  prompt: string;
  dialogue_text: string;
  character_name: string;
  duration_seconds: number;
}

interface VideoItem {
  id: number;
  prompt: string;
  category: string;
  length_preset: string;
  duration_seconds: number;
  orientation: string;
  resolution: string;
  fps: number;
  audio_mode: string;
  subtitles: boolean;
  output_format: string;
  engine: string;
  status: string;
  progress: number;
  error_message?: string;
  stream_url?: string | null;
  download_url?: string | null;
  thumbnail_url?: string | null;
  created_at?: string;
  scenes?: any[];
  characters?: any[];
  has_output?: boolean;
}

const CATEGORY_OPTIONS = [
  { id: "instagram_short", label: "Instagram Short / Reel" },
  { id: "youtube_short", label: "YouTube Short" },
  { id: "web_series", label: "Web Series Episode" },
  { id: "movie_short", label: "Movie / Short Film" },
  { id: "drama", label: "Drama" },
  { id: "music_video", label: "Music Video" },
  { id: "advertisement", label: "Advertisement" },
  { id: "explainer", label: "Explainer" },
  { id: "story_kids", label: "Story / Kids" },
  { id: "documentary", label: "Documentary" },
  { id: "custom", label: "Custom" },
];

export default function VideoStudio() {
  const { user, hasAccess } = useAuth();
  const canUse = Boolean(user && hasAccess("video"));

  const [tab, setTab] = useState<Tab>("create");
  const [prompt, setPrompt] = useState("");
  const [category, setCategory] = useState("instagram_short");
  const [lengthPreset, setLengthPreset] = useState("short");
  const [customSeconds, setCustomSeconds] = useState(15);
  const [orientation, setOrientation] = useState("portrait");
  const [resolution, setResolution] = useState("720p");
  const [fps, setFps] = useState(30);
  const [audioMode, setAudioMode] = useState("dialogue");
  const [subtitles, setSubtitles] = useState(true);
  const [outputFormat, setOutputFormat] = useState("mp4");
  const [engine, setEngine] = useState("local");
  const [engines, setEngines] = useState<any[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [characters, setCharacters] = useState<CharacterDraft[]>([
    { name: "Alex", voice_id: "en-US-JennyNeural", file: null, previewUrl: null },
    { name: "Sam", voice_id: "en-US-GuyNeural", file: null, previewUrl: null },
  ]);
  const [useScenes, setUseScenes] = useState(false);
  const [scenes, setScenes] = useState<SceneDraft[]>([
    { prompt: "", dialogue_text: "", character_name: "Alex", duration_seconds: 8 },
    { prompt: "", dialogue_text: "", character_name: "Sam", duration_seconds: 8 },
  ]);

  const [submitting, setSubmitting] = useState(false);
  const [activeJob, setActiveJob] = useState<VideoItem | null>(null);
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [selected, setSelected] = useState<VideoItem | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const blobCache = useRef<Map<string, string>>(new Map());
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    if (!canUse) return;
    loadMeta();
    loadVoices();
    loadGallery();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
      blobCache.current.forEach((url) => URL.revokeObjectURL(url));
      blobCache.current.clear();
    };
  }, [canUse]);

  useEffect(() => {
    // Category defaults
    const defaults: Record<string, { orientation: string; length: string; fps: number; seconds: number }> = {
      instagram_short: { orientation: "portrait", length: "short", fps: 30, seconds: 15 },
      youtube_short: { orientation: "portrait", length: "short", fps: 30, seconds: 30 },
      web_series: { orientation: "landscape", length: "medium", fps: 24, seconds: 180 },
      movie_short: { orientation: "landscape", length: "long", fps: 24, seconds: 600 },
      drama: { orientation: "landscape", length: "medium", fps: 24, seconds: 120 },
      music_video: { orientation: "landscape", length: "medium", fps: 30, seconds: 180 },
      advertisement: { orientation: "landscape", length: "short", fps: 30, seconds: 30 },
      explainer: { orientation: "landscape", length: "medium", fps: 24, seconds: 90 },
      story_kids: { orientation: "landscape", length: "medium", fps: 24, seconds: 120 },
      documentary: { orientation: "landscape", length: "long", fps: 25, seconds: 480 },
      custom: { orientation: "landscape", length: "custom", fps: 24, seconds: 30 },
    };
    const d = defaults[category] || defaults.custom;
    setOrientation(d.orientation);
    setLengthPreset(d.length);
    setFps(d.fps);
    setCustomSeconds(Math.min(d.seconds, 60));
  }, [category]);

  const loadMeta = async () => {
    try {
      const data = await apiRequest<any>("/video/meta");
      setEngines(data.engines || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadVoices = async () => {
    try {
      const data = await apiRequest<any>("/audio/voices");
      setVoices(data.voices || []);
    } catch (err) {
      console.error(err);
    }
  };

  const loadGallery = async () => {
    try {
      const data = await apiRequest<any>("/video/my?limit=50");
      setVideos(data.items || []);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchBlobUrl = async (path: string) => {
    if (blobCache.current.has(path)) return blobCache.current.get(path)!;
    const token = localStorage.getItem("access_token");
    const res = await fetch(`http://localhost:8000${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to load media");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    blobCache.current.set(path, url);
    return url;
  };

  const startPolling = (id: number) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const status = await apiRequest<any>(`/video/${id}/status`);
        setActiveJob((prev) => (prev ? { ...prev, ...status } : status));
        if (status.status === "completed" || status.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          pollRef.current = null;
          await loadGallery();
          if (status.status === "completed") {
            const full = await apiRequest<VideoItem>(`/video/${id}`);
            setSelected(full);
            setTab("gallery");
          }
        }
      } catch (err) {
        console.error(err);
      }
    }, 1500);
  };

  const updateCharacter = (index: number, patch: Partial<CharacterDraft>) => {
    setCharacters((prev) => prev.map((c, i) => (i === index ? { ...c, ...patch } : c)));
  };

  const onCharacterFile = (index: number, file: File | null) => {
    const prev = characters[index]?.previewUrl;
    if (prev) URL.revokeObjectURL(prev);
    updateCharacter(index, {
      file,
      previewUrl: file ? URL.createObjectURL(file) : null,
    });
  };

  const submitJob = async () => {
    setError(null);
    if (!prompt.trim()) {
      setError("Enter a prompt or script.");
      return;
    }
    if (characters.some((c) => !c.name.trim())) {
      setError("Each character needs a name.");
      return;
    }
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("prompt", prompt.trim());
      form.append("category", category);
      form.append("length_preset", lengthPreset);
      form.append("duration_seconds", String(customSeconds));
      form.append("orientation", orientation);
      form.append("resolution", resolution);
      form.append("fps", String(fps));
      form.append("audio_mode", audioMode);
      form.append("subtitles", String(subtitles));
      form.append("output_format", outputFormat);
      form.append("engine", engine);
      form.append(
        "characters_json",
        JSON.stringify(
          characters.map((c) => ({
            name: c.name.trim(),
            voice_id: c.voice_id,
            has_image: Boolean(c.file),
          }))
        )
      );
      form.append(
        "scenes_json",
        JSON.stringify(
          useScenes
            ? scenes.map((s) => ({
                prompt: s.prompt || prompt,
                dialogue_text: s.dialogue_text || s.prompt || prompt,
                character_name: s.character_name,
                duration_seconds: s.duration_seconds,
              }))
            : []
        )
      );
      characters.forEach((c) => {
        if (c.file) form.append("character_images", c.file);
      });

      const created = await apiRequest<VideoItem>("/video/generate", {
        method: "POST",
        body: form,
      });
      setActiveJob(created);
      startPolling(created.id);
      setTab("create");
    } catch (err: any) {
      setError(err?.message || "Failed to create video");
    } finally {
      setSubmitting(false);
    }
  };

  const playVideo = async (item: VideoItem) => {
    if (!item.stream_url || !videoRef.current) return;
    try {
      if (playingId === item.id) {
        videoRef.current.pause();
        setPlayingId(null);
        return;
      }
      const url = await fetchBlobUrl(item.stream_url);
      videoRef.current.src = url;
      await videoRef.current.play();
      setPlayingId(item.id);
      await apiRequest("/video/events", {
        method: "POST",
        body: JSON.stringify({ action: "play", project_id: item.id }),
      }).catch(() => undefined);
    } catch (err) {
      alert("Unable to play video");
    }
  };

  const downloadVideo = async (item: VideoItem) => {
    if (!item.download_url) return;
    try {
      const url = await fetchBlobUrl(item.download_url);
      const a = document.createElement("a");
      a.href = url;
      a.download = `video_${item.id}.mp4`;
      a.click();
      await apiRequest("/video/events", {
        method: "POST",
        body: JSON.stringify({ action: "download", project_id: item.id }),
      }).catch(() => undefined);
    } catch {
      alert("Download failed");
    }
  };

  const deleteVideo = async (id: number) => {
    if (!confirm("Delete this video?")) return;
    await apiRequest(`/video/${id}`, { method: "DELETE" });
    if (selected?.id === id) setSelected(null);
    if (playingId === id) setPlayingId(null);
    await loadGallery();
  };

  if (!user) {
    return (
      <div className="content-page">
        <div className="studio-heading">
          <Video size={36} />
          <div>
            <h1>Video Studio</h1>
            <p>Sign in to generate AI videos with the local preview engine.</p>
          </div>
        </div>
        <div className="generation-card video-signin-card">
          <LogIn size={28} />
          <p>Video generation is available to signed-in users only.</p>
          <a className="primary-button" href="/login">
            Sign in
          </a>
        </div>
      </div>
    );
  }

  if (!canUse) {
    return (
      <div className="content-page">
        <div className="studio-heading">
          <Video size={36} />
          <div>
            <h1>Video Studio</h1>
            <p>Your account does not have Video Studio access yet.</p>
          </div>
        </div>
      </div>
    );
  }

  const ltx = engines.find((e) => e.engine_id === "ltx2");

  return (
    <div className="content-page video-studio">
      <div className="studio-heading">
        <Video size={36} />
        <div>
          <h1>Video Studio</h1>
          <p>Create short AI preview videos from scripts, characters, and voices.</p>
        </div>
      </div>

      <div className="video-tabs">
        <button className={tab === "create" ? "active" : ""} onClick={() => setTab("create")}>
          Create
        </button>
        <button className={tab === "gallery" ? "active" : ""} onClick={() => { setTab("gallery"); loadGallery(); }}>
          My Videos
        </button>
        <button
          className={tab === "details" ? "active" : ""}
          onClick={() => setTab("details")}
          disabled={!selected}
        >
          Details
        </button>
      </div>

      {tab === "create" && (
        <div className="generation-card video-form">
          <h3>
            <Clapperboard size={18} /> Script & settings
          </h3>
          <div className="prompt-with-voice">
            <textarea
              placeholder="Describe the video or paste a script..."
              rows={5}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />
            <VoiceInput
              onTranscript={(text) => setPrompt((prev) => (prev ? `${prev} ${text}` : text))}
              language="en-IN"
            />
          </div>

          <div className="video-grid-2">
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORY_OPTIONS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Length
              <select value={lengthPreset} onChange={(e) => setLengthPreset(e.target.value)}>
                <option value="short">Short (5–60s)</option>
                <option value="medium">Medium (1–5 min)</option>
                <option value="long">Long (5–20 min)</option>
                <option value="custom">Custom (seconds)</option>
              </select>
            </label>
            {(lengthPreset === "custom" || lengthPreset === "short") && (
              <label>
                Duration (seconds)
                <input
                  type="number"
                  min={5}
                  max={1200}
                  value={customSeconds}
                  onChange={(e) => setCustomSeconds(Number(e.target.value))}
                />
              </label>
            )}
            <label>
              Orientation
              <select value={orientation} onChange={(e) => setOrientation(e.target.value)}>
                <option value="portrait">Portrait</option>
                <option value="landscape">Landscape</option>
                <option value="square">Square</option>
              </select>
            </label>
            <label>
              Resolution
              <select value={resolution} onChange={(e) => setResolution(e.target.value)}>
                <option value="480p">480p</option>
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
                <option value="1440p">1440p (GPU-only)</option>
                <option value="4k">4K (GPU-only)</option>
              </select>
            </label>
            <label>
              FPS
              <select value={fps} onChange={(e) => setFps(Number(e.target.value))}>
                <option value={24}>24</option>
                <option value={25}>25</option>
                <option value={30}>30</option>
              </select>
            </label>
            <label>
              Audio mode
              <select value={audioMode} onChange={(e) => setAudioMode(e.target.value)}>
                <option value="dialogue">Dialogue / voiceover</option>
                <option value="background_music">Background music</option>
                <option value="dialogue_music">Dialogue + music</option>
                <option value="silent">Silent</option>
              </select>
            </label>
            <label>
              Output
              <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
                <option value="mp4">MP4</option>
                <option value="webm">WebM</option>
              </select>
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={subtitles}
                onChange={(e) => setSubtitles(e.target.checked)}
              />
              Burn / mux subtitles
            </label>
            <label>
              Engine
              <select value={engine} onChange={(e) => setEngine(e.target.value)}>
                <option value="local">Local (CPU) preview engine</option>
                <option value="ltx2" disabled={!ltx?.available}>
                  LTX-2.5 (GPU server)
                  {!ltx?.available ? " — unavailable" : ""}
                </option>
              </select>
            </label>
          </div>
          {engine === "ltx2" && !ltx?.available && (
            <p className="video-hint">Configure LTX_WORKER_URL to enable the GPU engine.</p>
          )}

          <h3>Characters (1–6)</h3>
          <div className="video-characters">
            {characters.map((c, i) => (
              <div className="video-character" key={i}>
                <div className="video-character-preview">
                  {c.previewUrl ? (
                    <img src={c.previewUrl} alt={c.name} />
                  ) : (
                    <div className="video-character-placeholder">
                      <Upload size={18} />
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => onCharacterFile(i, e.target.files?.[0] || null)}
                  />
                </div>
                <input
                  type="text"
                  value={c.name}
                  placeholder="Name"
                  onChange={(e) => updateCharacter(i, { name: e.target.value })}
                />
                <select
                  value={c.voice_id}
                  onChange={(e) => updateCharacter(i, { voice_id: e.target.value })}
                >
                  {voices.map((v) => (
                    <option key={v.voice_id} value={v.voice_id}>
                      {v.name} ({v.language || "en"})
                    </option>
                  ))}
                </select>
                {characters.length > 1 && (
                  <button
                    type="button"
                    className="ghost-button"
                    onClick={() => setCharacters((prev) => prev.filter((_, idx) => idx !== i))}
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            ))}
          </div>
          {characters.length < 6 && (
            <button
              type="button"
              className="ghost-button"
              onClick={() =>
                setCharacters((prev) => [
                  ...prev,
                  {
                    name: `Character ${prev.length + 1}`,
                    voice_id: voices[0]?.voice_id || "en-US-JennyNeural",
                    file: null,
                    previewUrl: null,
                  },
                ])
              }
            >
              <Plus size={14} /> Add character
            </button>
          )}

          <label className="checkbox-row" style={{ marginTop: 16 }}>
            <input
              type="checkbox"
              checked={useScenes}
              onChange={(e) => setUseScenes(e.target.checked)}
            />
            Multi-scene script
          </label>
          {useScenes && (
            <div className="video-scenes">
              {scenes.map((s, i) => (
                <div className="video-scene" key={i}>
                  <strong>Scene {i + 1}</strong>
                  <textarea
                    rows={2}
                    placeholder="Scene prompt"
                    value={s.prompt}
                    onChange={(e) =>
                      setScenes((prev) =>
                        prev.map((sc, idx) => (idx === i ? { ...sc, prompt: e.target.value } : sc))
                      )
                    }
                  />
                  <textarea
                    rows={2}
                    placeholder="Dialogue"
                    value={s.dialogue_text}
                    onChange={(e) =>
                      setScenes((prev) =>
                        prev.map((sc, idx) =>
                          idx === i ? { ...sc, dialogue_text: e.target.value } : sc
                        )
                      )
                    }
                  />
                  <div className="video-grid-2">
                    <select
                      value={s.character_name}
                      onChange={(e) =>
                        setScenes((prev) =>
                          prev.map((sc, idx) =>
                            idx === i ? { ...sc, character_name: e.target.value } : sc
                          )
                        )
                      }
                    >
                      {characters.map((c) => (
                        <option key={c.name} value={c.name}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min={2}
                      max={60}
                      value={s.duration_seconds}
                      onChange={(e) =>
                        setScenes((prev) =>
                          prev.map((sc, idx) =>
                            idx === i
                              ? { ...sc, duration_seconds: Number(e.target.value) }
                              : sc
                          )
                        )
                      }
                    />
                  </div>
                </div>
              ))}
              <button
                type="button"
                className="ghost-button"
                onClick={() =>
                  setScenes((prev) => [
                    ...prev,
                    {
                      prompt: "",
                      dialogue_text: "",
                      character_name: characters[0]?.name || "Alex",
                      duration_seconds: 8,
                    },
                  ])
                }
              >
                <Plus size={14} /> Add scene
              </button>
            </div>
          )}

          {error && <p className="video-error">{error}</p>}
          <button className="primary-button" disabled={submitting} onClick={submitJob}>
            {submitting ? "Queuing…" : "Generate Video"}
          </button>

          {activeJob && (
            <div className="video-progress">
              <div className="video-progress-meta">
                <strong>Job #{activeJob.id}</strong>
                <span>
                  {activeJob.status} — {activeJob.progress || 0}%
                </span>
              </div>
              <div className="video-progress-bar">
                <div style={{ width: `${activeJob.progress || 0}%` }} />
              </div>
              {activeJob.error_message && (
                <p className="video-error">{activeJob.error_message}</p>
              )}
            </div>
          )}
        </div>
      )}

      {tab === "gallery" && (
        <div className="generation-card video-gallery">
          <video
            ref={videoRef}
            controls
            className="video-player"
            onEnded={() => setPlayingId(null)}
          />
          <div className="video-gallery-grid">
            {videos.map((item) => (
              <div className="video-card" key={item.id}>
                <div className="video-card-body">
                  <strong>#{item.id}</strong>
                  <p>{item.prompt.slice(0, 90)}{item.prompt.length > 90 ? "…" : ""}</p>
                  <small>
                    {item.category} · {item.status} · {item.orientation} · {item.resolution}
                  </small>
                </div>
                <div className="video-card-actions">
                  {item.has_output && (
                    <>
                      <button type="button" onClick={() => playVideo(item)} title="Play">
                        {playingId === item.id ? <Pause size={16} /> : <Play size={16} />}
                      </button>
                      <button type="button" onClick={() => downloadVideo(item)} title="Download">
                        <Download size={16} />
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={async () => {
                      const full = await apiRequest<VideoItem>(`/video/${item.id}`);
                      setSelected(full);
                      setTab("details");
                    }}
                  >
                    Details
                  </button>
                  <button type="button" onClick={() => deleteVideo(item.id)} title="Delete">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
            {videos.length === 0 && <p>No videos yet — create one above.</p>}
          </div>
        </div>
      )}

      {tab === "details" && selected && (
        <div className="generation-card video-details">
          <h3>Video #{selected.id}</h3>
          <p>{selected.prompt}</p>
          <ul className="video-detail-list">
            <li>Status: {selected.status} ({selected.progress}%)</li>
            <li>Category: {selected.category}</li>
            <li>Length: {selected.length_preset} / {selected.duration_seconds}s</li>
            <li>
              {selected.orientation} · {selected.resolution} · {selected.fps}fps · {selected.engine}
            </li>
            <li>Audio: {selected.audio_mode} · Subtitles: {selected.subtitles ? "on" : "off"}</li>
          </ul>
          <h4>Characters</h4>
          <ul>
            {(selected.characters || []).map((c: any) => (
              <li key={c.id}>
                {c.name} — voice {c.voice_id}
              </li>
            ))}
          </ul>
          <h4>Scenes</h4>
          <ul>
            {(selected.scenes || []).map((s: any) => (
              <li key={s.id}>
                #{s.scene_index + 1} {s.character_name}: {s.dialogue_text || s.prompt}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
