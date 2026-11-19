
import { useState } from "react";
import { AudioLines } from "lucide-react";
import VoiceInput from "../../components/VoiceInput";

export default function AudioStudio() {
  const [prompt, setPrompt] = useState("");

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
        <div className="prompt-with-voice">
          <textarea
            placeholder="Enter the text or audio description..."
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
          Generate Audio — Coming Soon
        </button>
      </div>
    </div>
  );
}
