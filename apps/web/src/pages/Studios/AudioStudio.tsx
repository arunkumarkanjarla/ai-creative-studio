
import { AudioLines } from "lucide-react";

export default function AudioStudio() {
  return (
    <div className="content-page">
      <div className="studio-heading">
        <AudioLines size={36} />
        <div>
          <h1>Audio Studio</h1>
          <p>Generate speech, sounds and music using local AI models.</p>
        </div>
      </div>

      <div className="generation-card">
        <h3>Text to Audio</h3>
        <textarea
          placeholder="Enter the text or audio description..."
          rows={5}
        />

        <button className="primary-button" disabled>
          Generate Audio — Coming Soon
        </button>
      </div>
    </div>
  );
}
