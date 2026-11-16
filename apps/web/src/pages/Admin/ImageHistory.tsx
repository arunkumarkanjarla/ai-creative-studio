import { useEffect, useState } from "react";
import { Images, Trash2 } from "lucide-react";

import { apiRequest, mediaUrl } from "../../services/api";

interface HistoryItem {
  id: number;
  user_id: number | null;
  user_name: string | null;
  user_email: string | null;
  visitor_id: string | null;
  prompt: string;
  status: string;
  image_url: string | null;
  generation_time_seconds: number | null;
  created_at: string;
  error_message: string | null;
}

interface HistoryResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: HistoryItem[];
}

export default function ImageHistory() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);

  async function loadPage(nextPage: number) {
    setLoading(true);
    setError("");

    try {
      const result = await apiRequest<HistoryResponse>(
        `/images/admin/history?page=${nextPage}&page_size=20`
      );
      setData(result);
      setPage(nextPage);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load image history."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPage(1);
  }, []);

  async function handleDelete(item: HistoryItem) {
    const ok = window.confirm(
      `Delete this generated image?\n\n${item.prompt.slice(0, 120)}`
    );
    if (!ok) return;

    setDeletingId(item.id);
    setError("");
    setMessage("");

    try {
      await apiRequest(`/images/${item.id}`, { method: "DELETE" });
      setMessage("Generated image deleted.");
      await loadPage(page);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to delete image."
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="content-page">
      <div className="page-heading">
        <div>
          <h1>
            <Images size={28} style={{ verticalAlign: "middle", marginRight: 10 }} />
            Generated Images
          </h1>
          <p>All text-to-image results from users and guests.</p>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {message && <div className="alert">{message}</div>}

      {loading && !data ? (
        <p>Loading...</p>
      ) : (
        <>
          <p className="muted-text">Total: {data?.total ?? 0}</p>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Preview</th>
                  <th>Prompt</th>
                  <th>Created by</th>
                  <th>Status</th>
                  <th>Time</th>
                  <th>Created</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {(data?.items ?? []).map((item) => (
                  <tr key={item.id}>
                    <td>
                      {item.image_url ? (
                        <img
                          className="table-thumb"
                          src={mediaUrl(item.image_url) || ""}
                          alt={item.prompt}
                        />
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="prompt-cell">{item.prompt}</td>
                    <td>
                      {item.user_name || "Guest"}
                      {item.user_email ? (
                        <>
                          <br />
                          <small>{item.user_email}</small>
                        </>
                      ) : null}
                    </td>
                    <td>{item.status}</td>
                    <td>
                      {item.generation_time_seconds != null
                        ? `${item.generation_time_seconds}s`
                        : "-"}
                    </td>
                    <td>{new Date(item.created_at).toLocaleString()}</td>
                    <td>
                      <button
                        type="button"
                        className="danger-button"
                        disabled={deletingId === item.id}
                        onClick={() => handleDelete(item)}
                      >
                        <Trash2 size={15} />
                        {deletingId === item.id ? "Deleting..." : "Delete"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data && data.total_pages > 1 && (
            <div className="form-actions">
              <button
                className="secondary-button"
                disabled={page <= 1 || loading}
                onClick={() => loadPage(page - 1)}
              >
                Previous
              </button>
              <span>
                Page {page} of {data.total_pages}
              </span>
              <button
                className="secondary-button"
                disabled={page >= data.total_pages || loading}
                onClick={() => loadPage(page + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
