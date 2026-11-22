import { useState, useEffect } from "react";
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { format, subDays, startOfDay, endOfDay, parseISO } from "date-fns";
import { Calendar, TrendingUp, TrendingDown, Users, LogIn, Image, Download, Search, AlertTriangle, Activity } from "lucide-react";
import { apiRequest, apiFetch } from "../services/api";

const CHART_COLORS = ["var(--accent)", "var(--accent-strong)", "var(--text-secondary)", "var(--text-muted)"];
const STUDIO_COLORS = {
  image: "var(--accent)",
  audio: "var(--accent-strong)",
  video: "var(--text-secondary)",
};

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
  const [dateRange, setDateRange] = useState<"today" | "7d" | "30d" | "year" | "custom">("7d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [customStartDate, setCustomStartDate] = useState("");
  const [customEndDate, setCustomEndDate] = useState("");
  const [granularity, setGranularity] = useState<"day" | "week" | "month" | "year">("day");
  
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [changes, setChanges] = useState<Changes | null>(null);
  const [studioUsage, setStudioUsage] = useState<any[]>([]);
  const [deviceSplit, setDeviceSplit] = useState<any[]>([]);
  const [topIPs, setTopIPs] = useState<any[]>([]);
  const [topUsers, setTopUsers] = useState<any[]>([]);
  const [timeseries, setTimeseries] = useState<any>(null);
  const [hourlyData, setHourlyData] = useState<any>(null);
  const [loginHistory, setLoginHistory] = useState<any[]>([]);
  const [loginTotal, setLoginTotal] = useState(0);
  const [loginPage, setLoginPage] = useState(0);
  const [loginSearch, setLoginSearch] = useState("");
  const [loginIPFilter, setLoginIPFilter] = useState("");
  const [loginStatusFilter, setLoginStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [insights, setInsights] = useState<string[]>([]);

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
      case "year":
        start = subDays(today, 365);
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
    
    fetchAnalytics();
    fetchLoginHistory();
  }, [startDate, endDate, granularity]);
  
  useEffect(() => {
    if (!startDate || !endDate) return;
    fetchLoginHistory();
  }, [loginPage, loginSearch, loginIPFilter, loginStatusFilter]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        granularity,
      });
      
      // Get timezone offset in minutes
      const tzOffsetMinutes = -new Date().getTimezoneOffset();
      const hourlyParams = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        tz_offset_minutes: String(tzOffsetMinutes),
      });

      const [summaryData, timeseriesData, hourlyBreakdown] = await Promise.all([
        apiRequest<any>(`/analytics/summary?${params}`),
        apiRequest<any>(`/analytics/timeseries?${params}`),
        apiRequest<any>(`/analytics/hourly-breakdown?${hourlyParams}`),
      ]);

      setSummary(summaryData.summary);
      setChanges(summaryData.changes);
      setStudioUsage(summaryData.studio_usage);
      setDeviceSplit(summaryData.device_split);
      setTopIPs(summaryData.top_ips);
      setTopUsers(summaryData.top_users || []);
      setTimeseries(timeseriesData);
      setHourlyData(hourlyBreakdown);
      
      // Generate insights
      generateInsights(summaryData, hourlyBreakdown);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchLoginHistory = async () => {
    try {
      const params = new URLSearchParams({
        skip: String(loginPage * 50),
        limit: "50",
      });
      
      if (loginSearch) params.append("user_email", loginSearch);
      if (loginIPFilter) params.append("ip", loginIPFilter);
      if (loginStatusFilter) params.append("status", loginStatusFilter);
      if (startDate) params.append("start_date", startDate);
      if (endDate) params.append("end_date", endDate);
      
      const data = await apiRequest<any>(`/analytics/login-history?${params}`);
      setLoginHistory(data.items || []);
      setLoginTotal(data.total || 0);
    } catch (err) {
      console.error("Failed to fetch login history:", err);
    }
  };
  
  const generateInsights = (data: any, hourlyData: any) => {
    const newInsights: string[] = [];
    const summary = data.summary;
    
    // Peak hours insight from REAL data
    if (hourlyData && hourlyData.peak_hours && hourlyData.peak_hours.length > 0) {
      const topHours = hourlyData.peak_hours
        .map((h: any) => {
          const hour = h.hour;
          const period = hour === 0 ? "12 AM" : hour < 12 ? `${hour} AM` : hour === 12 ? "12 PM" : `${hour - 12} PM`;
          return period;
        })
        .slice(0, 3)
        .join(", ");
      newInsights.push(`Peak activity hours: ${topHours}`);
    }
    
    // Top studio from real data
    if (data.studio_usage && data.studio_usage.length > 0) {
      const topStudio = data.studio_usage.reduce((a: any, b: any) => a.count > b.count ? a : b);
      const studioName = topStudio.studio.charAt(0).toUpperCase() + topStudio.studio.slice(1);
      newInsights.push(`${studioName} Studio is most popular with ${topStudio.count} uses`);
    }
    
    // Growth trend from real data
    if (data.changes && data.changes.unique_ips > 0) {
      newInsights.push(`Growing: +${data.changes.unique_ips} new IPs vs previous period`);
    } else if (data.changes && data.changes.unique_ips < 0) {
      newInsights.push(`Declining: ${data.changes.unique_ips} fewer IPs vs previous period`);
    }
    
    // Failed login spikes from real data
    if (summary.logins_failed > 10) {
      const topIP = data.top_ips && data.top_ips.length > 0 ? data.top_ips[0] : null;
      if (topIP && topIP.visits > 20) {
        newInsights.push(`⚠️ Possible brute force: ${summary.logins_failed} failed logins, check IP ${topIP.ip}`);
      } else {
        newInsights.push(`⚠️ High failed login rate: ${summary.logins_failed} attempts`);
      }
    }
    
    setInsights(newInsights);
  };

  const downloadCSV = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      const response = await apiFetch(`/analytics/export/csv?${params}`);
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analytics_${format(new Date(), "yyyy-MM-dd")}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to download CSV:", err);
    }
  };
  
  const downloadLoginHistoryCSV = async () => {
    try {
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
      });
      if (loginSearch) params.append("user_email", loginSearch);
      if (loginIPFilter) params.append("ip", loginIPFilter);
      if (loginStatusFilter) params.append("status", loginStatusFilter);
      
      const response = await apiFetch(`/analytics/login-history/export?${params}`);
      
      if (!response.ok) throw new Error("Export failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `login_history_${format(new Date(), "yyyy-MM-dd")}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to download login history CSV:", err);
    }
  };
  
  const prepareStudioTimeseriesData = () => {
    if (!timeseries?.studio_usage) return [];
    
    const grouped: any = {};
    timeseries.studio_usage.forEach((item: any) => {
      const period = item.period;
      if (!grouped[period]) {
        grouped[period] = { period, image: 0, audio: 0, video: 0 };
      }
      grouped[period][item.studio] = item.count;
    });
    
    return Object.values(grouped);
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
  const studioTimeseriesData = prepareStudioTimeseriesData();

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
          <button className={dateRange === "custom" ? "active" : ""} onClick={() => setDateRange("custom")}>Custom</button>
        </div>
        
        <div className="granularity-controls">
          <label>Granularity:</label>
          <select value={granularity} onChange={(e) => setGranularity(e.target.value as any)}>
            <option value="day">Day</option>
            <option value="week">Week</option>
            <option value="month">Month</option>
            <option value="year">Year</option>
          </select>
        </div>
        
        <button className="secondary-button" onClick={downloadCSV}>
          <Download size={16} />
          Export Visits CSV
        </button>
      </div>
      
      {dateRange === "custom" && (
        <div className="custom-date-range">
          <div className="form-row">
            <label>Start Date:</label>
            <input
              type="date"
              value={customStartDate}
              onChange={(e) => setCustomStartDate(e.target.value)}
            />
          </div>
          <div className="form-row">
            <label>End Date:</label>
            <input
              type="date"
              value={customEndDate}
              onChange={(e) => setCustomEndDate(e.target.value)}
            />
          </div>
        </div>
      )}

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

          {insights.length > 0 && (
            <div className="insights-panel">
              <h3><Activity size={20} /> Insights</h3>
              <ul className="insights-list">
                {insights.map((insight, idx) => (
                  <li key={idx}>
                    {insight.startsWith("⚠️") && <AlertTriangle size={16} />}
                    {insight}
                  </li>
                ))}
              </ul>
            </div>
          )}

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
          
          {studioTimeseriesData.length > 0 && (
            <div className="chart-card">
              <h3>Studio Usage Over Time</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={studioTimeseriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="period" stroke="var(--text-secondary)" />
                  <YAxis stroke="var(--text-secondary)" />
                  <Tooltip contentStyle={{ background: "var(--bg-card)", border: "1px solid var(--border)" }} />
                  <Legend />
                  <Bar dataKey="image" stackId="a" fill={STUDIO_COLORS.image} name="Image" />
                  <Bar dataKey="audio" stackId="a" fill={STUDIO_COLORS.audio} name="Audio" />
                  <Bar dataKey="video" stackId="a" fill={STUDIO_COLORS.video} name="Video" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          
          {hourlyData && hourlyData.heatmap && hourlyData.heatmap.length > 0 && (
            <div className="chart-card heatmap-card">
              <h3>Activity Heatmap (Weekday × Hour)</h3>
              <div className="heatmap-container">
                <div className="heatmap-grid">
                  <div className="heatmap-y-labels">
                    <div></div>
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                      <div key={day} className="heatmap-label">{day}</div>
                    ))}
                  </div>
                  <div className="heatmap-chart">
                    <div className="heatmap-x-labels">
                      {Array.from({ length: 24 }, (_, i) => (
                        <div key={i} className="heatmap-label">{i}</div>
                      ))}
                    </div>
                    <div className="heatmap-cells">
                      {Array.from({ length: 7 }, (_, weekday) => (
                        <div key={weekday} className="heatmap-row">
                          {Array.from({ length: 24 }, (_, hour) => {
                            const cell = hourlyData.heatmap.find(
                              (d: any) => d.weekday === weekday && d.hour === hour
                            );
                            const count = cell ? cell.count : 0;
                            const maxCount = Math.max(...hourlyData.heatmap.map((d: any) => d.count));
                            const intensity = maxCount > 0 ? count / maxCount : 0;
                            return (
                              <div
                                key={hour}
                                className="heatmap-cell"
                                style={{
                                  backgroundColor: `rgba(var(--accent-rgb, 59, 130, 246), ${intensity})`,
                                  opacity: count === 0 ? 0.1 : 1,
                                }}
                                title={`${["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][weekday]} ${hour}:00 - ${count} visits`}
                              />
                            );
                          })}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
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

          <div className="charts-row">
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
                    {topIPs.slice(0, 5).map((item) => (
                      <tr key={item.ip}>
                        <td>{item.ip}</td>
                        <td>{item.visits}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {topUsers.length > 0 && (
              <div className="table-card">
                <h3>Top Users</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Email</th>
                      <th>Visits</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topUsers.slice(0, 5).map((item, idx) => (
                      <tr key={idx}>
                        <td>{item.email}</td>
                        <td>{item.visits}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="table-card login-history-card">
            <div className="table-header">
              <h3>Login History</h3>
              <button className="secondary-button" onClick={downloadLoginHistoryCSV}>
                <Download size={16} />
                Export CSV
              </button>
            </div>
            
            <div className="login-filters">
              <div className="filter-group">
                <Search size={16} />
                <input
                  type="text"
                  placeholder="Search by email..."
                  value={loginSearch}
                  onChange={(e) => { setLoginSearch(e.target.value); setLoginPage(0); }}
                />
              </div>
              <div className="filter-group">
                <input
                  type="text"
                  placeholder="Filter by IP..."
                  value={loginIPFilter}
                  onChange={(e) => { setLoginIPFilter(e.target.value); setLoginPage(0); }}
                />
              </div>
              <div className="filter-group">
                <select
                  value={loginStatusFilter}
                  onChange={(e) => { setLoginStatusFilter(e.target.value); setLoginPage(0); }}
                >
                  <option value="">All Statuses</option>
                  <option value="success">Success</option>
                  <option value="failed">Failed</option>
                  <option value="logged_out">Logged Out</option>
                  <option value="expired">Expired</option>
                </select>
              </div>
            </div>
            
            {loginHistory.length > 0 ? (
              <>
                <div className="table-responsive">
                  <table>
                    <thead>
                      <tr>
                        <th>User</th>
                        <th>IP Address</th>
                        <th>Browser</th>
                        <th>Device</th>
                        <th>Time</th>
                        <th>Status</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {loginHistory.map((session) => (
                        <tr key={session.id}>
                          <td>{session.user_email || session.username_attempted || "N/A"}</td>
                          <td>{session.ip}</td>
                          <td>{session.browser || "N/A"}</td>
                          <td>{session.device_type || "N/A"}</td>
                          <td>{format(new Date(session.login_at), "MMM d, yyyy HH:mm")}</td>
                          <td>
                            <span className={`status-badge status-${session.status}`}>
                              {session.status}
                            </span>
                          </td>
                          <td>{session.failure_reason || "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                
                <div className="pagination">
                  <button
                    disabled={loginPage === 0}
                    onClick={() => setLoginPage((p) => p - 1)}
                    className="secondary-button"
                  >
                    Previous
                  </button>
                  <span>Page {loginPage + 1} of {Math.ceil(loginTotal / 50)}</span>
                  <button
                    disabled={(loginPage + 1) * 50 >= loginTotal}
                    onClick={() => setLoginPage((p) => p + 1)}
                    className="secondary-button"
                  >
                    Next
                  </button>
                </div>
              </>
            ) : (
              <p className="empty-message">No login history found for this period.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
