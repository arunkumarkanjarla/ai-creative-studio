import { useEffect, useState } from "react";
import { apiRequest } from "../../../services/api";

export default function AdminVideoUsers() {
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    apiRequest<any>("/admin/video/users")
      .then((data) => setItems(data.items || []))
      .catch(console.error);
  }, []);

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Video Users</h1>
          <p>Per-user generation counts and render averages.</p>
        </div>
      </div>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Total</th>
            <th>Completed</th>
            <th>Failed</th>
            <th>Total size</th>
            <th>Avg render</th>
          </tr>
        </thead>
        <tbody>
          {items.map((u) => (
            <tr key={u.user_id}>
              <td>{u.name}</td>
              <td>{u.email}</td>
              <td>{u.total}</td>
              <td>{u.completed}</td>
              <td>{u.failed}</td>
              <td>{Math.round((u.total_size || 0) / 1024)} KB</td>
              <td>{u.avg_render_seconds}s</td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={7}>No users yet</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
