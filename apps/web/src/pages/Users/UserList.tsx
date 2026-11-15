
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Pencil } from "lucide-react";

import { apiRequest } from "../../services/api";
import type { User } from "../../services/auth";

export default function UserList() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadUsers() {
    try {
      const data = await apiRequest<User[]>("/users/");
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1>User Management</h1>
          <p>Manage accounts and studio permissions.</p>
        </div>

        <Link to="/users/create" className="primary-button">
          <Plus size={18} /> Create User
        </Link>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <p>Loading users...</p>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Mobile</th>
                <th>Role</th>
                <th>Studios</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.email}</td>
                  <td>{user.mobile || "—"}</td>
                  <td>{user.role}</td>
                  <td>
                    {[
                      user.can_access_image && "Image",
                      user.can_access_audio && "Audio",
                      user.can_access_video && "Video",
                    ].filter(Boolean).join(", ") || "None"}
                  </td>
                  <td>
                    {user.is_active ? "Active" : "Inactive"}
                  </td>
                  <td>
                    <Link to={`/users/${user.id}/edit`}>
                      <Pencil size={18} />
                    </Link>
                  </td>
                </tr>
              ))}

              {users.length === 0 && (
                <tr>
                  <td colSpan={7}>No users found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
