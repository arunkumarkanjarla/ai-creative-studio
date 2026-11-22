import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { apiRequest } from "../../../services/api";

const COLORS = ["var(--accent)", "var(--accent-strong)", "var(--text-secondary)", "var(--text-muted)"];

export default function AdminVideoOverview() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        setData(await apiRequest<any>(`/admin/video/overview?days=${days}`));
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    })();
  }, [days]);

  if (loading && !data) return <div className="content-page">Loading…</div>;
  const summary = data?.summary || {};

  return (
    <div className="content-page">
      <div className="studio-heading">
        <div>
          <h1>Video Overview</h1>
          <p>KPIs and charts for Video Studio generation.</p>
        </div>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="admin-kpi-row">
        <div className="admin-kpi"><span>Total</span><strong>{summary.total_videos ?? 0}</strong></div>
        <div className="admin-kpi"><span>Today</span><strong>{summary.today_count ?? 0}</strong></div>
        <div className="admin-kpi"><span>Completed</span><strong>{summary.completed ?? 0}</strong></div>
        <div className="admin-kpi"><span>Failed</span><strong>{summary.failed ?? 0}</strong></div>
        <div className="admin-kpi"><span>Queue</span><strong>{summary.queued_or_processing ?? 0}</strong></div>
        <div className="admin-kpi"><span>Avg render</span><strong>{summary.avg_render_seconds ?? 0}s</strong></div>
      </div>

      <div className="admin-chart-grid">
        <div className="generation-card">
          <h3>Videos per day</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data?.videos_per_day || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke={COLORS[0]} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="generation-card">
          <h3>By category</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data?.by_category || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill={COLORS[1]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="generation-card">
          <h3>By engine</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data?.by_engine || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="engine" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill={COLORS[2]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="generation-card">
          <h3>Success / failure</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data?.success_failure || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="status" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill={COLORS[0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="generation-card">
        <h3>Top users</h3>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Videos</th>
            </tr>
          </thead>
          <tbody>
            {(data?.top_users || []).map((u: any) => (
              <tr key={u.user_id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>{u.count}</td>
              </tr>
            ))}
            {(data?.top_users || []).length === 0 && (
              <tr><td colSpan={3}>No data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
