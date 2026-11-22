import { useEffect, useState } from "react";
import { apiRequest } from "../../../services/api";

export default function AdminVideoErrors() {
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 50;

  useEffect(() => {
    apiRequest<any>(`/admin/video/errors?page=${page}&limit=${limit}`)
      .then((data) => {
        setItems(data.items || []);
        setTotal(data.total || 0);
      })
      .catch(console.error);
  }, [page]);

  const pages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Video Failed / Errors</h1>
          <p>Failed video generation jobs and error messages.</p>
        </div>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>User</th>
            <th>Category</th>
            <th>Engine</th>
            <th>Prompt</th>
            <th>Error</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.user?.email || item.user?.name || "—"}</td>
              <td>{item.category}</td>
              <td>{item.engine}</td>
              <td>{item.prompt_preview}</td>
              <td className="video-error-cell">{item.error_message}</td>
              <td>{item.created_at}</td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={7}>No failed jobs</td></tr>}
        </tbody>
      </table>
      <div className="admin-pagination">
        <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
        <span>
          Page {page} / {pages}
        </span>
        <button disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>
    </div>
  );
}
