
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "../../services/api";

export default function CreateUser() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    mobile: "",
    password: "",
    can_access_image: false,
    can_access_audio: false,
    can_access_video: false,
  });

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  function updateField(name: string, value: string | boolean) {
    setForm((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      await apiRequest("/users/", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          role: "user",
          mobile: form.mobile || null,
        }),
      });

      navigate("/users");
    } catch (err) {
      setError(err instanceof Error ? err.message : "User creation failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="content-page">
      <h1>Create New User</h1>
      <p>Create a user account and assign studio permissions.</p>

      <form className="form-card" onSubmit={handleSubmit}>
        <label>Full Name</label>
        <input
          value={form.name}
          onChange={(e) => updateField("name", e.target.value)}
          required
          maxLength={150}
          placeholder="Enter full name"
        />

        <label>Email Address</label>
        <input
          type="email"
          value={form.email}
          onChange={(e) => updateField("email", e.target.value)}
          required
          placeholder="Enter email address"
        />

        <label>Mobile Number (Optional)</label>
        <input
          type="tel"
          value={form.mobile}
          onChange={(e) => updateField("mobile", e.target.value)}
          placeholder="Enter mobile number"
        />

        <label>Password</label>
        <input
          type="password"
          value={form.password}
          onChange={(e) => updateField("password", e.target.value)}
          required
          minLength={12}
          placeholder="Minimum 12 characters"
        />

        <h3>Studio Permissions</h3>

        {[
          ["can_access_image", "Image Studio"],
          ["can_access_audio", "Audio Studio"],
          ["can_access_video", "Video Studio"],
        ].map(([field, label]) => (
          <label className="permission-option" key={field}>
            <input
              type="checkbox"
              checked={Boolean(form[field as keyof typeof form])}
              onChange={(e) => updateField(field, e.target.checked)}
            />
            {label}
          </label>
        ))}

        {error && <div className="error-message">{error}</div>}

        <div className="form-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => navigate("/users")}
          >
            Cancel
          </button>

          <button className="primary-button" disabled={saving}>
            {saving ? "Creating..." : "Create User"}
          </button>
        </div>
      </form>
    </div>
  );
}
