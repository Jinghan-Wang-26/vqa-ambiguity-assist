"use client";

import { useMemo, useRef } from "react";
import { createSpeechRecognition, speak, stopSpeaking } from "../lib/speech";

export default function VoiceControls({
  onTranscript,
  onAnnounce,
  enabledSpeak,
}: {
  onTranscript: (t: string) => void;
  onAnnounce: (t: string) => void;
  enabledSpeak: boolean;
}) {
  const recognition = useMemo(() => createSpeechRecognition(), []);
  const listeningRef = useRef(false);

  function startListening() {
    if (!recognition) {
      onAnnounce("Speech recognition is not supported in this browser.");
      return;
    }
    if (listeningRef.current) return;

    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (e: any) => {
      const t = e.results[0][0].transcript as string;
      onTranscript(t);
      onAnnounce(`Heard: ${t}`);
      if (enabledSpeak) speak(`Heard: ${t}`);
    };

    recognition.onerror = () => onAnnounce("Voice input failed.");
    recognition.onend = () => { listeningRef.current = false; };

    listeningRef.current = true;
    recognition.start();
    onAnnounce("Listening. Speak your question now.");
    if (enabledSpeak) speak("Listening. Speak your question now.");
  }

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <button onClick={startListening} aria-label="Start voice input">
        🎙️ Voice Input
      </button>
      <button onClick={stopSpeaking} aria-label="Stop voice output">
        ⏹ Stop Speech
      </button>
    </div>
  );
}
