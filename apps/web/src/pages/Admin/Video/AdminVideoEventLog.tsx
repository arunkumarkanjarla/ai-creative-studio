import { useEffect, useState } from "react";
import { FileDown, Search } from "lucide-react";
import { apiRequest, apiFetch } from "../../../services/api";

export default function AdminVideoEventLog() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const limit = 50;

  const load = async () => {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });
    if (action) params.set("action", action);
    if (status) params.set("status", status);
    if (search) params.set("search", search);
    const data = await apiRequest<any>(`/admin/video/events?${params}`);
    setItems(data.items || []);
    setTotal(data.total || 0);
  };

  useEffect(() => {
    load().catch(console.error);
  }, [page, action, status, search]);

  const exportCsv = async () => {
    const params = new URLSearchParams();
    if (action) params.set("action", action);
    if (status) params.set("status", status);
    const res = await apiFetch(`/admin/video/events/export?${params}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "video_events.csv";
    a.click();
  };

  const pages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Video Event Log</h1>
          <p>Filterable create / progress / play / download / delete events.</p>
        </div>
      </div>

      <div className="admin-filters">
        <div className="admin-search">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => { setPage(1); setSearch(e.target.value); }}
            placeholder="Search…"
          />
        </div>
        <select value={action} onChange={(e) => { setPage(1); setAction(e.target.value); }}>
          <option value="">All actions</option>
          {["create", "start", "progress", "complete", "fail", "play", "download", "delete"].map(
            (a) => (
              <option key={a} value={a}>
                {a}
              </option>
            )
          )}
        </select>
        <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value); }}>
          <option value="">All statuses</option>
          <option value="success">success</option>
          <option value="failed">failed</option>
          <option value="rate_limited">rate_limited</option>
        </select>
        <button type="button" className="ghost-button" onClick={exportCsv}>
          <FileDown size={14} /> Export CSV
        </button>
      </div>

      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>When</th>
            <th>User</th>
            <th>Action</th>
            <th>Status</th>
            <th>Project</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e) => (
            <tr key={e.id}>
              <td>{e.id}</td>
              <td>{e.created_at}</td>
              <td>{e.user?.email || e.user?.name || "—"}</td>
              <td>{e.action}</td>
              <td>{e.status}</td>
              <td>{e.project_id ?? "—"}</td>
              <td>{e.error_message || "—"}</td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={7}>No events</td></tr>}
        </tbody>
      </table>

      <div className="admin-pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
        <span>
          Page {page} / {pages} ({total})
        </span>
        <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>
    </div>
  );
}
