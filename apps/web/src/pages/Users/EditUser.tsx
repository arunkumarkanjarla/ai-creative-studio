
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { apiRequest } from "../../services/api";
import type { User } from "../../services/auth";

export default function EditUser() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await apiRequest<User>(`/users/${id}`);
        setUser(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load user");
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [id]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    if (!user) return;

    try {
      await apiRequest(`/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: user.name,
          mobile: user.mobile,
          can_access_image: user.can_access_image,
          can_access_audio: user.can_access_audio,
          can_access_video: user.can_access_video,
          is_active: user.is_active,
        }),
      });

      navigate("/users");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  if (loading) return <p>Loading user...</p>;
  if (!user) return <p>{error || "User not found"}</p>;

  return (
    <div className="content-page">
      <h1>Edit User</h1>

      <form className="form-card" onSubmit={handleSubmit}>
        <label>Name</label>
        <input
          value={user.name}
          onChange={(e) => setUser({ ...user, name: e.target.value })}
          required
        />

        <label>Email</label>
        <input value={user.email} disabled />

        <label>Mobile</label>
        <input
          value={user.mobile || ""}
          onChange={(e) =>
            setUser({ ...user, mobile: e.target.value || null })
          }
        />

        <h3>Studio Permissions</h3>

        <label className="permission-option">
          <input
            type="checkbox"
            checked={user.can_access_image}
            onChange={(e) =>
              setUser({ ...user, can_access_image: e.target.checked })
            }
          />
          Image Studio
        </label>

        <label className="permission-option">
          <input
            type="checkbox"
            checked={user.can_access_audio}
            onChange={(e) =>
              setUser({ ...user, can_access_audio: e.target.checked })
            }
          />
          Audio Studio
        </label>

        <label className="permission-option">
          <input
            type="checkbox"
            checked={user.can_access_video}
            onChange={(e) =>
              setUser({ ...user, can_access_video: e.target.checked })
            }
          />
          Video Studio
        </label>

        <label className="permission-option">
          <input
            type="checkbox"
            checked={user.is_active}
            onChange={(e) =>
              setUser({ ...user, is_active: e.target.checked })
            }
          />
          Active Account
        </label>

        {error && <div className="error-message">{error}</div>}

        <button className="primary-button">Save Changes</button>
      </form>
    </div>
  );
}
