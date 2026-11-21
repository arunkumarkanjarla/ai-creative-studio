import { useState, useEffect } from "react";
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { format, subDays, startOfDay, endOfDay } from "date-fns";
import { Calendar, TrendingUp, TrendingDown, Users, LogIn, Image, Download } from "lucide-react";
import { apiRequest } from "../services/api";

const CHART_COLORS = ["var(--accent)", "var(--accent-strong)", "var(--text-secondary)", "var(--text-muted)"];

interface AnalyticsSummary {
  unique_ips: number;
  unique_users: number;
  unique_visitors: number;
  total_visits: number;
  logins_success: number;
  logins_failed: number;
  generations: number;
}

interface Changes {
  unique_ips: number;
  unique_users: number;
  logins_success: number;
}

export default function AnalyticsReports() {
  const [dateRange, setDateRange] = useState<"today" | "7d" | "30d" | "year">("7d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [granularity, setGranularity] = useState<"day" | "week" | "month" | "year">("day");
  
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [changes, setChanges] = useState<Changes | null>(null);
  const [studioUsage, setStudioUsage] = useState<any[]>([]);
  const [deviceSplit, setDeviceSplit] = useState<any[]>([]);
  const [topIPs, setTopIPs] = useState<any[]>([]);
  const [timeseries, setTimeseries] = useState<any>(null);
  const [loginHistory, setLoginHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const today = new Date();
    let start: Date, end: Date;

    switch (dateRange) {
      case "today":
        start = startOfDay(today);
        end = endOfDay(today);
        setGranularity("day");
        break;
      case "7d":
        start = subDays(today, 7);
        end = today;
        setGranularity("day");
        break;
      case "30d":
        start = subDays(today, 30);
        end = today;
        setGranularity("day");
        break;
      case "year":
        start = subDays(today, 365);
        end = today;
        setGranularity("month");
        break;
      default:
        return;
    }

    setStartDate(format(start, "yyyy-MM-dd'T'HH:mm:ss"));
    setEndDate(format(end, "yyyy-MM-dd'T'HH:mm:ss"));
  }, [dateRange]);

  useEffect(() => {
    if (!startDate || !endDate) return;
    
    fetchAnalytics();
  }, [startDate, endDate, granularity]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        granularity,
      });

      const [summaryData, timeseriesData, loginHistoryData] = await Promise.all([
        apiRequest<any>(`/analytics/summary?${params}`),
        apiRequest<any>(`/analytics/timeseries?${params}`),
        apiRequest<any>(`/analytics/login-history?limit=10`),
      ]);

      setSummary(summaryData.summary);
      setChanges(summaryData.changes);
      setStudioUsage(summaryData.studio_usage);
      setDeviceSplit(summaryData.device_split);
      setTopIPs(summaryData.top_ips);
      setTimeseries(timeseriesData);
      setLoginHistory(loginHistoryData.items || []);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      window.open(`/api/v1/analytics/export/csv?${params}`, "_blank");
    } catch (err) {
      console.error("Failed to download CSV:", err);
    }
  };

  const renderChange = (value: number) => {
    if (value === 0) return null;
    return (
      <span className={value > 0 ? "trend-positive" : "trend-negative"}>
        {value > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
        {Math.abs(value)}
      </span>
    );
  };

  if (loading && !summary) {
    return (
      <div className="content-page">
        <h1>Analytics Reports</h1>
        <p>Loading analytics data...</p>
      </div>
    );
  }

  const isEmpty = !summary || (summary.total_visits === 0 && summary.logins_success === 0);

  return (
    <div className="content-page analytics-page">
      <div className="page-header">
        <h1>Analytics Reports</h1>
        <p>Usage analytics and login history</p>
      </div>

      <div className="analytics-controls">
        <div className="date-range-presets">
          <button className={dateRange === "today" ? "active" : ""} onClick={() => setDateRange("today")}>Today</button>
          <button className={dateRange === "7d" ? "active" : ""} onClick={() => setDateRange("7d")}>7 Days</button>
          <button className={dateRange === "30d" ? "active" : ""} onClick={() => setDateRange("30d")}>30 Days</button>
          <button className={dateRange === "year" ? "active" : ""} onClick={() => setDateRange("year")}>This Year</button>
        </div>
        <button className="secondary-button" onClick={downloadCSV}>
          <Download size={16} />
          Export CSV
        </button>
      </div>

      {isEmpty ? (
        <div className="empty-state">
          <Calendar size={48} />
          <h3>No Data Yet</h3>
          <p>Analytics data will appear here once users start visiting and using the platform.</p>
        </div>
      ) : (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-header">
                <Users size={20} />
                <span>Unique IPs</span>
              </div>
              <div className="kpi-value">{summary?.unique_ips || 0}</div>
              {renderChange(changes?.unique_ips || 0)}
            </div>
            <div className="kpi-card">
              <div className="kpi-header">
                <Users size={20} />
                <span>Logged-in Users</span>
              </div>
              <div className="kpi-value">{summary?.unique_users || 0}</div>
              {renderChange(changes?.unique_users || 0)}
            </div>
            <div className="kpi-card">
              <div className="kpi-header">
                <Users size={20} />
                <span>Guest Visitors</span>
              </div>
              <div className="kpi-value">{(summary?.unique_visitors || 0) - (summary?.unique_users || 0)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-header">
                <LogIn size={20} />
                <span>Successful Logins</span>
              </div>
              <div className="kpi-value">{summary?.logins_success || 0}</div>
              {renderChange(changes?.logins_success || 0)}
            </div>
            <div className="kpi-card">
              <div className="kpi-header">
                <LogIn size={20} />
                <span>Failed Logins</span>
              </div>
              <div className="kpi-value">{summary?.logins_failed || 0}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-header">
                <Image size={20} />
                <span>Generations</span>
              </div>
              <div className="kpi-value">{summary?.generations || 0}</div>
            </div>
          </div>

          {timeseries?.visitors && timeseries.visitors.length > 0 && (
            <div className="chart-card">
              <h3>Visitors Over Time</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={timeseries.visitors}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="period" stroke="var(--text-secondary)" />
                  <YAxis stroke="var(--text-secondary)" />
                  <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)" }} />
                  <Legend />
                  <Line type="monotone" dataKey="logged_in" stroke="var(--accent)" name="Logged In" />
                  <Line type="monotone" dataKey="guest" stroke="var(--text-muted)" name="Guest" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="charts-row">
            {studioUsage.length > 0 && (
              <div className="chart-card">
                <h3>Studio Usage</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={studioUsage} dataKey="count" nameKey="studio" cx="50%" cy="50%" label>
                      {studioUsage.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}

            {deviceSplit.length > 0 && (
              <div className="chart-card">
                <h3>Device Types</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie data={deviceSplit} dataKey="count" nameKey="device" cx="50%" cy="50%" label>
                      {deviceSplit.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {topIPs.length > 0 && (
            <div className="table-card">
              <h3>Top IP Addresses</h3>
              <table>
                <thead>
                  <tr>
                    <th>IP Address</th>
                    <th>Visits</th>
                  </tr>
                </thead>
                <tbody>
                  {topIPs.map((item) => (
                    <tr key={item.ip}>
                      <td>{item.ip}</td>
                      <td>{item.visits}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {loginHistory.length > 0 && (
            <div className="table-card">
              <h3>Recent Login Sessions</h3>
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>IP Address</th>
                    <th>Device</th>
                    <th>Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {loginHistory.map((session) => (
                    <tr key={session.id}>
                      <td>{session.user_email || session.username_attempted || "N/A"}</td>
                      <td>{session.ip}</td>
                      <td>{session.device_type}</td>
                      <td>{format(new Date(session.login_at), "MMM d, HH:mm")}</td>
                      <td>
                        <span className={`status-badge status-${session.status}`}>
                          {session.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
