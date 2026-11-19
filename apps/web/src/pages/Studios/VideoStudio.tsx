
import { useState } from "react";
import { Video } from "lucide-react";
import VoiceInput from "../../components/VoiceInput";

export default function VideoStudio() {
  const [prompt, setPrompt] = useState("");

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
        <div className="prompt-with-voice">
          <textarea
            placeholder="Describe the video you want to create..."
            rows={5}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <VoiceInput
            onTranscript={(text) => {
              setPrompt((prev) => (prev ? `${prev} ${text}` : text));
            }}
            language="en-IN"
          />
        </div>

        <button className="primary-button" disabled>
          Generate Video — Coming Soon
        </button>
      </div>
    </div>
  );
}
