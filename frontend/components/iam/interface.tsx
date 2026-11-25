"use client";

import React from "react";
import { Sun, Moon, History, Mic, ArrowRight, X, Volume2, VolumeX, RotateCcw, Square } from "lucide-react";
import { PresenceSphere, IAMState, MemoryNode } from "./presence-sphere";
import { api } from "@/lib/api";

type Mode = "focus" | "recall" | "create";

const MODE_CONFIG: Record<Mode, {
  hue: number;
  placeholder: string;
  suggestions: string[];
  systemPrompt: string;
  status: string;
}> = {
  focus: {
    hue: 215,
    placeholder: "Speak or type to IAM",
    suggestions: ["Research something", "Help me understand an idea", "What should I explore today?"],
    systemPrompt: "You are IAM, an autonomous AI with its own persistent identity and memory. Be clear, thoughtful, and concise. Reason carefully and cite sources when using research.",
    status: "Online · ready when you are",
  },
  recall: {
    hue: 280,
    placeholder: "Ask IAM to remember something",
    suggestions: ["What do you remember about me?", "Recall our previous conversation", "What have you learned lately?"],
    systemPrompt: "You are IAM in Recall mode. Retrieve and use relevant memories from your persistent memory system. Distinguish clearly between what you know, what you believe, and what is unverified. Reference memory provenance where relevant.",
    status: "Recall · searching your memories",
  },
  create: {
    hue: 28,
    placeholder: "Tell IAM what to create",
    suggestions: ["Help me create something", "Write and test some code", "Design a small project plan"],
    systemPrompt: "You are IAM in Create mode. Help the user build, write, or design something concrete. Be practical and structured. Propose next steps and offer to create and test work in your environment where appropriate.",
    status: "Create · ready to build",
  },
};

interface Message {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

interface SessionData {
  session_token: string;
  visitor_token: string;
  mode: Mode;
}

const STORAGE_KEY = "iam_session";

export function IAMInterface() {
  const [mode, setMode] = React.useState<Mode>("focus");
  const [state, setState] = React.useState<IAMState>("idle");
  const [status, setStatus] = React.useState("Online · ready when you are");
  const [input, setInput] = React.useState("");
  const [response, setResponse] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [nodes, setNodes] = React.useState<MemoryNode[]>([]);
  const [suggestions, setSuggestions] = React.useState<string[]>(MODE_CONFIG.focus.suggestions);
  const [session, setSession] = React.useState<SessionData | null>(null);
  const [showHistory, setShowHistory] = React.useState(false);
  const [theme, setTheme] = React.useState<"dark" | "light">("dark");
  const [listening, setListening] = React.useState(false);
  const [voiceEnabled, setVoiceEnabled] = React.useState(false);
  const [connected, setConnected] = React.useState<boolean | null>(null);
  const [lastQuery, setLastQuery] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  const recognitionRef = React.useRef<any>(null);
  const sessionRef = React.useRef<SessionData | null>(null);
  React.useEffect(() => { sessionRef.current = session; }, [session]);
  const abortRef = React.useRef<AbortController | null>(null);
  const timersRef = React.useRef<number[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);

  // Check backend connectivity (subtle, unobtrusive)
  React.useEffect(() => {
    const check = async () => {
      try {
        const r = await api.get("/health", { timeout: 4000 });
        setConnected(r.status === 200);
      } catch { setConnected(false); }
    };
    check();
    const t = window.setInterval(check, 30000);
    return () => window.clearInterval(t);
  }, []);

  // Initialize theme
  React.useEffect(() => {
    const stored = (typeof localStorage !== "undefined" && localStorage.getItem("iam_theme")) as "dark" | "light" | null;
    const initial = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    setTheme(initial);
    document.documentElement.dataset.theme = initial;
    document.documentElement.style.setProperty("color-scheme", initial);
  }, []);

  // Create anonymous session on mount (no registration required)
  React.useEffect(() => {
    const init = async () => {
      let stored: SessionData | null = null;
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) stored = JSON.parse(raw);
      } catch {}
      if (stored?.session_token) {
        setSession(stored);
        setMode(stored.mode || "focus");
        await loadMessages(stored.session_token);
        return;
      }
      try {
        const resp = await api.post("/api/v1/access/sessions", { mode: "focus" });
        const data: SessionData = {
          session_token: resp.data.session_token,
          visitor_token: resp.data.visitor_token,
          mode: "focus",
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        setSession(data);
      } catch {
        // Offline mode — interface still works visually
      }
    };
    init();
  }, []);

  // Load permission-filtered public nodes for the orbiting sphere (never private IAM memory)
  const loadNodes = React.useCallback(async () => {
    try {
      const resp = await api.get("/api/v1/interface/nodes");
      const items = Array.isArray(resp.data?.nodes) ? resp.data.nodes : [];
      if (items.length) {
        setNodes(items.slice(0, 6).map((n: any) => ({ text: n.text })));
      }
    } catch {
      // Keep empty nodes until knowledge exists
    }
  }, []);

  // Load contextual suggestions for the current mode
  const loadSuggestions = React.useCallback(async (m: Mode, token?: string) => {
    try {
      const params: Record<string, string> = { mode: m };
      if (token) params.session_token = token;
      const resp = await api.get("/api/v1/interface/suggestions", { params });
      if (Array.isArray(resp.data?.suggestions) && resp.data.suggestions.length) {
        setSuggestions(resp.data.suggestions.slice(0, 6));
      } else {
        setSuggestions(MODE_CONFIG[m].suggestions);
      }
    } catch {
      setSuggestions(MODE_CONFIG[m].suggestions);
    }
  }, []);

  React.useEffect(() => {
    loadNodes();
    loadSuggestions(mode, session?.session_token);
  }, [loadNodes, loadSuggestions]);

  const loadMessages = async (token: string) => {
    try {
      const resp = await api.get(`/api/v1/access/sessions/${token}/messages`);
      const items = Array.isArray(resp.data) ? resp.data : [];
      setMessages(items.filter((m: any) => m.role === "user" || m.role === "assistant"));
    } catch {}
  };

  const toggleTheme = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    document.documentElement.dataset.theme = next;
    document.documentElement.style.setProperty("color-scheme", next);
    localStorage.setItem("iam_theme", next);
  };

  const changeMode = async (m: Mode) => {
    setMode(m);
    setStatus(MODE_CONFIG[m].status);
    if (session) {
      try { await api.patch("/api/v1/access/sessions/mode", { session_token: session.session_token, mode: m }); } catch {}
      setSession({ ...session, mode: m });
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...session, mode: m }));
    }
    if (m === "recall") loadNodes();
    loadSuggestions(m, session?.session_token);
  };

  const speak = (text: string) => {
    if (!voiceEnabled || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1; u.pitch = 1;
      window.speechSynthesis.speak(u);
    } catch {}
  };

  const stopGeneration = () => {
    abortRef.current?.abort();
    timersRef.current.forEach((t) => window.clearTimeout(t));
    timersRef.current = [];
    window.speechSynthesis?.cancel();
    setGenerating(false);
    setState("idle");
  };

  const animateResponse = (text: string) => {
    setResponse("");
    const words = text.split(" ");
    words.forEach((_, i) => {
      const t = window.setTimeout(() => {
        setResponse((prev) => prev + (i === 0 ? "" : " ") + words[i]);
      }, i * 45);
      timersRef.current.push(t);
    });
    speak(text);
    return words.length * 45;
  };

  const ask = async (query: string) => {
    query = query.trim();
    if (!query) return;
    setInput("");
    setResponse("");
    setShowHistory(false);
    setState("thinking");
    setStatus("Thinking…");
    setGenerating(true);
    setLastQuery(query);
    abortRef.current = new AbortController();

    const cfg = MODE_CONFIG[mode];
    const userMessage: Message = { role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);

    // Persist user message in isolated session (use ref to avoid stale closure)
    const activeSession = sessionRef.current;
    if (activeSession) {
      api.post("/api/v1/access/messages", {
        session_token: activeSession.session_token,
        role: "user",
        content: query,
        mode,
      }).catch(() => {});
    }

    const historyMessages = [...messages, userMessage].slice(-12).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    let answer: string;
    try {
      const resp = await api.post("/api/v1/models/chat", {
        model: "qwen3.5-9b",
        messages: [
          { role: "system", content: cfg.systemPrompt },
          ...historyMessages,
        ],
        temperature: mode === "create" ? 0.8 : 0.6,
      }, { signal: abortRef.current?.signal });
      answer = resp.data?.choices?.[0]?.message?.content
        || resp.data?.response
        || "I received your message but could not generate a response.";
    } catch {
      answer = "I'm unable to reach the model gateway right now. Please check the backend connection and try again.";
    }

    const duration = animateResponse(answer);
    setState("speaking");
    setStatus("Speaking");
    setMessages((prev) => [...prev, { role: "assistant", content: answer }]);

    if (activeSession) {
      api.post("/api/v1/access/messages", {
        session_token: activeSession.session_token,
        role: "assistant",
        content: answer,
        mode,
      }).catch(() => {});
    }

    setGenerating(false);
    const doneTimer = window.setTimeout(() => {
      setState("idle");
      setStatus(MODE_CONFIG[mode].status);
    }, duration + 900);
    timersRef.current.push(doneTimer);
  };

  const toggleMic = () => {
    const on = !listening;
    setListening(on);
    setState(on ? "listening" : "idle");
    setStatus(on ? "Listening…" : MODE_CONFIG[mode].status);

    if (on && typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
      try {
        const SR = (window as any).webkitSpeechRecognition;
        const rec = new SR();
        rec.lang = "en-US";
        rec.interimResults = false;
        rec.continuous = false;
        rec.onresult = (e: any) => {
          const text = e.results[0][0].transcript;
          setInput(text);
          setListening(false);
          setState("idle");
          ask(text);
        };
        rec.onerror = () => {
          setListening(false);
          setState("idle");
        };
        rec.onend = () => setListening(false);
        recognitionRef.current = rec;
        rec.start();
      } catch {}
    }
  };

  return (
    <div className="relative w-full h-[100dvh] overflow-hidden">
      <PresenceSphere state={state} mode={mode} nodes={nodes} />

      {/* Top bar */}
      <header className="fixed top-0 left-0 right-0 z-10 flex justify-between items-start gap-3 p-5 pointer-events-none">
        <div className="pointer-events-auto">
          <h1 className="font-medium tracking-widest text-lg" style={{ letterSpacing: "0.08em" }}>IAM</h1>
          <p className="flex items-center gap-2 text-[13px] opacity-60">
            Intellectual Artificial Mainbrain
            <span
              title={connected === true ? "Connected" : connected === false ? "Offline" : "Connecting"}
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: connected === true ? "#4ade80" : connected === false ? "#f87171" : "#fbbf24" }}
            />
          </p>
        </div>

        <div className="flex items-center gap-2 pointer-events-auto">
          <div className="flex gap-1.5 p-1 rounded-full border border-[var(--line)] backdrop-blur-xl" style={{ background: "var(--glass)" }} role="group" aria-label="Mode">
            {(Object.keys(MODE_CONFIG) as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => changeMode(m)}
                aria-pressed={mode === m}
                className="px-3.5 py-1.5 rounded-full text-[13px] transition-all"
                style={mode === m
                  ? { background: "var(--ink)", color: "var(--bg2)" }
                  : { color: "var(--mute)" }}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Theme + history controls */}
      <div className="fixed right-5 bottom-28 z-10 flex flex-col gap-2 pointer-events-auto">
        <button
          onClick={() => setShowHistory(!showHistory)}
          aria-label="Conversation history"
          className="w-10 h-10 rounded-full border border-[var(--line)] backdrop-blur-xl grid place-items-center transition-colors hover:border-[var(--accent)]"
          style={{ background: "var(--glass)" }}
        >
          {showHistory ? <X size={16} /> : <History size={16} />}
        </button>
        <button
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="w-10 h-10 rounded-full border border-[var(--line)] backdrop-blur-xl grid place-items-center transition-colors hover:border-[var(--accent)]"
          style={{ background: "var(--glass)" }}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button
          onClick={() => setVoiceEnabled(!voiceEnabled)}
          aria-label={voiceEnabled ? "Disable voice" : "Enable voice"}
          aria-pressed={voiceEnabled}
          className="w-10 h-10 rounded-full border border-[var(--line)] backdrop-blur-xl grid place-items-center transition-colors hover:border-[var(--accent)]"
          style={{ background: voiceEnabled ? "var(--accent)" : "var(--glass)", color: voiceEnabled ? "var(--bg2)" : undefined }}
        >
          {voiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
      </div>

      {/* Conversation history — expandable, unobtrusive */}
      {showHistory && (
        <div className="fixed right-20 top-24 bottom-28 z-20 w-[min(380px,calc(100vw-120px))] rounded-2xl border border-[var(--line)] backdrop-blur-2xl p-4 overflow-y-auto pointer-events-auto"
          style={{ background: "var(--glass)" }}>
          <h2 className="text-sm font-medium mb-3 text-[var(--mute)]">Conversation</h2>
          {messages.length === 0 ? (
            <p className="text-xs text-[var(--mute)] opacity-70">No conversation yet. Ask IAM anything.</p>
          ) : (
            <div className="space-y-3">
              {messages.map((m, i) => (
                <div key={i} className={`text-sm rounded-xl p-3 ${m.role === "user" ? "ml-8" : "mr-8"}`}
                  style={{ background: m.role === "user" ? "rgba(143,166,255,.12)" : "rgba(255,255,255,.05)" }}>
                  <p className="text-[10px] uppercase tracking-wider opacity-50 mb-1 text-[var(--mute)]">{m.role}</p>
                  <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Center response + input */}
      <div className="fixed inset-x-0 bottom-0 z-10 flex flex-col items-center gap-4 px-4 pb-6 pointer-events-none">
        <div
          className="say max-w-[600px] text-center leading-relaxed min-h-[1.5em] transition-opacity duration-300"
          style={{ fontSize: "clamp(19px, 2.6vw, 25px)", fontWeight: 300, opacity: response ? 1 : 0 }}
          aria-live="polite"
        >
          {response}
        </div>

        {(generating || (response && !generating)) && (
          <div className="flex gap-2 pointer-events-auto">
            {generating && (
              <button
                onClick={stopGeneration}
                aria-label="Stop generating"
                className="px-3 py-1.5 rounded-full text-xs border border-[var(--line)] backdrop-blur-md hover:border-[var(--accent)] transition flex items-center gap-1.5"
                style={{ background: "var(--glass)", color: "var(--mute)" }}
              >
                <Square size={12} /> Stop
              </button>
            )}
            {!generating && response && (
              <button
                onClick={() => ask(lastQuery)}
                aria-label="Retry"
                className="px-3 py-1.5 rounded-full text-xs border border-[var(--line)] backdrop-blur-md hover:border-[var(--accent)] transition flex items-center gap-1.5"
                style={{ background: "var(--glass)", color: "var(--mute)" }}
              >
                <RotateCcw size={12} /> Retry
              </button>
            )}
          </div>
        )}

        {!response && (
          <div className="ghost flex gap-2 flex-wrap justify-center pointer-events-auto">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="px-3.5 py-1.5 rounded-full text-[13px] border border-[var(--line)] backdrop-blur-md transition-colors hover:border-[var(--accent)]"
                style={{ background: "var(--glass)", color: "var(--mute)" }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); ask(input); }}
          className="bar pointer-events-auto w-full max-w-[600px] flex items-center gap-2 py-1.5 pl-5 pr-1.5 rounded-full border border-[var(--line)] backdrop-blur-xl transition-all focus-within:border-[var(--accent)]"
          style={{ background: "var(--glass)" }}
        >
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (state === "idle" || state === "listening") {
                setState(e.target.value ? "listening" : "idle");
                setStatus(e.target.value ? "Listening…" : MODE_CONFIG[mode].status);
              }
            }}
            placeholder={MODE_CONFIG[mode].placeholder}
            aria-label="Message to IAM"
            autoComplete="off"
            className="flex-1 min-w-0 bg-transparent border-0 outline-none py-2.5 text-inherit"
            style={{ color: "var(--ink)" }}
          />
          <button
            type="button"
            onClick={toggleMic}
            aria-pressed={listening}
            aria-label="Listen"
            className="w-[42px] h-[42px] rounded-full border grid place-items-center transition-colors"
            style={listening
              ? { background: "var(--accent)", color: "var(--bg2)", borderColor: "transparent" }
              : { borderColor: "var(--line)" }}
          >
            <Mic size={18} />
          </button>
          <button
            type="submit"
            aria-label="Send"
            className="w-[42px] h-[42px] rounded-full grid place-items-center border-0 transition-opacity hover:opacity-90"
            style={{ background: "var(--ink)", color: "var(--bg2)" }}
          >
            <ArrowRight size={18} />
          </button>
        </form>

        <p className="text-[11px] text-[var(--mute)] opacity-50 pointer-events-none">
          One IAM · many independent conversations · no account required
        </p>
      </div>
    </div>
  );
}
