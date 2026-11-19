import { useEffect, useRef, useState } from "react";
import { Mic, MicOff } from "lucide-react";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  language?: string;
  className?: string;
}

// Supported languages
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

export default function VoiceInput({
  onTranscript,
  language = "en-IN",
  className = "",
}: VoiceInputProps) {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const silenceTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Check for Web Speech API support
    const SpeechRecognition =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
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
      // Clear silence timeout on any result
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

      // Send transcript to parent
      if (finalTranscript) {
        onTranscript(finalTranscript.trim());
      } else if (interimTranscript) {
        onTranscript(interimTranscript.trim());
      }

      // Set silence timeout (3 seconds)
      silenceTimeoutRef.current = setTimeout(() => {
        if (recognitionRef.current && isListening) {
          recognitionRef.current.stop();
        }
      }, 3000);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      
      if (event.error === "not-allowed") {
        setError("Microphone permission denied. Please allow microphone access.");
      } else if (event.error === "no-speech") {
        setError("No speech detected. Please try again.");
      } else if (event.error === "network") {
        setError("Network error. Please check your connection.");
      } else {
        setError(`Error: ${event.error}`);
      }
      
      setIsListening(false);
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

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      if (silenceTimeoutRef.current) {
        clearTimeout(silenceTimeoutRef.current);
      }
    };
  }, [language, onTranscript, isListening]);

  const toggleListening = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.lang = language;
        recognitionRef.current.start();
      } catch (err) {
        console.error("Failed to start recognition:", err);
        setError("Failed to start voice recognition.");
      }
    }
  };

  if (!isSupported) {
    return (
      <button
        type="button"
        className={`voice-input-button voice-input-unsupported ${className}`}
        title="Voice input not supported in this browser"
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
        <span className="voice-input-status">Listening...</span>
      )}
      {error && (
        <span className="voice-input-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
