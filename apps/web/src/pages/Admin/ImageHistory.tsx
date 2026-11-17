import { useEffect, useState, type FormEvent } from "react";
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

type StatusFilter = "" | "pending" | "processing" | "completed" | "failed";
type CreatedByFilter = "all" | "guest" | "user";

export default function ImageHistory() {
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [promptFilter, setPromptFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [createdByFilter, setCreatedByFilter] = useState<CreatedByFilter>("all");
  const [appliedPrompt, setAppliedPrompt] = useState("");
  const [appliedStatus, setAppliedStatus] = useState<StatusFilter>("");
  const [appliedCreatedBy, setAppliedCreatedBy] =
    useState<CreatedByFilter>("all");

  async function loadPage(
    nextPage: number,
    opts?: {
      prompt?: string;
      status?: StatusFilter;
      createdBy?: CreatedByFilter;
      size?: number;
    }
  ) {
    setLoading(true);
    setError("");

    const prompt = opts?.prompt ?? appliedPrompt;
    const status = opts?.status ?? appliedStatus;
    const createdBy = opts?.createdBy ?? appliedCreatedBy;
    const size = opts?.size ?? pageSize;

    const params = new URLSearchParams({
      page: String(nextPage),
      page_size: String(size),
      created_by: createdBy,
    });
    if (prompt.trim()) params.set("prompt", prompt.trim());
    if (status) params.set("status", status);

    try {
      const result = await apiRequest<HistoryResponse>(
        `/images/admin/history?${params.toString()}`
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

  function handleApplyFilters(event: FormEvent) {
    event.preventDefault();
    setAppliedPrompt(promptFilter);
    setAppliedStatus(statusFilter);
    setAppliedCreatedBy(createdByFilter);
    loadPage(1, {
      prompt: promptFilter,
      status: statusFilter,
      createdBy: createdByFilter,
    });
  }

  function handleClearFilters() {
    setPromptFilter("");
    setStatusFilter("");
    setCreatedByFilter("all");
    setAppliedPrompt("");
    setAppliedStatus("");
    setAppliedCreatedBy("all");
    loadPage(1, {
      prompt: "",
      status: "",
      createdBy: "all",
    });
  }

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

      <form className="admin-filters" onSubmit={handleApplyFilters}>
        <label>
          Search prompt
          <input
            type="text"
            placeholder="Search by prompt text..."
            value={promptFilter}
            onChange={(e) => setPromptFilter(e.target.value)}
          />
        </label>

        <label>
          Status
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          >
            <option value="">All</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="failed">Failed</option>
          </select>
        </label>

        <label>
          Created by
          <select
            value={createdByFilter}
            onChange={(e) =>
              setCreatedByFilter(e.target.value as CreatedByFilter)
            }
          >
            <option value="all">All</option>
            <option value="guest">Guests</option>
            <option value="user">Users</option>
          </select>
        </label>

        <label>
          Per page
          <select
            value={pageSize}
            onChange={(e) => {
              const size = Number(e.target.value);
              setPageSize(size);
              loadPage(1, { size });
            }}
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </label>

        <div className="admin-filter-actions">
          <button className="primary-button" type="submit" disabled={loading}>
            Apply
          </button>
          <button
            className="secondary-button"
            type="button"
            disabled={loading}
            onClick={handleClearFilters}
          >
            Clear
          </button>
        </div>
      </form>

      {loading && !data ? (
        <p>Loading...</p>
      ) : (
        <>
          <p className="muted-text">
            Showing {data?.items.length ?? 0} of {data?.total ?? 0}
            {loading ? " (updating...)" : ""}
          </p>

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
                {(data?.items ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={7}>No images match these filters.</td>
                  </tr>
                ) : (
                  (data?.items ?? []).map((item) => (
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
                  ))
                )}
              </tbody>
            </table>
          </div>

          {data && data.total_pages > 0 && (
            <div className="pagination-bar">
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
