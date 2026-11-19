import { useEffect, useRef, useState } from "react";
import { Mic, MicOff, AlertCircle } from "lucide-react";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  language?: string;
  className?: string;
}

export const VOICE_LANGUAGES = [
  { code: "en-IN", label: "English (India)" },
  { code: "en-US", label: "English (US)" },
  { code: "hi-IN", label: "हिन्दी (Hindi)" },
  { code: "te-IN", label: "తెలుగు (Telugu)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
  { code: "mr-IN", label: "मराठी (Marathi)" },
  { code: "bn-IN", label: "বাংলা (Bengali)" },
  { code: "gu-IN", label: "ગુજરાતી (Gujarati)" },
  { code: "kn-IN", label: "ಕನ್ನಡ (Kannada)" },
  { code: "ml-IN", label: "മലയാളം (Malayalam)" },
] as const;

type PermissionState = "prompt" | "granted" | "denied" | "unsupported";

export default function VoiceInput({
  onTranscript,
  language = "en-IN",
  className = "",
}: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [permissionState, setPermissionState] = useState<PermissionState>("prompt");
  const [error, setError] = useState<string | null>(null);
  const [useFallback, setUseFallback] = useState(false);
  
  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const silenceTimeoutRef = useRef<number | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setUseFallback(true);
      checkMicrophonePermission();
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event: any) => {
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }

      let interimTranscript = "";
      let finalTranscript = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + " ";
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        onTranscript(finalTranscript.trim());
      } else if (interimTranscript) {
        onTranscript(interimTranscript.trim());
      }

      silenceTimeoutRef.current = setTimeout(() => {
        if (recognitionRef.current && isListening) {
          recognitionRef.current.stop();
        }
      }, 3000);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      
      const errorMessages: Record<string, string> = {
        "not-allowed": "Microphone access denied.",
        "service-not-allowed": "Speech recognition service not available.",
        "no-speech": "No speech detected.",
        "network": "Network error. Check your connection.",
        "audio-capture": "Microphone not available or in use.",
        "aborted": "Recognition aborted.",
      };

      setError(errorMessages[event.error] || `Error: ${event.error}`);
      setIsListening(false);
      
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setPermissionState("denied");
      }

      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
    };

    recognitionRef.current = recognition;
    checkMicrophonePermission();

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {}
      }
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
      stopMediaStream();
    };
  }, [language, onTranscript, isListening]);

  const checkMicrophonePermission = async () => {
    if (!navigator.permissions) {
      setPermissionState("unsupported");
      return;
    }

    try {
      const result = await navigator.permissions.query({ name: "microphone" as PermissionName });
      setPermissionState(result.state as PermissionState);
      
      result.addEventListener("change", () => {
        setPermissionState(result.state as PermissionState);
      });
    } catch (err) {
      console.warn("Permissions API not fully supported:", err);
      setPermissionState("unsupported");
    }
  };

  const requestMicrophoneAccess = async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      setPermissionState("granted");
      setError(null);
      return true;
    } catch (err: any) {
      console.error("Microphone access error:", err);
      
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setPermissionState("denied");
        setError("Microphone access denied.");
      } else if (err.name === "NotFoundError") {
        setError("No microphone found.");
      } else if (err.name === "NotReadableError") {
        setError("Microphone is in use by another app.");
      } else {
        setError("Could not access microphone.");
      }
      
      return false;
    }
  };

  const stopMediaStream = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
  };

  const startWebSpeechRecognition = async () => {
    if (!recognitionRef.current) return false;

    try {
      recognitionRef.current.lang = language;
      recognitionRef.current.start();
      return true;
    } catch (err) {
      console.error("Failed to start recognition:", err);
      setError("Failed to start speech recognition.");
      return false;
    }
  };

  const startFallbackRecording = async () => {
    if (!mediaStreamRef.current) return false;

    try {
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(mediaStreamRef.current);
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await transcribeAudio(audioBlob);
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsListening(true);
      setError(null);

      silenceTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current?.state === "recording") {
          mediaRecorderRef.current.stop();
        }
      }, 5000);

      return true;
    } catch (err) {
      console.error("Failed to start recording:", err);
      setError("Failed to start recording.");
      return false;
    }
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append("audio", audioBlob, "audio.webm");
      formData.append("language", language.split("-")[0]);

      const response = await fetch("/api/v1/transcribe", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Transcription failed");
      }

      const data = await response.json();
      if (data.text) {
        onTranscript(data.text);
      }
    } catch (err) {
      console.error("Transcription error:", err);
      setError("Transcription failed. Using Web Speech API fallback.");
      setUseFallback(false);
    } finally {
      setIsListening(false);
    }
  };

  const toggleListening = async () => {
    if (isListening) {
      if (useFallback && mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      } else if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    if (!mediaStreamRef.current) {
      const hasAccess = await requestMicrophoneAccess();
      if (!hasAccess) return;
    }

    if (useFallback) {
      await startFallbackRecording();
    } else {
      await startWebSpeechRecognition();
    }
  };

  const retryPermission = async () => {
    setError(null);
    setPermissionState("prompt");
    await toggleListening();
  };

  if (permissionState === "unsupported" && !navigator.mediaDevices) {
    return (
      <button
        type="button"
        className={`voice-input-button voice-input-unsupported ${className}`}
        title="Voice input requires HTTPS or localhost"
        disabled
      >
        <MicOff size={18} />
      </button>
    );
  }

  return (
    <div className="voice-input-wrapper">
      <button
        type="button"
        className={`voice-input-button ${isListening ? "is-listening" : ""} ${className}`}
        onClick={toggleListening}
        title={isListening ? "Stop listening" : "Start voice input"}
        aria-label={isListening ? "Stop listening" : "Start voice input"}
      >
        {isListening ? (
          <>
            <Mic size={18} className="voice-input-icon-pulse" />
            <span className="voice-input-listening-dot" />
          </>
        ) : (
          <Mic size={18} />
        )}
      </button>
      {isListening && (
        <span className="voice-input-status">
          {useFallback ? "Recording..." : "Listening..."}
        </span>
      )}
      {error && (
        <div className="voice-input-error" role="alert">
          <AlertCircle size={14} />
          <span>{error}</span>
          {permissionState === "denied" && (
            <div className="voice-input-help">
              <p>To enable microphone:</p>
              <ol>
                <li>Click the lock/site info icon in address bar</li>
                <li>Go to Site permissions → Microphone</li>
                <li>Select "Allow"</li>
                <li>Reload the page</li>
              </ol>
              <button onClick={retryPermission} className="voice-input-retry">
                Retry
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
