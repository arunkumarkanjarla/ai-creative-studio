
import { Video } from "lucide-react";

export default function VideoStudio() {
  return (
    <div className="content-page">
      <div className="studio-heading">
        <Video size={36} />
        <div>
          <h1>Video Studio</h1>
          <p>Transform creative ideas into AI-generated videos.</p>
        </div>
      </div>

      <div className="generation-card">
        <h3>Text to Video</h3>
        <textarea
          placeholder="Describe the video you want to create..."
          rows={5}
        />

        <button className="primary-button" disabled>
          Generate Video — Coming Soon
        </button>
      </div>
    </div>
  );
}
