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
  region?: string;
  country?: string;
  accent?: string;
  voice_type?: string;
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
  const [regionFilter, setRegionFilter] = useState<string>("");
  const [countryFilter, setCountryFilter] = useState<string>("");
  const [voiceTypeFilter, setVoiceTypeFilter] = useState<string>("");
  const [searchFilter, setSearchFilter] = useState<string>("");
  
  // Preview state
  const [playingPreview, setPlayingPreview] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState<string | null>(null);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);
  
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
  
  // Blob URL cache for authenticated media
  const blobUrlCache = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    loadVoices();
    if (mode === "history") {
      loadHistory();
    }
    
    // Cleanup blob URLs on unmount
    return () => {
      blobUrlCache.current.forEach(url => URL.revokeObjectURL(url));
      blobUrlCache.current.clear();
    };
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
    
    // Check if trying to use custom voice without being logged in
    const token = localStorage.getItem("access_token");
    if (!token && selectedVoice.is_custom) {
      if (confirm("Custom voices are only available to signed-in users. Would you like to sign in now?")) {
        window.location.href = "/login";
      }
      return;
    }
    
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

  // Fetch media (authenticated or guest) and return blob URL
  const fetchAuthenticatedMedia = async (url: string): Promise<string> => {
    // Check cache first
    if (blobUrlCache.current.has(url)) {
      return blobUrlCache.current.get(url)!;
    }

    try {
      const token = localStorage.getItem("access_token");
      const visitorId = localStorage.getItem("visitor_id");
      const apiUrl = "http://localhost:8000"; // Backend URL
      
      const headers: Record<string, string> = {
        "X-Visitor-Id": visitorId || "",
      };
      
      // Only add Authorization if token exists
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      
      const response = await fetch(`${apiUrl}${url}`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch media: ${response.statusText}`);
      }

      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      
      // Cache the blob URL
      blobUrlCache.current.set(url, blobUrl);
      
      return blobUrl;
    } catch (error) {
      console.error("Failed to fetch media:", error);
      throw error;
    }
  };

  // Log audio events to backend
  const logAudioEvent = async (
    action: string,
    metadata?: {
      generation_id?: number;
      transcription_id?: number;
      voice_id?: string;
      voice_name?: string;
      language?: string;
      audio_duration?: number;
      file_size?: number;
    }
  ) => {
    try {
      const formData = new FormData();
      formData.append("action", action);
      if (metadata?.generation_id) formData.append("generation_id", metadata.generation_id.toString());
      if (metadata?.transcription_id) formData.append("transcription_id", metadata.transcription_id.toString());
      if (metadata?.voice_id) formData.append("voice_id", metadata.voice_id);
      if (metadata?.voice_name) formData.append("voice_name", metadata.voice_name);
      if (metadata?.language) formData.append("language", metadata.language);
      if (metadata?.audio_duration) formData.append("audio_duration", metadata.audio_duration.toString());
      if (metadata?.file_size) formData.append("file_size", metadata.file_size.toString());
      
      await apiRequest("/audio/events", {
        method: "POST",
        body: formData
      });
    } catch (error) {
      // Don't fail the main operation if logging fails
      console.error("Failed to log audio event:", error);
    }
  };

  const playAudio = async (url: string, metadata?: { 
    generation_id?: number;
    voice_id?: string;
    voice_name?: string;
    duration?: number;
    file_size?: number;
  }) => {
    if (audioRef.current) {
      if (currentAudioUrl === url && isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        try {
          const blobUrl = await fetchAuthenticatedMedia(url);
          audioRef.current.src = blobUrl;
          await audioRef.current.play();
          setCurrentAudioUrl(url);
          setIsPlaying(true);
          
          // Log play event
          if (metadata?.generation_id) {
            await logAudioEvent("play", {
              generation_id: metadata.generation_id,
              voice_id: metadata.voice_id,
              voice_name: metadata.voice_name,
              audio_duration: metadata.duration,
              file_size: metadata.file_size
            });
          }
        } catch (error) {
          console.error("Failed to play audio:", error);
          alert("Failed to play audio. Please try again.");
        }
      }
    }
  };

  const downloadMedia = async (url: string, filename: string, metadata?: {
    generation_id?: number;
    transcription_id?: number;
    voice_id?: string;
    voice_name?: string;
    language?: string;
    duration?: number;
    file_size?: number;
  }) => {
    try {
      const blobUrl = await fetchAuthenticatedMedia(url);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      // Log download event
      await logAudioEvent("download", metadata);
    } catch (error) {
      console.error("Failed to download media:", error);
      alert("Failed to download file. Please try again.");
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

  const handlePreviewPlay = async (voice: Voice) => {
    if (playingPreview === voice.voice_id) {
      // Stop playing
      if (previewAudioRef.current) {
        previewAudioRef.current.pause();
        previewAudioRef.current = null;
      }
      setPlayingPreview(null);
      return;
    }
    
    try {
      setLoadingPreview(voice.voice_id);
      
      const url = `/audio/voices/${voice.voice_id}/preview`;
      const response = await apiRequest(url, { method: "GET", isBlob: true });
      const blob = await response.blob();
      const audioUrl = URL.createObjectURL(blob);
      
      const audio = new Audio(audioUrl);
      previewAudioRef.current = audio;
      setPlayingPreview(voice.voice_id);
      setLoadingPreview(null);
      
      audio.onended = () => {
        setPlayingPreview(null);
        URL.revokeObjectURL(audioUrl);
      };
      
      await audio.play();
    } catch (error: any) {
      setLoadingPreview(null);
      alert(`Preview failed: ${error.message}`);
    }
  };

  const filteredVoices = voices.filter((v) => {
    if (genderFilter && v.gender !== genderFilter) return false;
    if (ageFilter && v.age_group !== ageFilter) return false;
    if (langFilter && v.language !== langFilter) return false;
    if (regionFilter && v.region !== regionFilter) return false;
    if (countryFilter && v.country !== countryFilter) return false;
    if (voiceTypeFilter && v.voice_type !== voiceTypeFilter) return false;
    if (searchFilter) {
      const search = searchFilter.toLowerCase();
      if (!v.name.toLowerCase().includes(search) && 
          !v.voice_id.toLowerCase().includes(search)) {
        return false;
      }
    }
    return true;
  });
  
  const languages = Array.from(new Set(voices.map(v => v.language)));
  const regions = Array.from(new Set(voices.filter(v => v.region).map(v => v.region)));
  const countries = Array.from(new Set(voices.filter(v => v.country).map(v => v.country)));
  const voiceTypes = Array.from(new Set(voices.filter(v => v.voice_type).map(v => v.voice_type)));

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
                placeholder={`Enter text to convert to speech (up to ${localStorage.getItem("access_token") ? "5000" : "1000"} characters)...`}
                rows={6}
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                maxLength={localStorage.getItem("access_token") ? 5000 : 1000}
              />
              <VoiceInput
                onTranscript={(text) => {
                  setTtsText((prev) => (prev ? `${prev} ${text}` : text));
                }}
                language="en-IN"
              />
            </div>
            
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
              {ttsText.length} / {localStorage.getItem("access_token") ? "5000" : "1000"} characters
              {!localStorage.getItem("access_token") && " (Sign in for 5000 characters)"}
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
                  <button 
                    className="secondary-button"
                    onClick={() => downloadMedia(generatedAudio, `tts_audio.${outputFormat}`)}
                  >
                    <Download size={16} /> Download
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="generation-card">
            <h3>Voice Library</h3>
            
            <div className="voice-filters" style={{display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px"}}>
              <div className="filter-group">
                <label>Search:</label>
                <input 
                  type="text" 
                  placeholder="Voice name..." 
                  value={searchFilter} 
                  onChange={(e) => setSearchFilter(e.target.value)}
                />
              </div>
              
              <div className="filter-group">
                <label>Region:</label>
                <select value={regionFilter} onChange={(e) => setRegionFilter(e.target.value)}>
                  <option value="">All Regions</option>
                  {regions.map(r => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              
              <div className="filter-group">
                <label>Country:</label>
                <select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)}>
                  <option value="">All Countries</option>
                  {countries.map(c => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>
              
              <div className="filter-group">
                <label>Gender:</label>
                <select value={genderFilter} onChange={(e) => setGenderFilter(e.target.value)}>
                  <option value="">All</option>
                  <option value="male">Male</option>
                  <option value="female">Female</option>
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
              
              <div className="filter-group">
                <label>Style/Type:</label>
                <select value={voiceTypeFilter} onChange={(e) => setVoiceTypeFilter(e.target.value)}>
                  <option value="">All Types</option>
                  {voiceTypes.map(t => (
                    <option key={t} value={t}>{t}</option>
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
                    <div className="voice-name">
                      {voice.name}
                      {voice.country && <span style={{fontSize: "12px", marginLeft: "8px", opacity: 0.7}}>
                        {voice.region} - {voice.country}
                      </span>}
                    </div>
                    <div className="voice-tags">
                      <span className="tag">{voice.gender}</span>
                      <span className="tag">{voice.age_group}</span>
                      <span className="tag">{voice.language}</span>
                      {voice.voice_type && <span className="tag">{voice.voice_type}</span>}
                      {voice.is_custom && <span className="tag custom">Custom</span>}
                    </div>
                  </div>
                  <button
                    className="preview-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handlePreviewPlay(voice);
                    }}
                    disabled={loadingPreview === voice.voice_id}
                  >
                    {loadingPreview === voice.voice_id ? (
                      <span style={{animation: "spin 1s linear infinite"}}>⏳</span>
                    ) : playingPreview === voice.voice_id ? (
                      <>
                        <Pause size={16} />
                        Stop
                      </>
                    ) : (
                      <>
                        <Play size={16} />
                        Preview
                      </>
                    )}
                  </button>
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
                <button 
                  className="secondary-button"
                  onClick={() => downloadMedia(transcriptResult.txt_url, "transcript.txt", {
                    transcription_id: transcriptResult.id,
                    language: transcriptResult.language,
                    duration: transcriptResult.duration
                  })}
                >
                  <FileText size={16} /> Download TXT
                </button>
                <button 
                  className="secondary-button"
                  onClick={() => downloadMedia(transcriptResult.srt_url, "transcript.srt", {
                    transcription_id: transcriptResult.id,
                    language: transcriptResult.language,
                    duration: transcriptResult.duration
                  })}
                >
                  <FileText size={16} /> Download SRT
                </button>
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
                        onClick={() => playAudio(item.download_url, {
                          generation_id: item.id,
                          voice_name: item.voice_name,
                          duration: item.duration,
                          file_size: item.file_size
                        })}
                        title="Play"
                      >
                        {currentAudioUrl === item.download_url && isPlaying ? <Pause size={18} /> : <Play size={18} />}
                      </button>
                      <button 
                        className="icon-button"
                        onClick={() => downloadMedia(item.download_url, `tts_${item.id}.mp3`, {
                          generation_id: item.id,
                          voice_name: item.voice_name,
                          duration: item.duration,
                          file_size: item.file_size
                        })}
                        title="Download"
                      >
                        <Download size={18} />
                      </button>
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
                      <button 
                        className="icon-button"
                        onClick={() => downloadMedia(item.txt_url, `transcript_${item.id}.txt`, {
                          transcription_id: item.id,
                          language: item.language,
                          duration: item.duration
                        })}
                        title="Download TXT"
                      >
                        <FileText size={18} />
                      </button>
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
