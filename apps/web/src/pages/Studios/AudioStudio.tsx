import { useState, useEffect, useRef } from "react";
import { AudioLines, Play, Pause, Download, Trash2, Upload, FileText, Languages, Volume2, Gauge, Settings } from "lucide-react";
import VoiceInput from "../../components/VoiceInput";
import { apiRequest } from "../../services/api";

type Mode = "tts" | "stt" | "history";

interface Voice {
  id: number;
  name: string;
  voice_id: string;
  gender: string;
  age_group: string;
  language: string;
  locale: string;
  is_custom: boolean;
  pitch?: number;
  rate?: number;
  volume?: number;
}

interface TTSGeneration {
  id: number;
  text: string;
  full_text: string;
  voice_name: string;
  duration: number;
  file_size: number;
  status: string;
  created_at: string;
  download_url: string;
}

interface Transcription {
  id: number;
  text: string;
  full_text: string;
  language: string;
  duration: number;
  status: string;
  created_at: string;
  txt_url: string;
  srt_url: string;
}

export default function AudioStudio() {
  const [mode, setMode] = useState<Mode>("tts");
  
  // TTS State
  const [ttsText, setTtsText] = useState("");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<Voice | null>(null);
  const [pitch, setPitch] = useState(1.0);
  const [rate, setRate] = useState(1.0);
  const [volume, setVolume] = useState(1.0);
  const [outputFormat, setOutputFormat] = useState("mp3");
  const [generating, setGenerating] = useState(false);
  const [generatedAudio, setGeneratedAudio] = useState<string | null>(null);
  
  // Voice filters
  const [genderFilter, setGenderFilter] = useState<string>("");
  const [ageFilter, setAgeFilter] = useState<string>("");
  const [langFilter, setLangFilter] = useState<string>("");
  
  // STT State
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [transcriptResult, setTranscriptResult] = useState<any>(null);
  
  // History State
  const [ttsHistory, setTtsHistory] = useState<TTSGeneration[]>([]);
  const [sttHistory, setSttHistory] = useState<Transcription[]>([]);
  const [historyType, setHistoryType] = useState<"tts" | "stt">("tts");
  
  // Audio player
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string>("");

  useEffect(() => {
    loadVoices();
    if (mode === "history") {
      loadHistory();
    }
  }, [mode]);

  const loadVoices = async () => {
    try {
      const params = new URLSearchParams();
      if (genderFilter) params.append("gender", genderFilter);
      if (ageFilter) params.append("age_group", ageFilter);
      if (langFilter) params.append("language", langFilter);
      
      const data = await apiRequest<any>(`/audio/voices?${params}`);
      setVoices(data.voices);
      if (data.voices.length > 0 && !selectedVoice) {
        setSelectedVoice(data.voices[0]);
      }
    } catch (error) {
      console.error("Failed to load voices:", error);
    }
  };

  useEffect(() => {
    loadVoices();
  }, [genderFilter, ageFilter, langFilter]);

  const handleGenerateTTS = async () => {
    if (!ttsText.trim() || !selectedVoice) return;
    
    setGenerating(true);
    setGeneratedAudio(null);
    
    try {
      const formData = new FormData();
      formData.append("text", ttsText);
      formData.append("voice_id", selectedVoice.voice_id);
      formData.append("pitch", pitch.toString());
      formData.append("rate", rate.toString());
      formData.append("volume", volume.toString());
      formData.append("output_format", outputFormat);
      
      const result = await apiRequest<any>("/audio/generate", {
        method: "POST",
        body: formData
      });
      
      setGeneratedAudio(result.file_url);
      alert("Audio generated successfully!");
    } catch (error: any) {
      alert(`Generation failed: ${error.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleTranscribe = async () => {
    if (!uploadedFile) return;
    
    setTranscribing(true);
    setTranscriptResult(null);
    
    try {
      const formData = new FormData();
      formData.append("audio", uploadedFile);
      
      const result = await apiRequest<any>("/audio/transcribe", {
        method: "POST",
        body: formData
      });
      
      setTranscriptResult(result);
    } catch (error: any) {
      alert(`Transcription failed: ${error.message}`);
    } finally {
      setTranscribing(false);
    }
  };

  const loadHistory = async () => {
    try {
      if (historyType === "tts") {
        const data = await apiRequest<any>("/audio/history/tts");
        setTtsHistory(data.items);
      } else {
        const data = await apiRequest<any>("/audio/history/transcriptions");
        setSttHistory(data.items);
      }
    } catch (error) {
      console.error("Failed to load history:", error);
    }
  };

  useEffect(() => {
    if (mode === "history") {
      loadHistory();
    }
  }, [historyType]);

  const playAudio = (url: string) => {
    if (audioRef.current) {
      if (currentAudioUrl === url && isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.src = url.startsWith("http") ? url : `http://localhost:8000${url}`;
        audioRef.current.play();
        setCurrentAudioUrl(url);
        setIsPlaying(true);
      }
    }
  };

  const deleteItem = async (id: number, type: "tts" | "stt") => {
    if (!confirm("Delete this item?")) return;
    
    try {
      if (type === "tts") {
        await apiRequest(`/audio/history/tts/${id}`, { method: "DELETE" });
      } else {
        await apiRequest(`/audio/history/transcriptions/${id}`, { method: "DELETE" });
      }
      loadHistory();
    } catch (error: any) {
      alert(`Delete failed: ${error.message}`);
    }
  };

  const filteredVoices = voices;
  const languages = Array.from(new Set(voices.map(v => v.language)));

  return (
    <div className="content-page">
      <div className="studio-heading">
        <AudioLines size={36} />
        <div>
          <h1>Audio Studio</h1>
          <p>Text-to-speech, speech-to-text and voice customization</p>
        </div>
      </div>

      <div className="mode-tabs" style={{ marginBottom: "24px" }}>
        <button 
          className={mode === "tts" ? "tab-active" : "tab-button"}
          onClick={() => setMode("tts")}
        >
          Text to Speech
        </button>
        <button 
          className={mode === "stt" ? "tab-active" : "tab-button"}
          onClick={() => setMode("stt")}
        >
          Speech to Text
        </button>
        <button 
          className={mode === "history" ? "tab-active" : "tab-button"}
          onClick={() => setMode("history")}
        >
          History
        </button>
      </div>

      {mode === "tts" && (
        <div className="tts-container">
          <div className="generation-card">
            <h3>Generate Speech</h3>
            
            <div className="prompt-with-voice">
              <textarea
                placeholder="Enter text to convert to speech (up to 5000 characters)..."
                rows={6}
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                maxLength={5000}
              />
              <VoiceInput
                onTranscript={(text) => {
                  setTtsText((prev) => (prev ? `${prev} ${text}` : text));
                }}
                language="en-IN"
              />
            </div>
            
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
              {ttsText.length} / 5000 characters
            </div>

            <div className="audio-controls">
              <div className="control-group">
                <label><Gauge size={16} /> Speed: {rate.toFixed(2)}x</label>
                <input 
                  type="range" 
                  min="0.5" 
                  max="2.0" 
                  step="0.1" 
                  value={rate}
                  onChange={(e) => setRate(parseFloat(e.target.value))}
                />
              </div>
              
              <div className="control-group">
                <label><Settings size={16} /> Pitch: {pitch.toFixed(2)}x</label>
                <input 
                  type="range" 
                  min="0.5" 
                  max="1.5" 
                  step="0.1" 
                  value={pitch}
                  onChange={(e) => setPitch(parseFloat(e.target.value))}
                />
              </div>
              
              <div className="control-group">
                <label><Volume2 size={16} /> Volume: {volume.toFixed(2)}x</label>
                <input 
                  type="range" 
                  min="0.5" 
                  max="1.5" 
                  step="0.1" 
                  value={volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value))}
                />
              </div>
              
              <div className="control-group">
                <label>Format:</label>
                <select value={outputFormat} onChange={(e) => setOutputFormat(e.target.value)}>
                  <option value="mp3">MP3</option>
                  <option value="wav">WAV</option>
                </select>
              </div>
            </div>

            <button 
              className="primary-button" 
              onClick={handleGenerateTTS}
              disabled={generating || !ttsText.trim() || !selectedVoice}
            >
              {generating ? "Generating..." : "Generate Speech"}
            </button>
            
            {generatedAudio && (
              <div className="generated-result">
                <p style={{ color: "var(--success-text)" }}>✓ Audio generated successfully!</p>
                <div style={{ display: "flex", gap: "12px", marginTop: "12px" }}>
                  <button 
                    className="secondary-button"
                    onClick={() => playAudio(generatedAudio)}
                  >
                    <Play size={16} /> Play
                  </button>
                  <a 
                    href={`http://localhost:8000${generatedAudio}`}
                    download
                    className="secondary-button"
                  >
                    <Download size={16} /> Download
                  </a>
                </div>
              </div>
            )}
          </div>

          <div className="generation-card">
            <h3>Voice Library</h3>
            
            <div className="voice-filters">
              <div className="filter-group">
                <label>Gender:</label>
                <select value={genderFilter} onChange={(e) => setGenderFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="child">Child</option>
                </select>
              </div>
              
              <div className="filter-group">
                <label>Age:</label>
                <select value={ageFilter} onChange={(e) => setAgeFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="adult">Adult</option>
                  <option value="child">Child</option>
                </select>
              </div>
              
              <div className="filter-group">
                <label><Languages size={16} /> Language:</label>
                <select value={langFilter} onChange={(e) => setLangFilter(e.target.value)}>
                  <option value="">All Languages</option>
                  {languages.map(lang => (
                    <option key={lang} value={lang}>{lang}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="voice-list">
              {filteredVoices.map((voice) => (
                <div 
                  key={voice.id}
                  className={`voice-item ${selectedVoice?.id === voice.id ? "selected" : ""}`}
                  onClick={() => setSelectedVoice(voice)}
                >
                  <div className="voice-info">
                    <div className="voice-name">{voice.name}</div>
                    <div className="voice-tags">
                      <span className="tag">{voice.gender}</span>
                      <span className="tag">{voice.language}</span>
                      {voice.is_custom && <span className="tag custom">Custom</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {mode === "stt" && (
        <div className="generation-card">
          <h3>Transcribe Audio</h3>
          
          <div className="upload-area">
            <input
              type="file"
              accept="audio/*"
              onChange={(e) => setUploadedFile(e.target.files?.[0] || null)}
              style={{ marginBottom: "16px" }}
            />
            {uploadedFile && (
              <p>Selected: {uploadedFile.name}</p>
            )}
          </div>

          <button 
            className="primary-button" 
            onClick={handleTranscribe}
            disabled={transcribing || !uploadedFile}
          >
            {transcribing ? "Transcribing..." : <><Upload size={16} /> Transcribe Audio</>}
          </button>

          {transcriptResult && (
            <div className="transcript-result">
              <h4>Transcript ({transcriptResult.language})</h4>
              <div className="transcript-text">
                {transcriptResult.text}
              </div>
              <div style={{ display: "flex", gap: "12px", marginTop: "16px" }}>
                <a 
                  href={`http://localhost:8000${transcriptResult.txt_url}`}
                  download
                  className="secondary-button"
                >
                  <FileText size={16} /> Download TXT
                </a>
                <a 
                  href={`http://localhost:8000${transcriptResult.srt_url}`}
                  download
                  className="secondary-button"
                >
                  <FileText size={16} /> Download SRT
                </a>
              </div>
            </div>
          )}
        </div>
      )}

      {mode === "history" && (
        <div>
          <div className="history-tabs" style={{ marginBottom: "16px" }}>
            <button 
              className={historyType === "tts" ? "secondary-button" : "tertiary-button"}
              onClick={() => setHistoryType("tts")}
            >
              TTS History
            </button>
            <button 
              className={historyType === "stt" ? "secondary-button" : "tertiary-button"}
              onClick={() => setHistoryType("stt")}
            >
              Transcriptions
            </button>
          </div>

          {historyType === "tts" ? (
            <div className="history-list">
              {ttsHistory.length === 0 ? (
                <p className="empty-message">No TTS generations yet</p>
              ) : (
                ttsHistory.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-info">
                      <div className="history-text">{item.text}</div>
                      <div className="history-meta">
                        {item.voice_name} • {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="history-actions">
                      <button 
                        className="icon-button"
                        onClick={() => playAudio(item.download_url)}
                        title="Play"
                      >
                        {currentAudioUrl === item.download_url && isPlaying ? <Pause size={18} /> : <Play size={18} />}
                      </button>
                      <a 
                        href={`http://localhost:8000${item.download_url}`}
                        download
                        className="icon-button"
                        title="Download"
                      >
                        <Download size={18} />
                      </a>
                      <button 
                        className="icon-button"
                        onClick={() => deleteItem(item.id, "tts")}
                        title="Delete"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="history-list">
              {sttHistory.length === 0 ? (
                <p className="empty-message">No transcriptions yet</p>
              ) : (
                sttHistory.map((item) => (
                  <div key={item.id} className="history-item">
                    <div className="history-info">
                      <div className="history-text">{item.text}</div>
                      <div className="history-meta">
                        {item.language} • {new Date(item.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="history-actions">
                      <a 
                        href={`http://localhost:8000${item.txt_url}`}
                        download
                        className="icon-button"
                        title="Download TXT"
                      >
                        <FileText size={18} />
                      </a>
                      <button 
                        className="icon-button"
                        onClick={() => deleteItem(item.id, "stt")}
                        title="Delete"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      <audio 
        ref={audioRef}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
      />
    </div>
  );
}
