import { useEffect, useState } from "react";
import { apiRequest } from "../../../services/api";

export default function AdminVideoJobs() {
  const [items, setItems] = useState<any[]>([]);

  const load = async () => {
    const data = await apiRequest<any>("/admin/video/jobs");
    setItems(data.items || []);
  };

  useEffect(() => {
    load().catch(console.error);
    const id = window.setInterval(() => load().catch(console.error), 3000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Video Jobs Queue</h1>
          <p>Queued and processing jobs with live progress.</p>
        </div>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Status</th>
            <th>Progress</th>
            <th>Engine</th>
            <th>Category</th>
            <th>Prompt</th>
            <th>Started</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.user?.email || item.user?.name || "—"}</td>
              <td>{item.status}</td>
              <td>
                <div className="video-progress-bar inline">
                  <div style={{ width: `${item.progress || 0}%` }} />
                </div>
                {item.progress || 0}%
              </td>
              <td>{item.engine}</td>
              <td>{item.category}</td>
              <td>{item.prompt_preview}</td>
              <td>{item.processing_started_at || item.created_at || "—"}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={8}>No active jobs</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
