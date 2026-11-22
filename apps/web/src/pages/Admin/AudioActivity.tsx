import { useState, useEffect } from "react";
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { format, subDays, startOfDay, endOfDay, parseISO } from "date-fns";
import { 
  Calendar, Users, AudioLines, Play, Download, FileText, 
  TrendingUp, ChevronLeft, ChevronRight 
} from "lucide-react";
import { apiRequest } from "../../services/api";

const CHART_COLORS = ["var(--accent)", "var(--accent-strong)", "var(--text-secondary)", "var(--text-muted)"];

type EventsTab = "users" | "log" | "timeline";

interface AudioActivityProps {
  initialTab?: EventsTab;
  initialStatusFilter?: string;
}

export default function AudioActivity({
  initialTab = "users",
  initialStatusFilter = "",
}: AudioActivityProps = {}) {
  const [dateRange, setDateRange] = useState<"today" | "7d" | "30d" | "custom">("7d");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  const [summary, setSummary] = useState<any>(null);
  const [topVoices, setTopVoices] = useState<any[]>([]);
  const [topLanguages, setTopLanguages] = useState<any[]>([]);
  const [timeSeries, setTimeSeries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Events log filters and state
  const [eventsTab, setEventsTab] = useState<EventsTab>(initialTab);
  const [events, setEvents] = useState<any[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsPage, setEventsPage] = useState(0);
  const [eventFilters, setEventFilters] = useState({
    user_type: "",
    action: "",
    status: initialStatusFilter,
    search: ""
  });
  
  // Users list state
  const [users, setUsers] = useState<any[]>([]);
  const [usersFilter, setUsersFilter] = useState<"" | "authenticated" | "guest">("");
  
  // Timeline state
  const [selectedUser, setSelectedUser] = useState<{ type: string; id: string } | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [timelineTotal, setTimelineTotal] = useState(0);
  const [timelinePage, setTimelinePage] = useState(0);

  useEffect(() => {
    const today = new Date();
    let start: Date, end: Date;

    if (dateRange === "custom") {
      if (customStartDate && customEndDate) {
        setStartDate(format(parseISO(customStartDate), "yyyy-MM-dd'T'HH:mm:ss"));
        setEndDate(format(parseISO(customEndDate), "yyyy-MM-dd'T'23:59:59"));
      }
      return;
    }

    switch (dateRange) {
      case "today":
        start = startOfDay(today);
        end = endOfDay(today);
        break;
      case "7d":
        start = subDays(today, 7);
        end = today;
        break;
      case "30d":
        start = subDays(today, 30);
        end = today;
        break;
      default:
        return;
    }

    setStartDate(format(start, "yyyy-MM-dd'T'HH:mm:ss"));
    setEndDate(format(end, "yyyy-MM-dd'T'HH:mm:ss"));
  }, [dateRange, customStartDate, customEndDate]);

  useEffect(() => {
    if (!startDate || !endDate) return;
    fetchSummary();
  }, [startDate, endDate]);
  
  useEffect(() => {
    if (!startDate || !endDate) return;
    if (eventsTab === "users") {
      fetchUsers();
    } else if (eventsTab === "log") {
      fetchEvents();
    }
  }, [eventsTab, startDate, endDate, eventsPage, eventFilters, usersFilter]);
  
  useEffect(() => {
    if (selectedUser) {
      fetchTimeline();
    }
  }, [selectedUser, timelinePage]);

  const fetchSummary = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      
      const data = await apiRequest<any>(`/analytics/audio/summary?${params}`);
      setSummary(data.summary);
      setTopVoices(data.top_voices);
      setTopLanguages(data.top_languages);
      setTimeSeries(data.time_series);
    } catch (err) {
      console.error("Failed to fetch audio analytics:", err);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchEvents = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        limit: "50",
        offset: String(eventsPage * 50)
      });
      
      if (eventFilters.user_type) params.append("user_type", eventFilters.user_type);
      if (eventFilters.action) params.append("action", eventFilters.action);
      if (eventFilters.status) params.append("status", eventFilters.status);
      if (eventFilters.search) params.append("search", eventFilters.search);
      
      const data = await apiRequest<any>(`/analytics/audio/events?${params}`);
      setEvents(data.items);
      setEventsTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch audio events:", err);
    }
  };
  
  const fetchUsers = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        limit: "100",
        offset: "0"
      });
      
      if (usersFilter) params.append("user_type", usersFilter);
      
      const data = await apiRequest<any>(`/analytics/audio/users?${params}`);
      setUsers(data.items);
    } catch (err) {
      console.error("Failed to fetch audio users:", err);
    }
  };
  
  const fetchTimeline = async () => {
    if (!selectedUser) return;
    
    try {
      const params = new URLSearchParams({
        user_type: selectedUser.type,
        limit: "50",
        offset: String(timelinePage * 50)
      });
      
      const data = await apiRequest<any>(`/analytics/audio/timeline/${selectedUser.id}?${params}`);
      setTimeline(data.events);
      setTimelineTotal(data.total_events);
    } catch (err) {
      console.error("Failed to fetch timeline:", err);
    }
  };
  
  const exportCSV = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      
      if (eventFilters.user_type) params.append("user_type", eventFilters.user_type);
      if (eventFilters.action) params.append("action", eventFilters.action);
      if (eventFilters.status) params.append("status", eventFilters.status);
      
      const response = await fetch(`http://localhost:8000/api/v1/analytics/audio/events/csv?${params}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      });
      
      if (!response.ok) throw new Error("Export failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `audio_events_${format(new Date(), "yyyy-MM-dd")}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export CSV:", err);
      alert("Failed to export CSV");
    }
  };

  if (loading && !summary) {
    return <div className="page-loader">Loading audio analytics...</div>;
  }

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1><AudioLines size={32} /> Audio Activity</h1>
          <p>Text-to-speech and speech-to-text usage analytics</p>
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="analytics-controls" style={{ marginBottom: "24px" }}>
        <div className="date-range-tabs">
          <button 
            className={dateRange === "today" ? "tab-active" : "tab-button"}
            onClick={() => setDateRange("today")}
          >
            Today
          </button>
          <button 
            className={dateRange === "7d" ? "tab-active" : "tab-button"}
            onClick={() => setDateRange("7d")}
          >
            Last 7 Days
          </button>
          <button 
            className={dateRange === "30d" ? "tab-active" : "tab-button"}
            onClick={() => setDateRange("30d")}
          >
            Last 30 Days
          </button>
          <button 
            className={dateRange === "custom" ? "tab-active" : "tab-button"}
            onClick={() => setDateRange("custom")}
          >
            <Calendar size={16} /> Custom
          </button>
        </div>

        {dateRange === "custom" && (
          <div className="custom-date-range">
            <input
              type="date"
              value={customStartDate}
              onChange={(e) => setCustomStartDate(e.target.value)}
            />
            <span>to</span>
            <input
              type="date"
              value={customEndDate}
              onChange={(e) => setCustomEndDate(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="kpi-grid" style={{ marginBottom: "32px" }}>
          <div className="kpi-card">
            <div className="kpi-header">
              <AudioLines size={20} />
              <span>Total Events</span>
            </div>
            <div className="kpi-value">{summary.total_events.toLocaleString()}</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              {summary.success_count} success, {summary.failed_count} failed
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <Users size={20} />
              <span>Users & Guests</span>
            </div>
            <div className="kpi-value">
              {summary.unique_users + summary.unique_visitors}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              {summary.unique_users} users, {summary.unique_visitors} guests
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <TrendingUp size={20} />
              <span>TTS / STT</span>
            </div>
            <div className="kpi-value">
              {summary.tts_count} / {summary.stt_count}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              {summary.play_count} plays, {summary.download_count} downloads
            </div>
          </div>

          <div className="kpi-card">
            <div className="kpi-header">
              <FileText size={20} />
              <span>Processing</span>
            </div>
            <div className="kpi-value">
              {(summary.total_characters / 1000).toFixed(1)}K
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "4px" }}>
              {summary.total_minutes.toFixed(1)} min audio
            </div>
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="charts-grid" style={{ marginBottom: "32px" }}>
        <div className="chart-card">
          <h3>Activity Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--text-secondary)"
                tick={{ fill: "var(--text-secondary)" }}
              />
              <YAxis stroke="var(--text-secondary)" tick={{ fill: "var(--text-secondary)" }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "var(--card-background)", 
                  border: "1px solid var(--border-color)" 
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="tts_count" name="TTS" stroke={CHART_COLORS[0]} strokeWidth={2} />
              <Line type="monotone" dataKey="stt_count" name="STT" stroke={CHART_COLORS[1]} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Signed-in vs Guest</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={timeSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
              <XAxis 
                dataKey="date" 
                stroke="var(--text-secondary)"
                tick={{ fill: "var(--text-secondary)" }}
              />
              <YAxis stroke="var(--text-secondary)" tick={{ fill: "var(--text-secondary)" }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "var(--card-background)", 
                  border: "1px solid var(--border-color)" 
                }}
              />
              <Legend />
              <Bar dataKey="authenticated_count" name="Signed-in" fill={CHART_COLORS[0]} />
              <Bar dataKey="guest_count" name="Guest" fill={CHART_COLORS[1]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Top Voices</h3>
          <div style={{ maxHeight: "300px", overflowY: "auto" }}>
            {topVoices.map((voice, idx) => (
              <div key={idx} style={{ 
                display: "flex", 
                justifyContent: "space-between", 
                padding: "8px 0",
                borderBottom: "1px solid var(--border-color)"
              }}>
                <span>{voice.name}</span>
                <span style={{ fontWeight: "bold" }}>{voice.count}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-card">
          <h3>Top Languages</h3>
          <div style={{ maxHeight: "300px", overflowY: "auto" }}>
            {topLanguages.map((lang, idx) => (
              <div key={idx} style={{ 
                display: "flex", 
                justifyContent: "space-between", 
                padding: "8px 0",
                borderBottom: "1px solid var(--border-color)"
              }}>
                <span>{lang.name}</span>
                <span style={{ fontWeight: "bold" }}>{lang.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Events Section */}
      <div className="analytics-section">
        <div className="section-tabs" style={{ marginBottom: "16px" }}>
          <button
            className={eventsTab === "users" ? "tab-active" : "tab-button"}
            onClick={() => setEventsTab("users")}
          >
            <Users size={16} /> Users & Guests
          </button>
          <button
            className={eventsTab === "log" ? "tab-active" : "tab-button"}
            onClick={() => setEventsTab("log")}
          >
            <FileText size={16} /> Events Log
          </button>
          {selectedUser && (
            <button
              className={eventsTab === "timeline" ? "tab-active" : "tab-button"}
              onClick={() => setEventsTab("timeline")}
            >
              <Play size={16} /> Timeline
            </button>
          )}
        </div>

        {eventsTab === "users" && (
          <div className="events-container">
            <div className="events-filters" style={{ marginBottom: "16px" }}>
              <select 
                value={usersFilter} 
                onChange={(e) => setUsersFilter(e.target.value as any)}
                className="filter-select"
              >
                <option value="">All Users</option>
                <option value="authenticated">Signed-in Users</option>
                <option value="guest">Guests</option>
              </select>
            </div>

            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Type</th>
                    <th>TTS</th>
                    <th>STT</th>
                    <th>Play</th>
                    <th>Download</th>
                    <th>Characters</th>
                    <th>Minutes</th>
                    <th>Last Seen</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user, idx) => (
                    <tr key={idx}>
                      <td>
                        {user.user_type === "authenticated" 
                          ? user.user_email || user.user_name
                          : `Guest ${user.visitor_id?.substring(0, 8)}...`
                        }
                        {user.ip_address && (
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            {user.ip_address}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`status-badge ${user.user_type}`}>
                          {user.user_type === "authenticated" ? "Signed-in" : "Guest"}
                        </span>
                      </td>
                      <td>{user.tts_count}</td>
                      <td>{user.stt_count}</td>
                      <td>{user.play_count}</td>
                      <td>{user.download_count}</td>
                      <td>{user.total_characters.toLocaleString()}</td>
                      <td>{user.total_minutes}</td>
                      <td>{user.last_seen ? format(parseISO(user.last_seen), "MMM d, h:mm a") : "-"}</td>
                      <td>
                        <button
                          className="secondary-button"
                          style={{ padding: "4px 8px", fontSize: "12px" }}
                          onClick={() => {
                            setSelectedUser({
                              type: user.user_type,
                              id: user.user_type === "authenticated" ? user.user_id.toString() : user.visitor_id
                            });
                            setEventsTab("timeline");
                            setTimelinePage(0);
                          }}
                        >
                          View Timeline
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {eventsTab === "log" && (
          <div className="events-container">
            <div className="events-filters" style={{ marginBottom: "16px", display: "flex", gap: "12px", flexWrap: "wrap" }}>
              <select 
                value={eventFilters.user_type} 
                onChange={(e) => setEventFilters({...eventFilters, user_type: e.target.value})}
                className="filter-select"
              >
                <option value="">All Users</option>
                <option value="authenticated">Signed-in</option>
                <option value="guest">Guest</option>
              </select>

              <select 
                value={eventFilters.action} 
                onChange={(e) => setEventFilters({...eventFilters, action: e.target.value})}
                className="filter-select"
              >
                <option value="">All Actions</option>
                <option value="generate">Generate (TTS)</option>
                <option value="transcribe">Transcribe (STT)</option>
                <option value="play">Play</option>
                <option value="download">Download</option>
              </select>

              <select 
                value={eventFilters.status} 
                onChange={(e) => setEventFilters({...eventFilters, status: e.target.value})}
                className="filter-select"
              >
                <option value="">All Status</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="rate_limited">Rate Limited</option>
              </select>

              <input
                type="text"
                placeholder="Search..."
                value={eventFilters.search}
                onChange={(e) => setEventFilters({...eventFilters, search: e.target.value})}
                className="search-input"
                style={{ flex: 1, minWidth: "200px" }}
              />

              <button className="primary-button" onClick={exportCSV}>
                <Download size={16} /> Export CSV
              </button>
            </div>

            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Voice</th>
                    <th>Language</th>
                    <th>Details</th>
                    <th>Processing</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id}>
                      <td>{format(parseISO(event.created_at), "MMM d, h:mm a")}</td>
                      <td>
                        {event.user_email || `Guest ${event.visitor_id?.substring(0, 8)}...`}
                        {event.ip_address && (
                          <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                            {event.ip_address}
                          </div>
                        )}
                      </td>
                      <td><span className="action-badge">{event.action}</span></td>
                      <td>
                        <span className={`status-badge ${event.status}`}>
                          {event.status}
                        </span>
                      </td>
                      <td>{event.voice_name || "-"}</td>
                      <td>{event.language || "-"}</td>
                      <td style={{ fontSize: "12px" }}>
                        {event.text_length && <div>Chars: {event.text_length}</div>}
                        {event.audio_duration && <div>Duration: {event.audio_duration.toFixed(1)}s</div>}
                        {event.error_message && (
                          <div style={{ color: "var(--error-text)" }}>
                            Error: {event.error_message.substring(0, 50)}...
                          </div>
                        )}
                      </td>
                      <td>{event.processing_time_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination" style={{ marginTop: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                Showing {eventsPage * 50 + 1} - {Math.min((eventsPage + 1) * 50, eventsTotal)} of {eventsTotal}
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="secondary-button"
                  onClick={() => setEventsPage(p => Math.max(0, p - 1))}
                  disabled={eventsPage === 0}
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <button
                  className="secondary-button"
                  onClick={() => setEventsPage(p => p + 1)}
                  disabled={(eventsPage + 1) * 50 >= eventsTotal}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}

        {eventsTab === "timeline" && selectedUser && (
          <div className="events-container">
            <div style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3>
                Timeline for {selectedUser.type === "authenticated" ? "User" : "Guest"} #{selectedUser.id.substring(0, 16)}
              </h3>
              <button
                className="secondary-button"
                onClick={() => {
                  setSelectedUser(null);
                  setEventsTab("users");
                }}
              >
                Back to Users
              </button>
            </div>

            <div className="data-table">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Voice</th>
                    <th>Language</th>
                    <th>Details</th>
                    <th>Device</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.map((event) => (
                    <tr key={event.id}>
                      <td>{format(parseISO(event.created_at), "MMM d, h:mm:ss a")}</td>
                      <td><span className="action-badge">{event.action}</span></td>
                      <td>
                        <span className={`status-badge ${event.status}`}>
                          {event.status}
                        </span>
                      </td>
                      <td>{event.voice_name || "-"}</td>
                      <td>{event.language || "-"}</td>
                      <td style={{ fontSize: "12px", maxWidth: "300px" }}>
                        {event.input_text && (
                          <div style={{ marginBottom: "4px" }}>
                            {event.input_text.substring(0, 100)}
                            {event.input_text.length > 100 && "..."}
                          </div>
                        )}
                        {event.text_length && <div>Characters: {event.text_length}</div>}
                        {event.audio_duration && <div>Duration: {event.audio_duration.toFixed(1)}s</div>}
                        {event.file_size && <div>Size: {(event.file_size / 1024).toFixed(1)} KB</div>}
                        {event.error_message && (
                          <div style={{ color: "var(--error-text)", marginTop: "4px" }}>
                            {event.error_message}
                          </div>
                        )}
                      </td>
                      <td style={{ fontSize: "11px" }}>
                        {event.browser && <div>{event.browser}</div>}
                        {event.os && <div>{event.os}</div>}
                        {event.device && <div>{event.device}</div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pagination" style={{ marginTop: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                Showing {timelinePage * 50 + 1} - {Math.min((timelinePage + 1) * 50, timelineTotal)} of {timelineTotal}
              </div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="secondary-button"
                  onClick={() => setTimelinePage(p => Math.max(0, p - 1))}
                  disabled={timelinePage === 0}
                >
                  <ChevronLeft size={16} /> Previous
                </button>
                <button
                  className="secondary-button"
                  onClick={() => setTimelinePage(p => p + 1)}
                  disabled={(timelinePage + 1) * 50 >= timelineTotal}
                >
                  Next <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
