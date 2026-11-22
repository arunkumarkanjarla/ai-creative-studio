import { useState, useEffect } from "react";
import { AudioLines, Search } from "lucide-react";
import { apiRequest } from "../../../services/api";

interface Voice {
  id: number;
  voice_id: string;
  name: string;
  gender: string;
  age_group: string;
  language: string;
  locale: string;
  region: string;
  country: string;
  accent: string;
  voice_type: string;
  is_custom: boolean;
  is_active: boolean;
  usage_count: number;
  created_at: string;
}

export default function AdminVoiceLibrary() {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [filteredVoices, setFilteredVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [genderFilter, setGenderFilter] = useState("");
  const [languageFilter, setLanguageFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [includeCustom, setIncludeCustom] = useState(true);

  useEffect(() => {
    fetchVoices();
  }, [includeCustom]);

  useEffect(() => {
    filterVoices();
  }, [voices, search, genderFilter, languageFilter, typeFilter]);

  const fetchVoices = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        include_custom: String(includeCustom),
      });

      const data = await apiRequest<any>(`/admin/audio/voices/list?${params}`);
      setVoices(data.voices);
    } catch (err) {
      console.error("Failed to fetch voices:", err);
    } finally {
      setLoading(false);
    }
  };

  const filterVoices = () => {
    let filtered = [...voices];

    if (search) {
      const searchLower = search.toLowerCase();
      filtered = filtered.filter(
        (v) =>
          v.name.toLowerCase().includes(searchLower) ||
          v.voice_id.toLowerCase().includes(searchLower) ||
          v.language.toLowerCase().includes(searchLower)
      );
    }

    if (genderFilter) {
      filtered = filtered.filter((v) => v.gender === genderFilter);
    }

    if (languageFilter) {
      filtered = filtered.filter((v) => v.language === languageFilter);
    }

    if (typeFilter) {
      if (typeFilter === "custom") {
        filtered = filtered.filter((v) => v.is_custom);
      } else if (typeFilter === "builtin") {
        filtered = filtered.filter((v) => !v.is_custom);
      }
    }

    setFilteredVoices(filtered);
  };

  const toggleActive = async (voice: Voice) => {
    try {
      await apiRequest(`/admin/audio/voices/${voice.id}/toggle`, { method: "PATCH" });
      fetchVoices();
    } catch (err) {
      console.error("Failed to toggle voice:", err);
      alert("Failed to toggle voice status");
    }
  };

  const uniqueLanguages = Array.from(new Set(voices.map((v) => v.language))).sort();

  const totalUsage = filteredVoices.reduce((sum, v) => sum + v.usage_count, 0);
  const activeCount = filteredVoices.filter((v) => v.is_active).length;
  const customCount = filteredVoices.filter((v) => v.is_custom).length;

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1><AudioLines size={32} /> Voice Library</h1>
          <p>Manage available voices and custom voice profiles</p>
        </div>
      </div>

      <div className="kpi-grid" style={{ marginBottom: "24px" }}>
        <div className="kpi-card">
          <div className="kpi-header">
            <AudioLines size={20} />
            <span>Total Voices</span>
          </div>
          <div className="kpi-value">{filteredVoices.length}</div>
          <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
            {activeCount} active, {filteredVoices.length - activeCount} disabled
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <AudioLines size={20} />
            <span>Custom Voices</span>
          </div>
          <div className="kpi-value">{customCount}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <AudioLines size={20} />
            <span>Total Usage</span>
          </div>
          <div className="kpi-value">{totalUsage.toLocaleString()}</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <AudioLines size={20} />
            <span>Languages</span>
          </div>
          <div className="kpi-value">{uniqueLanguages.length}</div>
        </div>
      </div>

      <div className="analytics-controls" style={{ marginBottom: "16px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "200px" }}>
          <Search size={16} style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search voices..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
            style={{ paddingLeft: "32px", width: "100%" }}
          />
        </div>

        <select value={genderFilter} onChange={(e) => setGenderFilter(e.target.value)} className="filter-select">
          <option value="">All Genders</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="child">Child</option>
        </select>

        <select value={languageFilter} onChange={(e) => setLanguageFilter(e.target.value)} className="filter-select">
          <option value="">All Languages</option>
          {uniqueLanguages.map((lang) => (
            <option key={lang} value={lang}>
              {lang}
            </option>
          ))}
        </select>

        <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="filter-select">
          <option value="">All Types</option>
          <option value="builtin">Built-in</option>
          <option value="custom">Custom</option>
        </select>

        <label style={{ display: "flex", alignItems: "center", gap: "8px", padding: "0 12px", fontSize: "14px" }}>
          <input type="checkbox" checked={includeCustom} onChange={(e) => setIncludeCustom(e.target.checked)} />
          Include Custom
        </label>
      </div>

      {loading ? (
        <div className="page-loader">Loading...</div>
      ) : (
        <div className="data-table">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Voice ID</th>
                <th>Gender</th>
                <th>Language</th>
                <th>Region / Country</th>
                <th>Accent</th>
                <th>Type</th>
                <th>Usage</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredVoices.map((voice) => (
                <tr key={voice.id} style={{ opacity: voice.is_active ? 1 : 0.6 }}>
                  <td>
                    <div style={{ fontWeight: "500" }}>{voice.name}</div>
                    {voice.is_custom && (
                      <span
                        style={{
                          display: "inline-block",
                          marginTop: "4px",
                          padding: "2px 6px",
                          fontSize: "10px",
                          backgroundColor: "var(--accent)",
                          color: "white",
                          borderRadius: "4px",
                        }}
                      >
                        Custom
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: "11px", color: "var(--text-muted)" }}>{voice.voice_id}</td>
                  <td>{voice.gender}</td>
                  <td>
                    <div>{voice.language}</div>
                    {voice.locale && (
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{voice.locale}</div>
                    )}
                  </td>
                  <td>
                    {voice.region && <div>{voice.region}</div>}
                    {voice.country && (
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{voice.country}</div>
                    )}
                  </td>
                  <td>{voice.accent || "-"}</td>
                  <td>{voice.voice_type || "-"}</td>
                  <td style={{ fontWeight: "500" }}>{voice.usage_count}</td>
                  <td>
                    <span className={`status-badge ${voice.is_active ? "completed" : "failed"}`}>
                      {voice.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td>
                    <button
                      className="secondary-button"
                      style={{ padding: "4px 12px", fontSize: "12px" }}
                      onClick={() => toggleActive(voice)}
                    >
                      {voice.is_active ? "Disable" : "Enable"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {filteredVoices.length === 0 && !loading && (
        <div style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
          No voices found matching your filters.
        </div>
      )}
    </div>
  );
}
