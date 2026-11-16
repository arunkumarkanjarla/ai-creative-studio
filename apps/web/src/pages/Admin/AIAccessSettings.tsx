import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000/api/v1";

type Studio = "image" | "audio" | "video";

interface StudioSetting {
  id: number;
  studio: Studio;
  guest_access_enabled: boolean;
  guest_generation_limit: number;
  guest_limit_period: "day" | "week" | "month" | "lifetime";
  authenticated_limit_enabled: boolean;
  authenticated_generation_limit: number | null;
}

const STUDIO_TITLES: Record<Studio, string> = {
  image: "Text-to-Image",
  audio: "Text-to-Audio",
  video: "Text-to-Video",
};

export default function AIAccessSettings() {
  const [settings, setSettings] = useState<StudioSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<Studio | null>(null);
  const [message, setMessage] = useState("");

  const token = localStorage.getItem("access_token");

  const loadSettings = async () => {
    try {
      const response = await fetch(`${API_BASE}/ai-access/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Unable to load AI access settings.");
      }

      const data = await response.json();
      setSettings(data);
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Something went wrong."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const updateSetting = (
    studio: Studio,
    field: keyof StudioSetting,
    value: unknown
  ) => {
    setSettings((previous) =>
      previous.map((item) =>
        item.studio === studio ? { ...item, [field]: value } : item
      )
    );
  };

  const saveSetting = async (setting: StudioSetting) => {
    setSaving(setting.studio);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/ai-access/settings/${setting.studio}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            guest_access_enabled: setting.guest_access_enabled,
            guest_generation_limit: setting.guest_generation_limit,
            guest_limit_period: setting.guest_limit_period,
            authenticated_limit_enabled: setting.authenticated_limit_enabled,
            authenticated_generation_limit: setting.authenticated_limit_enabled
              ? setting.authenticated_generation_limit
              : null,
          }),
        }
      );

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.detail || "Unable to save settings.");
      }

      setSettings((previous) =>
        previous.map((item) =>
          item.studio === setting.studio ? result : item
        )
      );

      setMessage(
        `${STUDIO_TITLES[setting.studio]} settings saved successfully.`
      );
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to save settings."
      );
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return <div className="content-page">Loading AI access settings...</div>;
  }

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1>AI Access Settings</h1>
          <p>Configure guest and authenticated generation limits.</p>
        </div>
      </div>

      {message && <div className="alert">{message}</div>}

      <div className="ai-settings-grid">
        {settings.map((setting) => (
          <section className="studio-card ai-setting-card" key={setting.studio}>
            <h2>{STUDIO_TITLES[setting.studio]}</h2>

            <h3>Guest access</h3>

            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={setting.guest_access_enabled}
                onChange={(e) =>
                  updateSetting(
                    setting.studio,
                    "guest_access_enabled",
                    e.target.checked
                  )
                }
              />
              Enable guest access
            </label>

            <label>
              Maximum guest generations
              <input
                type="number"
                min="0"
                max="10000"
                value={setting.guest_generation_limit}
                onChange={(e) =>
                  updateSetting(
                    setting.studio,
                    "guest_generation_limit",
                    Number(e.target.value)
                  )
                }
              />
            </label>

            <label>
              Reset period
              <select
                value={setting.guest_limit_period}
                onChange={(e) =>
                  updateSetting(
                    setting.studio,
                    "guest_limit_period",
                    e.target.value
                  )
                }
              >
                <option value="day">Daily</option>
                <option value="week">Weekly</option>
                <option value="month">Monthly</option>
                <option value="lifetime">Lifetime</option>
              </select>
            </label>

            <hr />

            <h3>Logged-in user access</h3>

            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={setting.authenticated_limit_enabled}
                onChange={(e) =>
                  updateSetting(
                    setting.studio,
                    "authenticated_limit_enabled",
                    e.target.checked
                  )
                }
              />
              Enable generation limit
            </label>

            {setting.authenticated_limit_enabled && (
              <label>
                Maximum generations
                <input
                  type="number"
                  min="0"
                  max="100000"
                  value={setting.authenticated_generation_limit ?? 10}
                  onChange={(e) =>
                    updateSetting(
                      setting.studio,
                      "authenticated_generation_limit",
                      Number(e.target.value)
                    )
                  }
                />
              </label>
            )}

            <button
              type="button"
              className="primary-button"
              disabled={saving === setting.studio}
              onClick={() => saveSetting(setting)}
            >
              {saving === setting.studio ? "Saving..." : "Save Settings"}
            </button>
          </section>
        ))}
      </div>
    </div>
  );
}
