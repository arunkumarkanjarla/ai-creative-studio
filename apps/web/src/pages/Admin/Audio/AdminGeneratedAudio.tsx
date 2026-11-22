import { useState, useEffect, useRef } from "react";
import { AudioLines, Download, Trash2, ChevronLeft, ChevronRight, FileDown, Search } from "lucide-react";
import { format, parseISO } from "date-fns";
import { apiRequest } from "../../../services/api";

interface GeneratedAudioItem {
  id: number;
  user: { type: string; name?: string; email?: string; visitor_id?: string } | null;
  voice: { name?: string; language?: string; region?: string; gender?: string; voice_type?: string };
  text_preview: string;
  full_text: string;
  pitch: number;
  rate: number;
  volume: number;
  output_format: string;
  duration: number;
  file_size: number;
  status: string;
  created_at: string;
  file_path: string;
  file_exists: boolean;
  download_url: string | null;
}

export default function AdminGeneratedAudio() {
  const [summary, setSummary] = useState<any>(null);
  const [items, setItems] = useState<GeneratedAudioItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(50);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  
  // Filters
  const [search, setSearch] = useState("");
  const [userType, setUserType] = useState("");
  const [voice] = useState("");
  const [language] = useState("");
  const [status, setStatus] = useState("");
  const [dateFrom] = useState("");
  const [dateTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchList();
  }, [page, search, userType, voice, language, status, dateFrom, dateTo, sortBy, sortOrder]);

  const fetchSummary = async () => {
    try {
      const data = await apiRequest<any>("/admin/audio/generated/summary");
      setSummary(data);
    } catch (err) {
      console.error("Failed to fetch summary:", err);
    }
  };

  const fetchList = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        limit: String(limit),
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (search) params.append("search", search);
      if (userType) params.append("user_type", userType);
      if (voice) params.append("voice", voice);
      if (language) params.append("language", language);
      if (status) params.append("status", status);
      if (dateFrom) params.append("date_from", dateFrom);
      if (dateTo) params.append("date_to", dateTo);

      const data = await apiRequest<any>(`/admin/audio/generated/list?${params}`);
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch list:", err);
    } finally {
      setLoading(false);
    }
  };

  const playAudio = async (item: GeneratedAudioItem) => {
    if (playingId === item.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`http://localhost:8000/api/v1/admin/audio/generated/${item.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to fetch audio");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setPlayingId(null);
        URL.revokeObjectURL(url);
      };

      audio.play();
      setPlayingId(item.id);
    } catch (err) {
      console.error("Failed to play audio:", err);
      alert("Failed to play audio");
    }
  };

  const downloadAudio = async (item: GeneratedAudioItem) => {
    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`http://localhost:8000/api/v1/admin/audio/generated/${item.id}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Failed to download");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `tts_${item.id}.${item.output_format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download:", err);
      alert("Failed to download audio");
    }
  };

  const deleteItem = async (id: number) => {
    if (!confirm("Delete this audio file? This cannot be undone.")) return;

    try {
      await apiRequest(`/admin/audio/generated/${id}`, { method: "DELETE" });
      fetchList();
      fetchSummary();
    } catch (err) {
      console.error("Failed to delete:", err);
      alert("Failed to delete");
    }
  };

  const bulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} selected audio files? This cannot be undone.`)) return;

    try {
      await apiRequest("/admin/audio/generated/bulk-delete", {
        method: "POST",
        body: JSON.stringify(Array.from(selectedIds)),
      });

      setSelectedIds(new Set());
      fetchList();
      fetchSummary();
    } catch (err) {
      console.error("Failed to bulk delete:", err);
      alert("Failed to delete");
    }
  };

  const exportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (userType) params.append("user_type", userType);
      if (voice) params.append("voice", voice);
      if (language) params.append("language", language);
      if (status) params.append("status", status);
      if (dateFrom) params.append("date_from", dateFrom);
      if (dateTo) params.append("date_to", dateTo);

      const token = localStorage.getItem("access_token");
      const response = await fetch(`http://localhost:8000/api/v1/admin/audio/generated/export?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!response.ok) throw new Error("Export failed");

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `generated_audio_${format(new Date(), "yyyy-MM-dd")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export:", err);
      alert("Failed to export CSV");
    }
  };

  const toggleSelect = (id: number) => {
    const newSet = new Set(selectedIds);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setSelectedIds(newSet);
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((item) => item.id)));
    }
  };

  const formatBytes = (bytes: number | null | undefined) => {
    if (bytes == null || Number.isNaN(bytes)) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDuration = (seconds: number | null | undefined) => {
    if (seconds == null || Number.isNaN(seconds)) return "-";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1><AudioLines size={32} /> Generated Audio (TTS)</h1>
          <p>Admin management of text-to-speech generated audio</p>
        </div>
      </div>

      {summary && (
        <div className="kpi-grid" style={{ marginBottom: "24px" }}>
          <div className="kpi-card">
            <div className="kpi-header">
              <AudioLines size={20} />
              <span>Total Files</span>
            </div>
            <div className="kpi-value">{summary.total_files.toLocaleString()}</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <FileDown size={20} />
              <span>Total Size</span>
            </div>
            <div className="kpi-value">{formatBytes(summary.total_size)}</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <AudioLines size={20} />
              <span>Total Duration</span>
            </div>
            <div className="kpi-value">{formatDuration(summary.total_duration)}</div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <AudioLines size={20} />
              <span>Today</span>
            </div>
            <div className="kpi-value">{summary.today_count}</div>
          </div>
        </div>
      )}

      <div className="analytics-controls" style={{ marginBottom: "16px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "200px" }}>
          <Search size={16} style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search text..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="search-input"
            style={{ paddingLeft: "32px", width: "100%" }}
          />
        </div>

        <select value={userType} onChange={(e) => { setUserType(e.target.value); setPage(1); }} className="filter-select">
          <option value="">All Users</option>
          <option value="user">Signed-in</option>
          <option value="guest">Guest</option>
        </select>

        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="filter-select">
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="processing">Processing</option>
        </select>

        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="filter-select">
          <option value="created_at">Sort by Date</option>
          <option value="duration">Sort by Duration</option>
          <option value="file_size">Sort by Size</option>
        </select>

        <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)} className="filter-select">
          <option value="desc">Descending</option>
          <option value="asc">Ascending</option>
        </select>

        <button className="secondary-button" onClick={exportCSV}>
          <FileDown size={16} /> Export CSV
        </button>

        {selectedIds.size > 0 && (
          <button className="secondary-button" onClick={bulkDelete} style={{ color: "var(--error-text)" }}>
            <Trash2 size={16} /> Delete {selectedIds.size}
          </button>
        )}
      </div>

      {loading ? (
        <div className="page-loader">Loading...</div>
      ) : (
        <>
          <div className="data-table">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "40px" }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.size === items.length && items.length > 0}
                      onChange={toggleSelectAll}
                    />
                  </th>
                  <th>Play</th>
                  <th>User</th>
                  <th>Voice</th>
                  <th>Text</th>
                  <th>Settings</th>
                  <th>Format</th>
                  <th>Duration</th>
                  <th>Size</th>
                  <th>Status</th>
                  <th>Created</th>
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
                        onChange={() => toggleSelect(item.id)}
                      />
                    </td>
                    <td>
                      {item.file_exists ? (
                        <button
                          className="secondary-button"
                          style={{ padding: "4px 8px", fontSize: "12px" }}
                          onClick={() => playAudio(item)}
                          title={playingId === item.id ? "Pause" : "Play"}
                        >
                          {playingId === item.id ? "⏸" : "▶"}
                        </button>
                      ) : (
                        <span style={{ fontSize: "11px", color: "var(--error-text)" }}>Missing</span>
                      )}
                    </td>
                    <td>
                      {item.user?.type === "user" ? (
                        <div>
                          <div>{item.user.name}</div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{item.user.email}</div>
                        </div>
                      ) : (
                        <div>
                          <div>Guest</div>
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            {item.user?.visitor_id || "unknown"}
                          </div>
                        </div>
                      )}
                    </td>
                    <td>
                      <div>{item.voice.name}</div>
                      {item.voice.language && (
                        <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          {item.voice.language}
                          {item.voice.region && ` • ${item.voice.region}`}
                        </div>
                      )}
                    </td>
                    <td style={{ maxWidth: "300px" }}>
                      {expandedId === item.id ? (
                        <div>
                          <div style={{ fontSize: "12px", marginBottom: "4px" }}>{item.full_text}</div>
                          <button
                            className="secondary-button"
                            style={{ padding: "2px 6px", fontSize: "10px" }}
                            onClick={() => setExpandedId(null)}
                          >
                            Collapse
                          </button>
                        </div>
                      ) : (
                        <div>
                          <div style={{ fontSize: "12px" }}>{item.text_preview}</div>
                          {item.text_preview !== item.full_text && (
                            <button
                              className="secondary-button"
                              style={{ padding: "2px 6px", fontSize: "10px", marginTop: "4px" }}
                              onClick={() => setExpandedId(item.id)}
                            >
                              Expand
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                    <td style={{ fontSize: "11px" }}>
                      <div>Rate: {item.rate}x</div>
                      <div>Pitch: {item.pitch}x</div>
                      <div>Volume: {item.volume}x</div>
                    </td>
                    <td>{item.output_format.toUpperCase()}</td>
                    <td>{formatDuration(item.duration)}</td>
                    <td>{formatBytes(item.file_size)}</td>
                    <td>
                      <span className={`status-badge ${item.status}`}>{item.status}</span>
                    </td>
                    <td style={{ fontSize: "11px" }}>{format(parseISO(item.created_at), "MMM d, h:mm a")}</td>
                    <td>
                      <div style={{ display: "flex", gap: "4px" }}>
                        {item.file_exists && (
                          <button
                            className="secondary-button"
                            style={{ padding: "4px 8px", fontSize: "12px" }}
                            onClick={() => downloadAudio(item)}
                            title="Download"
                          >
                            <Download size={14} />
                          </button>
                        )}
                        <button
                          className="secondary-button"
                          style={{ padding: "4px 8px", fontSize: "12px", color: "var(--error-text)" }}
                          onClick={() => deleteItem(item.id)}
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pagination" style={{ marginTop: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              Showing {(page - 1) * limit + 1} - {Math.min(page * limit, total)} of {total}
            </div>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                className="secondary-button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft size={16} /> Previous
              </button>
              <button
                className="secondary-button"
                onClick={() => setPage((p) => p + 1)}
                disabled={page * limit >= total}
              >
                Next <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
