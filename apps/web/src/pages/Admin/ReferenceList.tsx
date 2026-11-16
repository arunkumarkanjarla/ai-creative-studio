import { useEffect, useState } from "react";
import { FileImage, Trash2 } from "lucide-react";

import { apiRequest, MEDIA_BASE_URL } from "../../services/api";

interface PromptPack {
  prompt_id: string;
  title: string;
  description: string;
  base_prompt: string;
  created_by: string;
  created_at: string | null;
  has_reference: boolean;
  reference_url: string | null;
}

export default function ReferenceList() {
  const [packs, setPacks] = useState<PromptPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadPacks() {
    setLoading(true);
    setError("");

    try {
      const data = await apiRequest<PromptPack[]>("/images/prompts");
      setPacks(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to load references."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPacks();
  }, []);

  async function handleDelete(pack: PromptPack) {
    const ok = window.confirm(
      `Delete reference style "${pack.title}"?\n\nFolder: reference_images/${pack.prompt_id}`
    );
    if (!ok) return;

    setDeletingId(pack.prompt_id);
    setError("");
    setMessage("");

    try {
      await apiRequest(`/images/prompts/${pack.prompt_id}`, {
        method: "DELETE",
      });
      setMessage(`Deleted: ${pack.title}`);
      await loadPacks();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to delete reference."
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
            <FileImage
              size={28}
              style={{ verticalAlign: "middle", marginRight: 10 }}
            />
            Reference Styles
          </h1>
          <p>Manage uploaded reference images used for text-to-image.</p>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {message && <div className="alert">{message}</div>}

      {loading ? (
        <p>Loading...</p>
      ) : packs.length === 0 ? (
        <p className="muted-text">No reference styles found.</p>
      ) : (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Preview</th>
                <th>Title</th>
                <th>Prompt ID</th>
                <th>Created by</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {packs.map((pack) => (
                <tr key={pack.prompt_id}>
                  <td>
                    {pack.reference_url ? (
                      <img
                        className="table-thumb"
                        src={`${MEDIA_BASE_URL}${pack.reference_url}`}
                        alt={pack.title}
                      />
                    ) : (
                      "-"
                    )}
                  </td>
                  <td>
                    <strong>{pack.title}</strong>
                    <br />
                    <small className="muted-text">{pack.description}</small>
                  </td>
                  <td className="prompt-cell">{pack.prompt_id}</td>
                  <td>{pack.created_by}</td>
                  <td>
                    {pack.created_at
                      ? new Date(pack.created_at).toLocaleString()
                      : "-"}
                  </td>
                  <td>
                    <button
                      type="button"
                      className="danger-button"
                      disabled={deletingId === pack.prompt_id}
                      onClick={() => handleDelete(pack)}
                    >
                      <Trash2 size={15} />
                      {deletingId === pack.prompt_id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
