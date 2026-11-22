import { useEffect, useRef, useState } from "react";
import { Download, Trash2, Play, Pause, Search, FileDown } from "lucide-react";
import { apiRequest } from "../../../services/api";

export default function AdminGeneratedVideos() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [category, setCategory] = useState("");
  const [engine, setEngine] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [playingId, setPlayingId] = useState<number | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const limit = 25;

  const load = async () => {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
      sort_by: "created_at",
      sort_order: "desc",
    });
    if (search) params.set("search", search);
    if (status) params.set("status", status);
    if (category) params.set("category", category);
    if (engine) params.set("engine", engine);
    const data = await apiRequest<any>(`/admin/video/generated/list?${params}`);
    setItems(data.items || []);
    setTotal(data.total || 0);
  };

  useEffect(() => {
    load().catch(console.error);
  }, [page, search, status, category, engine]);

  const authFetchBlob = async (path: string) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`http://localhost:8000${path}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed");
    return URL.createObjectURL(await res.blob());
  };

  const play = async (item: any) => {
    if (!videoRef.current) return;
    if (playingId === item.id) {
      videoRef.current.pause();
      setPlayingId(null);
      return;
    }
    const url = await authFetchBlob(item.stream_url);
    videoRef.current.src = url;
    await videoRef.current.play();
    setPlayingId(item.id);
  };

  const download = async (item: any) => {
    const url = await authFetchBlob(item.download_url);
    const a = document.createElement("a");
    a.href = url;
    a.download = `video_${item.id}.mp4`;
    a.click();
  };

  const remove = async (id: number) => {
    if (!confirm("Delete this video?")) return;
    await apiRequest(`/admin/video/generated/${id}`, { method: "DELETE" });
    await load();
  };

  const bulkDelete = async () => {
    if (!selectedIds.size || !confirm(`Delete ${selectedIds.size} videos?`)) return;
    await apiRequest("/admin/video/generated/bulk-delete", {
      method: "POST",
      body: JSON.stringify({ ids: Array.from(selectedIds) }),
    });
    setSelectedIds(new Set());
    await load();
  };

  const exportCsv = () => {
    const token = localStorage.getItem("access_token");
    window.open(
      `http://localhost:8000/api/v1/admin/video/generated/export?${new URLSearchParams({
        search,
        status,
        category,
        engine,
      })}`,
      "_blank"
    );
    // Prefer authenticated fetch when possible
    void (async () => {
      const res = await fetch(
        `http://localhost:8000/api/v1/admin/video/generated/export?${new URLSearchParams({
          search,
          status,
          category,
          engine,
        })}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} }
      );
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "videos.csv";
      a.click();
    })();
  };

  const pages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Generated Videos</h1>
          <p>Browse, play, export, and delete Video Studio outputs.</p>
        </div>
      </div>

      <video ref={videoRef} controls className="video-player" onEnded={() => setPlayingId(null)} />

      <div className="admin-filters">
        <div className="admin-search">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => { setPage(1); setSearch(e.target.value); }}
            placeholder="Search prompt…"
          />
        </div>
        <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">All statuses</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select value={category} onChange={(e) => { setPage(1); setCategory(e.target.value); }}>
          <option value="">All categories</option>
          <option value="instagram_short">Instagram Short</option>
          <option value="drama">Drama</option>
          <option value="youtube_short">YouTube Short</option>
          <option value="custom">Custom</option>
        </select>
        <select value={engine} onChange={(e) => { setPage(1); setEngine(e.target.value); }}>
          <option value="">All engines</option>
          <option value="local">Local</option>
          <option value="ltx2">LTX-2.5</option>
        </select>
        <button type="button" className="ghost-button" onClick={exportCsv}>
          <FileDown size={14} /> CSV
        </button>
        {selectedIds.size > 0 && (
          <button type="button" className="ghost-button" onClick={bulkDelete}>
            <Trash2 size={14} /> Delete ({selectedIds.size})
          </button>
        )}
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th />
            <th>ID</th>
            <th>User</th>
            <th>Prompt</th>
            <th>Category</th>
            <th>Engine</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.has(item.id)}
                  onChange={(e) => {
                    setSelectedIds((prev) => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(item.id);
                      else next.delete(item.id);
                      return next;
                    });
                  }}
                />
              </td>
              <td>{item.id}</td>
              <td>{item.user?.email || item.user?.name || "—"}</td>
              <td>{item.prompt_preview}</td>
              <td>{item.category}</td>
              <td>{item.engine}</td>
              <td>{item.status}</td>
              <td>{item.duration ? `${Number(item.duration).toFixed(1)}s` : "—"}</td>
              <td className="admin-row-actions">
                {item.file_exists && (
                  <>
                    <button type="button" onClick={() => play(item)}>
                      {playingId === item.id ? <Pause size={14} /> : <Play size={14} />}
                    </button>
                    <button type="button" onClick={() => download(item)}>
                      <Download size={14} />
                    </button>
                  </>
                )}
                <button type="button" onClick={() => remove(item.id)}>
                  <Trash2 size={14} />
                </button>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={9}>No videos found</td></tr>
          )}
        </tbody>
      </table>

      <div className="admin-pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
        <span>
          Page {page} / {pages} ({total} total)
        </span>
        <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>
    </div>
  );
}
