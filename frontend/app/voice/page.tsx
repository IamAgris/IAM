"use client";

import React from "react";
import { Mic, Volume2, Activity, MicOff, VolumeOff } from "lucide-react";
import { api } from "@/lib/api";

export default function VoicePage() {
  const [sttResult, setSttResult] = React.useState<{
    text: string;
    language: string;
    confidence: number;
  } | null>(null);
  const [ttsAudio, setTtsAudio] = React.useState<string | null>(null);
  const [isRecording, setIsRecording] = React.useState(false);
  const [isSpeaking, setIsSpeaking] = React.useState(false);
  const [ttsText, setTtsText] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);

  const handleSTT = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // In a real browser, we'd use MediaRecorder to capture audio
    // For this demo, show a placeholder
    setError("Browser audio capture requires MediaRecorder API integration. Use the API directly: POST /api/v1/voice/speech-to-text");
  };

  const handleTTS = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ttsText.trim()) return;
    setIsSpeaking(true);
    setError(null);

    try {
      const response = await api.post("/api/v1/voice/text-to-speech", {
        text: ttsText,
        voice_id: "aura-default",
        format: "mp3",
      });
      setTtsAudio(response.data.audio_base64 || null);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "TTS failed");
    } finally {
      setIsSpeaking(false);
    }
  };

  return (
    <main className="p-4 lg:p-8 space-y-6">
      <header>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Mic className="w-6 h-6" /> Voice Communication
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Speech-to-text for listening, text-to-speech for speaking.
          Configure your STT/TTS provider in the backend settings.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* STT Panel */}
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5" />
            <h2 className="font-semibold">Speech-to-Text</h2>
          </div>
          <form onSubmit={handleSTT} className="space-y-4">
            <div className="flex flex-col items-center justify-center py-8 border-2 border-dashed border-input rounded-lg">
              <div className={`p-4 rounded-full ${isRecording ? "bg-red-500" : "bg-muted"}`}>
                {isRecording ? (
                  <MicOff className="w-6 h-6 text-white" />
                ) : (
                  <Mic className="w-6 h-6 text-muted-foreground" />
                )}
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                {isRecording ? "Listening..." : "Click to start recording"}
              </p>
            </div>
            <button
              type="button"
              disabled={isRecording}
              onClick={() => setIsRecording(!isRecording)}
              className="w-full py-2 rounded-lg border border-input bg-background text-foreground hover:bg-muted transition"
            >
              {isRecording ? "Stop Recording" : "Start Recording"}
            </button>
          </form>

          {sttResult && (
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <h3 className="font-medium mb-2">Transcription</h3>
              <p className="text-sm">{sttResult.text}</p>
              <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                <span>Language: {sttResult.language}</span>
                <span>Confidence: {(sttResult.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
          )}
        </div>

        {/* TTS Panel */}
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Volume2 className="w-5 h-5" />
            <h2 className="font-semibold">Text-to-Speech</h2>
          </div>
          <form onSubmit={handleTTS} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Text to Speak</label>
              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                rows={4}
                placeholder="Type what you want AURA to say..."
                className="w-full px-4 py-2 rounded-lg border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
            <button
              type="submit"
              disabled={isSpeaking || !ttsText.trim()}
              className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition flex items-center justify-center gap-2"
            >
              {isSpeaking ? (
                <>
                  <Volume2 className="w-4 h-4 animate-pulse" /> Speaking...
                </>
              ) : (
                <>
                  <Volume2 className="w-4 h-4" /> Generate Speech
                </>
              )}
            </button>
          </form>

          {ttsAudio && (
            <div className="mt-6 p-4 bg-muted rounded-lg">
              <h3 className="font-medium mb-2">Generated Audio</h3>
              <audio
                controls
                className="w-full"
                src={`data:audio/mpeg;base64,${ttsAudio}`}
              />
              <p className="text-xs text-muted-foreground mt-2">
                Base64-encoded audio ready for playback.
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error}
        </div>
      )}

      <div className="bg-muted rounded-lg p-6">
        <h3 className="font-semibold mb-4">API Reference</h3>
        <div className="space-y-2 text-sm font-mono text-muted-foreground">
          <div>POST /api/v1/voice/speech-to-text — Upload audio, get transcription</div>
          <div>POST /api/v1/voice/text-to-speech — Convert text to audio (base64)</div>
          <div>POST /api/v1/voice/voice-activity — Detect voice in audio</div>
        </div>
      </div>
    </main>
  );
}
