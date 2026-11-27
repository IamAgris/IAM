"use client";

import React from "react";
import { Sun, Moon, History, Mic, ArrowRight, X, Volume2, VolumeX, RotateCcw, Square, Paperclip, Copy, Wand2, Settings2, Trash2, Activity, Minus, ChevronDown } from "lucide-react";
import { PresenceSphere, IAMState, MemoryNode, SourceNode, SphereActivity, KnowledgeConnection, KnowledgeCluster, FreshnessInfo, MapPlace } from "./presence-sphere";
import { api } from "@/lib/api";

type Mode = "focus" | "recall" | "create";

interface ProvenanceSource {
  title: string;
  url: string | null;
  domain: string;
  node_id: string | null;
  credibility: number;
}

interface ProvenanceItem {
  title: string;
  summary: string;
  confidence: number;
  created_at: string | null;
  sources: ProvenanceSource[];
}

interface ProvenanceResponse {
  cluster: string;
  items: ProvenanceItem[];
  claim: string;
}

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

function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i} className="font-semibold">{part.slice(2, -2)}</strong>;
        if (part.startsWith("`") && part.endsWith("`"))
          return <code key={i} className="rounded bg-white/10 px-1 py-0.5 text-[0.85em]">{part.slice(1, -1)}</code>;
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </>
  );
}

/** Lightweight, safe response formatting — no raw HTML from model output. */
function FormattedResponse({ text }: { text: string }) {
  const lines = text.split("\n");
  let inCode = false;
  return (
    <div className="space-y-2">
      {lines.map((line, i) => {
        if (line.trim().startsWith("```")) {
          inCode = !inCode;
          return null;
        }
        if (inCode)
          return (
            <pre key={i} className="overflow-x-auto rounded-xl border border-[var(--line)] bg-black/25 p-3 text-left text-[0.8em] font-mono leading-snug">
              {line}
            </pre>
          );
        if (!line.trim()) return <div key={i} className="h-1" />;
        const bullet = line.match(/^\s*[-*]\s+(.*)$/);
        const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
        const heading = line.match(/^\s*#{2,4}\s+(.*)$/);
        if (bullet)
          return <div key={i} className="ml-5 list-disc text-left"><InlineText text={bullet[1]} /></div>;
        if (numbered)
          return <div key={i} className="ml-5 list-decimal text-left"><InlineText text={numbered[1]} /></div>;
        if (heading)
          return <div key={i} className="font-semibold text-left"><InlineText text={heading[1]} /></div>;
        return <div key={i} className="text-left"><InlineText text={line} /></div>;
      })}
    </div>
  );
}

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
  const [theme, setTheme] = React.useState<"dark" | "light">("light");
  const [listening, setListening] = React.useState(false);
  const [voiceEnabled, setVoiceEnabled] = React.useState(false);
  const [attachment, setAttachment] = React.useState<File | null>(null);
  const fileRef = React.useRef<HTMLInputElement>(null);
  const [connected, setConnected] = React.useState<boolean | null>(null);
  const [lastQuery, setLastQuery] = React.useState("");
  const [generating, setGenerating] = React.useState(false);
  const [showOptions, setShowOptions] = React.useState(false);
  // OD-51 model control stays inside the sphere. Only free models are offered.
  type ModelMode = "manual" | "auto" | "hybrid";
  const [modelMode, setModelMode] = React.useState<ModelMode>("hybrid");
  const [selectedModel, setSelectedModel] = React.useState<string | null>(null);
  const [freeModels, setFreeModels] = React.useState<Array<{ model_id: string; display_name: string | null }>>([]);
  const [providerKeys, setProviderKeys] = React.useState<Array<{ provider: string; key_alias: string; health: string; scope: string; is_enabled: boolean }>>([]);
  const [delegations, setDelegations] = React.useState<Array<{ model: string; status: string }>>([]);
  const [previousModel, setPreviousModel] = React.useState<string | null>(null);
  const [inference, setInference] = React.useState<{ mode: string; model: string | null; available: boolean } | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [responseMinimized, setResponseMinimized] = React.useState(false);
  const [responseDismissed, setResponseDismissed] = React.useState(false);
  const [activity, setActivity] = React.useState<SphereActivity | null>(null);
  const [sources, setSources] = React.useState<SourceNode[]>([]);
  const [connections, setConnections] = React.useState<KnowledgeConnection[]>([]);
  const [clusters, setClusters] = React.useState<KnowledgeCluster[]>([]);
  const [graphConnections, setGraphConnections] = React.useState<KnowledgeConnection[]>([]);
  const [freshness, setFreshness] = React.useState<Record<string, FreshnessInfo>>({});
  const [mapMode, setMapMode] = React.useState(false);
  const [mapPlaces, setMapPlaces] = React.useState<MapPlace[]>([]);
  const [hoveredSource, setHoveredSource] = React.useState<{ node: SourceNode; x: number; y: number } | null>(null);
  const [selectedSource, setSelectedSource] = React.useState<SourceNode | null>(null);
  const [provenance, setProvenance] = React.useState<ProvenanceResponse | null>(null);
  const [provenanceLoading, setProvenanceLoading] = React.useState(false);
  const [lastInference, setLastInference] = React.useState<{ mode: string; model: string } | null>(null);
  const compactResponse = response.length > 0 && response.length < 160 && !response.includes("\n");
  const allConnections = React.useMemo(() => {
    const merged = new Map<string, KnowledgeConnection>();
    // Stored graph links carry from_node/to_node; map them onto the source
    // endpoints the sphere draws so persisted provenance survives event ageing.
    const persisted: KnowledgeConnection[] = graphConnections
      .filter((c) => c.from_node && c.to_node)
      .map((c) => ({ ...c, from: c.from_node as string, to: c.to_node as string }));
    [...connections, ...persisted].forEach((c) => {
      merged.set(`${c.from}-${c.to}`, c);
    });
    return Array.from(merged.values());
  }, [connections, graphConnections]);
  const recognitionRef = React.useRef<any>(null);
  const sessionRef = React.useRef<SessionData | null>(null);
  React.useEffect(() => { sessionRef.current = session; }, [session]);
  const abortRef = React.useRef<AbortController | null>(null);
  const timersRef = React.useRef<number[]>([]);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const lastHoverRef = React.useRef<string | null>(null);

  // Check backend connectivity (subtle, unobtrusive)
  React.useEffect(() => {
    const check = async () => {
      try {
        const r = await api.get("/health", { timeout: 4000 });
        setConnected(r.status === 200);
        const m = await api.get("/api/v1/models/readiness", { timeout: 4000 });
        setInference({ mode: m.data.mode, model: m.data.model, available: m.data.available });
        // Read-only model/key status. No credential is ever requested by the browser.
        try {
          const [primary, models, keys] = await Promise.all([
            api.get("/api/v1/models/primary", { timeout: 4000 }),
            api.get("/api/v1/models/router/models?provider=nvidia", { timeout: 4000 }),
            api.get("/api/v1/models/credentials/health?provider=nvidia", { timeout: 4000 }),
          ]);
          setPreviousModel(primary.data.resolved_model || null);
          // Free models only: paid access is a separate signed decision (OD-04).
          setFreeModels(
            (Array.isArray(models.data) ? models.data : [])
              .filter((item: any) => item?.is_free === true && item?.is_available !== false)
              .map((item: any) => ({
                model_id: String(item.model_id),
                display_name: item.display_name ? String(item.display_name) : null,
              }))
              .slice(0, 8),
          );
          setProviderKeys(
            Array.isArray(keys.data?.keys) ? keys.data.keys : [],
          );
        } catch {}
      } catch { setConnected(false); }
    };
    check();
    const t = window.setInterval(check, 30000);
    return () => window.clearInterval(t);
  }, []);

  // Live, privacy-filtered IAM activity from the public event stream.
  React.useEffect(() => {
    const controller = new AbortController();

    const handle = (dataStr: string) => {
      try {
        const payload = JSON.parse(dataStr);
        const d = payload.details || {};
        const source = d.source;
        const now = Date.now();
        const nodeState: SourceNode["state"] =
          payload.event_type === "research.memory_stored" ? "stored"
          : payload.event_type === "research.source_extracted" ? "extracted"
          : payload.event_type === "research.page_opened" ? "opened"
          : "discovered";

        setActivity({
          event_type: payload.event_type,
          label: d.label,
          sourceCount: d.source_count,
          memoryCount: d.result_count,
          activityId: d.activity_id,
          sourceId: source?.node_id,
          updatedAt: now,
        });

        if (payload.event_type === "research.started") {
          setSources((prev) => prev.map((s) => ({ ...s, recalled: false })));
        }

        if (payload.event_type === "memory.retrieved" && Array.isArray(d.nodes)) {
          setSources((prev) => {
            const next = new Map(prev.map((s) => [s.id, { ...s, recalled: false }]));
            for (const item of d.nodes) {
              if (!item?.node_id) continue;
              next.set(item.node_id, {
                id: item.node_id,
                title: item.domain || "Recalled source",
                domain: item.domain || "",
                url: "",
                state: "stored",
                recalled: true,
              });
            }
            return Array.from(next.values()).slice(-12);
          });
        }

        if (source?.node_id) {
          setSources((prev) => {
            const next = new Map(prev.map((s) => [s.id, s]));
            next.set(source.node_id, {
              id: source.node_id,
              title: source.title || source.domain || "Source",
              domain: source.domain || "",
              url: source.url || "",
              state: nodeState,
            });
            return Array.from(next.values()).slice(-12);
          });
        }

        if (payload.event_type === "knowledge.connected" && d.from_node && d.to_node) {
          setConnections((prev) => [
            ...prev.filter((c) => !(c.from === d.from_node && c.to === d.to_node)),
            { from: d.from_node, to: d.to_node },
          ].slice(-20));
        }

        // Keep the completed trace visible until the next user query.
      } catch {}
    };

    // The Next dev rewrite proxy buffers infinite SSE streams. Poll a finite
    // activity snapshot instead; the backend stream remains available for
    // production clients that connect directly.
    let cursor = new Date(Date.now() - 5 * 60_000).toISOString();
    const poll = async () => {
      try {
        const res = await fetch(`/api/v1/interface/activity`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ since: cursor }),
          signal: controller.signal,
        });
        if (!res.ok) return;
        const data = await res.json();
        for (const item of data.events || []) {
          handle(JSON.stringify(item));
          if (item.created_at) cursor = item.created_at;
        }
      } catch {}
    };
    poll();
    const timer = window.setInterval(poll, 2000);

    return () => {
      window.clearInterval(timer);
      controller.abort();
    };
  }, []);

  // Persistent knowledge graph — verified public clusters and discovered links.
  React.useEffect(() => {
    let live = true;
    const load = async () => {
      try {
        const [c, g, f, m] = await Promise.all([
          api.get("/api/v1/interface/clusters"),
          api.get("/api/v1/interface/connections"),
          api.get("/api/v1/interface/freshness"),
          api.get("/api/v1/interface/map"),
        ]);
        if (!live) return;
        const savedLinks: KnowledgeConnection[] = g.data?.connections || [];
        setClusters(c.data?.clusters || []);
        setGraphConnections(savedLinks);
        setFreshness(f.data?.nodes || {});
        setMapPlaces(m.data?.places || []);

        // Rebuild source dots from persisted links so the graph survives
        // activity events ageing out of the recent-event window.
        const savedNodes = new Map<string, SourceNode>();
        for (const link of savedLinks) {
          if (link.from_node && link.from_cluster) {
            savedNodes.set(link.from_node, {
              id: link.from_node,
              title: link.from_cluster,
              domain: link.from_cluster,
              url: "",
              state: "stored",
            });
          }
          if (link.to_node && link.to_cluster) {
            savedNodes.set(link.to_node, {
              id: link.to_node,
              title: link.to_cluster,
              domain: link.to_cluster,
              url: "",
              state: "stored",
            });
          }
        }
        if (savedNodes.size) {
          setSources((prev) => {
            const merged = new Map(prev.map((s) => [s.id, s]));
            savedNodes.forEach((node, id) => { if (!merged.has(id)) merged.set(id, node); });
            return Array.from(merged.values()).slice(-12);
          });
        }
      } catch {}
    };
    load();
    return () => { live = false; };
  }, []);

  React.useEffect(() => () => {
    timersRef.current.forEach((t) => window.clearTimeout(t));
    try { recognitionRef.current?.stop(); } catch {}
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
  }, []);

  // Initialize theme
  React.useEffect(() => {
    const stored = (typeof localStorage !== "undefined" && localStorage.getItem("iam_theme")) as "dark" | "light" | null;
    const initial = stored === "dark" ? "dark" : "light";
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
        const restoredMode: Mode = stored.mode || "focus";
        setSession(stored);
        setMode(restoredMode);
        setStatus(MODE_CONFIG[restoredMode].status);
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
  }, [loadNodes, loadSuggestions, mode, session?.session_token]);

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

  // Vision/document analysis — runs inside the same interface, no separate page.
  const handleAttachment = async (file: File) => {
    setAttachment(file);
    setResponse("");
    setResponseMinimized(false);
    setResponseDismissed(false);
    setShowHistory(false);
    setState("thinking");
    setStatus("Analysing…");
    setGenerating(true);
    try {
      const form = new FormData();
      const isImage = file.type.startsWith("image/");
      form.append(isImage ? "image" : "video", file);
      const url = isImage ? "/api/v1/vision/understand-image" : "/api/v1/vision/analyze-video";
      const base = (typeof window !== "undefined" && (window as any).__NEXT_PUBLIC_API_URL) || "";
      const res = await fetch(base + url, { method: "POST", body: form });
      const data = await res.json();
      const text = data.description || data.error || "Could not analyse the file.";
      setResponse(text);
      setMessages((prev) => [
        ...prev,
        { role: "user", content: `[attachment: ${file.name}]` },
        { role: "assistant", content: text },
      ]);
      if (res.ok && !text.startsWith("Could not")) speak(text);
    } catch {
      setResponse("I could not read that file. Try an image or video.");
    } finally {
      setGenerating(false);
      setAttachment(null);
      const t = window.setTimeout(() => { setState("idle"); setStatus(MODE_CONFIG[mode].status); }, 1200);
      timersRef.current.push(t);
    }
  };

  const loadProvenance = async (cluster: string) => {
    setProvenanceLoading(true);
    setSelectedSource(null);
    try {
      const res = await api.get("/api/v1/interface/provenance", { params: { cluster } });
      setProvenance(res.data as ProvenanceResponse);
    } catch {
      setProvenance({ cluster, items: [], claim: "provenance_unavailable" });
    } finally {
      setProvenanceLoading(false);
    }
  };

  const stopGeneration = () => {
    abortRef.current?.abort();
    timersRef.current.forEach((t) => window.clearTimeout(t));
    timersRef.current = [];
    window.speechSynthesis?.cancel();
    setGenerating(false);
    setState("idle");
  };

  const ask = async (query: string) => {
    query = query.trim();
    if (!query || generating) return;
    setInput("");
    setResponse("");
    setResponseMinimized(false);
    setResponseDismissed(false);
    setLastInference(null);
    setActivity(null);
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

    // Real SSE streaming from the backend. Stay in "thinking" until the
    // backend emits start/first token so the sphere reflects reality.
    let answer = "";
    try {
      const base = (typeof window !== "undefined" && (window as any).__NEXT_PUBLIC_API_URL) || "";
      const res = await fetch(`${base}/api/v1/models/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            { role: "system", content: cfg.systemPrompt },
            ...historyMessages,
          ],
          temperature: mode === "create" ? 0.8 : 0.6,
          // Recall mode opts into IAM's permission-controlled memory layer.
          include_memory: mode === "recall",
          // OD-51 sphere control: manual selects a free specialist; auto leaves
          // model choice to IAM; hybrid keeps the local primary and consults an
          // authorised specialist through IAM's delegation workflow.
          ...(modelMode === "manual" && selectedModel ? { model: selectedModel } : {}),
          ...(modelMode === "hybrid" ? { delegate: true } : {}),
        }),
        signal: abortRef.current?.signal,
      });

      if (!res.ok || !res.body) throw new Error(`stream status ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() || "";
        for (const frame of frames) {
          let event = "message", dataStr = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) dataStr += line.slice(5).trim();
          }
          if (!dataStr) continue;
          let data: any;
          try { data = JSON.parse(dataStr); } catch { continue; }

          if (event === "start") {
            setState("speaking");
            setStatus("Speaking");
            if (data.mode && data.model) {
              if (lastInference && lastInference.model !== data.model) {
                setPreviousModel(lastInference.model);
              }
              setLastInference({ mode: data.mode, model: data.model });
            }
            if (data.delegation) {
              const tasks = Array.isArray(data.delegation.tasks) ? data.delegation.tasks : null;
              setDelegations(
                tasks
                  ? tasks.map((task: any) => ({
                      model: String(task.delegate_model || "specialist"),
                      status: String(task.status || "unknown"),
                    }))
                  : [
                      {
                        model: String(data.delegation.delegate_model || "specialist"),
                        status: String(data.delegation.status || "unknown"),
                      },
                    ],
              );
            }
          } else if (event === "delta") {
            full += data.text || "";
            setResponse(full);
          } else if (event === "error") {
            full += (full ? "\n\n" : "") + (data.message || "stream error");
            setResponse(full);
          } else if (event === "done") {
            // finished
          }
        }
      }
      answer = full || "I could not generate a response.";
    } catch (err) {
      // User-initiated Stop is not an outage — do not record it as an answer.
      if ((err as DOMException)?.name === "AbortError" || abortRef.current?.signal.aborted) {
        return;
      }
      answer = "I'm unable to reach the model gateway right now. Please check the backend connection and try again.";
      setResponse(answer);
    }

    setMessages((prev) => [...prev, { role: "assistant", content: answer }]);
    if (activeSession) {
      api.post("/api/v1/access/messages", {
        session_token: activeSession.session_token,
        role: "assistant",
        content: answer,
        mode,
      }).catch(() => {});
    }

    if (answer && !answer.startsWith("I'm unable")) speak(answer);
    setGenerating(false);
    const doneTimer = window.setTimeout(() => {
      setState("idle");
      setStatus(MODE_CONFIG[mode].status);
    }, 900);
    timersRef.current.push(doneTimer);
  };

  const toggleMic = () => {
    const on = !listening;
    setListening(on);
    setState(on ? "listening" : "idle");
    setStatus(on ? "Listening…" : MODE_CONFIG[mode].status);

    if (!on) {
      try { recognitionRef.current?.stop(); } catch {}
      recognitionRef.current = null;
      return;
    }

    if (typeof window !== "undefined" && "webkitSpeechRecognition" in window) {
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
      <PresenceSphere
        state={state}
        mode={mode}
        nodes={nodes}
        activity={activity}
        sourceNodes={sources}
        connections={allConnections}
        clusters={clusters}
        graphConnections={graphConnections}
        freshness={freshness}
        mapMode={mapMode}
        mapPlaces={mapPlaces}
        onNodeHover={(node, x, y) => {
          const id = node?.id ?? null;
          if (id && id === lastHoverRef.current) return;
          lastHoverRef.current = id;
          setHoveredSource(node && x !== undefined && y !== undefined ? { node, x, y } : null);
        }}
        onNodeSelect={(node) => {
          if (node.kind === "cluster" && node.clusterName) void loadProvenance(node.clusterName);
          else setSelectedSource(node);
        }}
      />

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

      {/* Live intelligence activity — driven by real IAM events */}
      {activity && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 rounded-full border border-[var(--line)] px-3 py-1.5 text-[11px] backdrop-blur-xl pointer-events-none"
          style={{ background: "var(--glass)", color: "var(--mute)" }}>
          <span className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ background: "var(--accent)" }} />
          <span className="uppercase tracking-wider opacity-60">Live activity</span>
          <span>{activity.label || "Working"}</span>
          {typeof activity.sourceCount === "number" && (
            <span className="opacity-60">{activity.sourceCount} sources</span>
          )}
          {typeof activity.memoryCount === "number" && (
            <span className="opacity-60">{activity.memoryCount} memories</span>
          )}
        </div>
      )}

      {/* Source node detail — stays on the same screen */}
      {(selectedSource || hoveredSource) && (() => {
        const node = selectedSource || hoveredSource!.node;
        const x = Math.min(hoveredSource?.x ?? window.innerWidth / 2, window.innerWidth - 280);
        const y = Math.min(hoveredSource?.y ?? 180, window.innerHeight - 220);
        return (
          <div className="fixed z-30 w-[250px] rounded-2xl border border-[var(--line)] p-3 backdrop-blur-2xl pointer-events-auto"
            style={{ background: "var(--glass)", left: Math.max(12, x + 16), top: Math.max(80, y + 12) }}>
            <div className="flex items-start justify-between gap-2 mb-2">
              <p className="text-xs font-medium leading-snug">{node.title}</p>
              {selectedSource && (
                <button onClick={() => setSelectedSource(null)} aria-label="Close source details" className="opacity-50 hover:opacity-100">
                  <X size={13} />
                </button>
              )}
            </div>
            <p className="text-[10px] uppercase tracking-wider opacity-50 mb-2">{node.domain}</p>
            <div className="flex items-center gap-2 text-[10px] opacity-70">
              <span className="rounded-full border border-[var(--line)] px-2 py-0.5 capitalize">
                {node.kind === "cluster" ? "cluster" : node.recalled ? "recalled" : node.state}
              </span>
              <span>{node.kind === "cluster" ? "Verified knowledge" : "Public research"}</span>
            </div>
            {node.freshnessLabel ? (
              <p className="mt-2 text-[10px] opacity-60">{node.freshnessLabel}</p>
            ) : null}
            {node.url ? (
              <a href={node.url} target="_blank" rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-[11px] opacity-70 hover:opacity-100">
                Open source <ArrowRight size={11} />
              </a>
            ) : null}
            {node.kind === "cluster" && node.clusterName ? (
              <button onClick={() => void loadProvenance(node.clusterName!)}
                className="mt-2 inline-flex items-center gap-1 text-[11px] opacity-70 hover:opacity-100">
                View provenance <ArrowRight size={11} />
              </button>
            ) : null}
            <p className="mt-2 text-[9px] leading-relaxed opacity-40">
              Provenance only. Public sources are not automatically trusted facts.
            </p>
          </div>
        );
      })()}

      {/* Provenance path — sources behind a clicked cluster */}
      {provenance && (
        <div className="fixed left-4 right-4 top-28 z-30 w-auto max-h-[55vh] overflow-y-auto rounded-2xl border border-[var(--line)] p-4 backdrop-blur-2xl pointer-events-auto md:left-24 md:right-auto md:w-[330px]"
          style={{ background: "var(--glass)" }}>
          <div className="flex items-start justify-between gap-2 mb-3">
            <div>
              <h2 className="text-sm font-medium">Provenance</h2>
              <p className="text-[10px] uppercase tracking-wider opacity-50">{provenance.cluster}</p>
            </div>
            <button onClick={() => setProvenance(null)} aria-label="Close provenance" className="opacity-50 hover:opacity-100">
              <X size={14} />
            </button>
          </div>
          {provenanceLoading ? (
            <p className="text-xs opacity-60">Tracing sources…</p>
          ) : provenance.items.length === 0 ? (
            <p className="text-xs opacity-60 leading-relaxed">
              No verified public records are attached to this cluster yet.
            </p>
          ) : (
            <div className="space-y-3">
              {provenance.items.map((item, i) => (
                <div key={i} className="rounded-xl border border-[var(--line)] p-2.5 text-xs"
                  style={{ background: "rgba(255,255,255,.035)" }}>
                  <div className="flex justify-between gap-2">
                    <span className="font-medium leading-snug">{item.title}</span>
                    <span className="opacity-50">{Math.round(item.confidence * 100)}%</span>
                  </div>
                  <p className="mt-1 opacity-60 leading-snug">{item.summary}</p>
                  <div className="mt-2 space-y-1">
                    {item.sources.map((source, j) => (
                      <div key={j} className="flex items-center gap-2 text-[11px]">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: "var(--accent)" }} />
                        {source.url ? (
                          <a href={source.url} target="_blank" rel="noopener noreferrer"
                            className="truncate opacity-70 hover:opacity-100">
                            {source.title} · {source.domain}
                          </a>
                        ) : (
                          <span className="opacity-60">{source.title}</span>
                        )}
                        {source.node_id && freshness[source.node_id] ? (
                          <span className="rounded-full border border-[var(--line)] px-1.5 py-0.5 text-[9px] capitalize"
                            style={{ color: freshness[source.node_id].state === "contradicted" ? "#f87171" : undefined }}>
                            {freshness[source.node_id].state.replace("_", " ")}
                          </span>
                        ) : null}
                        <span className="ml-auto opacity-40">{Math.round(source.credibility * 100)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <p className="mt-3 text-[9px] leading-relaxed opacity-40">
            Provenance only. Sources are not automatically trusted facts.
          </p>
        </div>
      )}

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
          onClick={() => setShowOptions(!showOptions)}
          aria-label="IAM options"
          aria-pressed={showOptions}
          className="w-10 h-10 rounded-full border border-[var(--line)] backdrop-blur-xl grid place-items-center transition-colors hover:border-[var(--accent)]"
          style={{ background: showOptions ? "var(--accent)" : "var(--glass)", color: showOptions ? "var(--bg2)" : undefined }}
        >
          {showOptions ? <X size={16} /> : <Settings2 size={16} />}
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

      {/* In-screen options — no extra pages, no navigation */}
      {showOptions && (
        <div className="fixed right-20 top-24 z-20 w-[min(340px,calc(100vw-120px))] rounded-2xl border border-[var(--line)] backdrop-blur-2xl p-4 pointer-events-auto"
          style={{ background: "var(--glass)" }}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[var(--mute)]">IAM options</h2>
            <button onClick={() => setShowOptions(false)} aria-label="Close options" className="opacity-60 hover:opacity-100">
              <X size={15} />
            </button>
          </div>

          <div className="flex items-center gap-2 rounded-xl border border-[var(--line)] px-3 py-2 mb-3 text-xs"
            style={{ background: "rgba(255,255,255,.04)" }}>
            <Activity size={13} />
            <span className="opacity-70">Inference</span>
            <span className="ml-auto capitalize">
              {inference ? `${inference.mode}${inference.model ? ` · ${inference.model}` : ""}` : "checking…"}
            </span>
          </div>
          <div className="flex items-center justify-between text-[10px] opacity-50 mb-1">
            <span>Active model</span>
            <span className="truncate ml-2 capitalize">{lastInference?.model || inference?.model || "local primary"}</span>
          </div>
          <div className="flex items-center justify-between text-[10px] opacity-50 mb-3">
            <span>Previous</span>
            <span className="truncate ml-2 capitalize">{previousModel || "none"}</span>
          </div>

          <p className="text-[10px] uppercase tracking-wider opacity-50 mb-2 text-[var(--mute)]">Model mode</p>
          <div className="grid grid-cols-3 gap-2 mb-3">
            {(["manual", "auto", "hybrid"] as const).map((choice) => (
              <button key={choice} onClick={() => setModelMode(choice)}
                aria-pressed={modelMode === choice}
                title={
                  choice === "manual" ? "Choose a free specialist model" :
                  choice === "auto" ? "IAM chooses the model" :
                  "Local primary with an authorised specialist"
                }
                className="rounded-lg border px-1 py-2 text-[10px] transition-colors capitalize"
                style={{
                  borderColor: modelMode === choice ? "var(--accent)" : "var(--line)",
                  background: modelMode === choice ? "rgba(143,166,255,.16)" : "transparent",
                }}>
                {choice}
              </button>
            ))}
          </div>

          {modelMode === "manual" && (
            <div className="mb-3 max-h-28 overflow-y-auto rounded-xl border border-[var(--line)] px-2 py-1.5 text-[10px] space-y-1"
              style={{ background: "rgba(255,255,255,.035)" }}>
              <div className="opacity-60">Free models only · paid access needs signed approval</div>
              {freeModels.length === 0 && <div className="opacity-50">No free models discovered yet.</div>}
              {freeModels.map((item) => (
                <button key={item.model_id}
                  onClick={() => setSelectedModel(item.model_id)}
                  aria-pressed={selectedModel === item.model_id}
                  className="w-full flex justify-between gap-2 text-left hover:opacity-100 opacity-80">
                  <span className="truncate">{item.display_name || item.model_id}</span>
                  <span className="opacity-50">{selectedModel === item.model_id ? "selected" : "free"}</span>
                </button>
              ))}
            </div>
          )}

          <p className="text-[10px] uppercase tracking-wider opacity-50 mb-2 text-[var(--mute)]">Connections</p>
          <div className="mb-3 max-h-24 overflow-y-auto rounded-xl border border-[var(--line)] px-2 py-1.5 text-[10px] space-y-1"
            style={{ background: "rgba(255,255,255,.035)" }}>
            {providerKeys.length === 0 && <div className="opacity-50">No provider keys registered.</div>}
            {providerKeys.map((key) => (
              <div key={`${key.provider}-${key.key_alias}`} className="flex justify-between gap-2">
                <span className="truncate">{key.provider} · {key.key_alias}</span>
                <span className="opacity-60">{key.is_enabled ? key.health : "disabled"}</span>
              </div>
            ))}
          </div>

          {delegations.length > 0 && (
            <>
              <p className="text-[10px] uppercase tracking-wider opacity-50 mb-2 text-[var(--mute)]">Delegated tasks</p>
              <div className="mb-4 max-h-24 overflow-y-auto rounded-xl border border-[var(--line)] px-2 py-1.5 text-[10px] space-y-1"
                style={{ background: "rgba(255,255,255,.035)" }}>
                {delegations.map((task, index) => (
                  <div key={`${task.model}-${index}`} className="flex justify-between gap-2">
                    <span className="truncate">{task.model}</span>
                    <span className="opacity-60 capitalize">{task.status}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          <p className="text-[10px] uppercase tracking-wider opacity-50 mb-2 text-[var(--mute)]">
            Knowledge graph
          </p>
          <div className="mb-3 max-h-32 overflow-y-auto rounded-xl border border-[var(--line)] px-2 py-1.5 text-[10px] space-y-1"
            style={{ background: "rgba(255,255,255,.035)" }}>
            <div className="opacity-60">{clusters.length} clusters · {graphConnections.length + connections.length} links</div>
            {clusters.slice(0, 6).map((c) => (
              <button key={c.node_id} onClick={() => { void loadProvenance(c.name); setShowOptions(false); }}
                aria-label={`Inspect ${c.name} provenance`}
                className="w-full flex justify-between gap-2 text-left hover:opacity-100 opacity-80">
                <span className="truncate">{c.name}</span>
                <span className="opacity-50">{c.count}</span>
              </button>
            ))}
            {sources.slice(0, 6).map((source) => (
              <button key={source.id} onClick={() => { setSelectedSource(source); setShowOptions(false); }}
                aria-label={`Inspect source ${source.domain || source.title}`}
                className="w-full truncate text-left opacity-60 hover:opacity-100">
                · {source.domain || source.title}
              </button>
            ))}
            {graphConnections.slice(0, 4).map((link, i) => (
              <div key={link.id || i} className="truncate opacity-60">
                {link.from_cluster || link.from} → {link.to_cluster || link.to}
              </div>
            ))}
          </div>

          <button onClick={() => { setMapMode(!mapMode); setShowOptions(false); }}
            className="w-full mb-3 rounded-lg border border-[var(--line)] px-3 py-2 text-xs flex items-center justify-center gap-2 hover:border-[var(--accent)] transition-colors">
            {mapMode ? "Return to intelligence sphere" : "Open geospatial view"}
          </button>

          {clusters[0] ? (
            <button onClick={() => { void loadProvenance(clusters[0].name); setShowOptions(false); }}
              className="w-full mb-3 rounded-lg border border-[var(--line)] px-3 py-2 text-xs flex items-center justify-center gap-2 hover:border-[var(--accent)] transition-colors">
              Inspect {clusters[0].name} provenance <ArrowRight size={12} />
            </button>
          ) : null}

          <button
            onClick={() => { setMessages([]); setResponse(""); setLastQuery(""); setShowOptions(false); }}
            className="w-full rounded-lg border border-[var(--line)] px-3 py-2 text-xs flex items-center gap-2 justify-center hover:border-[var(--accent)] transition-colors"
          >
            <Trash2 size={13} /> Clear this conversation view
          </button>
          <p className="mt-3 text-[10px] leading-relaxed opacity-50 text-[var(--mute)]">
            Everything stays on this one screen. Responses are formatted, scrollable and copyable.
          </p>
        </div>
      )}

      {/* Center response + input */}
      <div className="fixed inset-x-0 bottom-0 z-10 flex flex-col items-center gap-4 px-4 pb-6 pointer-events-none">
        <span className="sr-only" aria-live="polite">
          {generating ? "IAM is responding" : response && !responseDismissed ? "Response ready" : ""}
        </span>
        {!responseDismissed && (
          <div
            className={`say w-full max-w-[720px] leading-relaxed min-h-[1.5em] transition-opacity duration-300 overflow-y-auto pointer-events-auto ${
              compactResponse ? "text-center" : "rounded-2xl border border-[var(--line)] p-4 text-left"
            }`}
            style={{
              fontSize: compactResponse ? "clamp(19px, 2.6vw, 25px)" : "clamp(14px, 1.35vw, 16px)",
              fontWeight: compactResponse ? 300 : 400,
              opacity: response ? 1 : 0,
              maxHeight: responseMinimized ? "auto" : compactResponse ? "30vh" : "42vh",
              background: compactResponse ? undefined : "var(--glass)",
              backdropFilter: compactResponse ? undefined : "blur(18px)",
            }}
            >
            {response && !compactResponse && !responseMinimized ? (
              <div className="flex justify-end gap-1.5 mb-2">
                <button
                  onClick={() => setResponseMinimized(true)}
                  aria-label="Minimize response"
                  className="w-6 h-6 rounded-full border border-[var(--line)] grid place-items-center opacity-50 hover:opacity-100"
                >
                  <Minus size={12} />
                </button>
                <button
                  onClick={() => setResponseDismissed(true)}
                  aria-label="Close response"
                  className="w-6 h-6 rounded-full border border-[var(--line)] grid place-items-center opacity-50 hover:opacity-100"
                >
                  <X size={12} />
                </button>
              </div>
            ) : null}
            {responseMinimized ? (
              <button
                onClick={() => setResponseMinimized(false)}
                aria-label="Expand response"
                className="w-full flex items-center gap-2 text-left opacity-70 hover:opacity-100"
                style={{ fontSize: 13 }}
              >
                <ChevronDown size={13} className="rotate-180 shrink-0" />
                <span className="truncate">{response.slice(0, 90)}{response.length > 90 ? "…" : ""}</span>
              </button>
            ) : (
              <>
                {response ? <FormattedResponse text={response} /> : null}
                {generating && <span className="ml-0.5 animate-pulse opacity-70">▍</span>}
              </>
            )}
          </div>
        )}

        {(generating || (response && !generating && !responseDismissed)) && (
          <div className="flex flex-wrap justify-center gap-2 pointer-events-auto">
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
            {!generating && response && !responseMinimized && (
              <>
                <button
                  onClick={async () => {
                    try { await navigator.clipboard.writeText(response); setCopied(true); timersRef.current.push(window.setTimeout(() => setCopied(false), 1500)); } catch {}
                  }}
                  aria-label="Copy response"
                  className="px-3 py-1.5 rounded-full text-xs border border-[var(--line)] backdrop-blur-md hover:border-[var(--accent)] transition flex items-center gap-1.5"
                  style={{ background: "var(--glass)", color: "var(--mute)" }}
                >
                  <Copy size={12} /> {copied ? "Copied" : "Copy"}
                </button>
                <button
                  onClick={() => ask("Explain that last answer more simply.")}
                  aria-label="Simplify response"
                  className="px-3 py-1.5 rounded-full text-xs border border-[var(--line)] backdrop-blur-md hover:border-[var(--accent)] transition flex items-center gap-1.5"
                  style={{ background: "var(--glass)", color: "var(--mute)" }}
                >
                  <Wand2 size={12} /> Simplify
                </button>
                <button
                  onClick={() => ask(lastQuery)}
                  aria-label="Retry"
                  className="px-3 py-1.5 rounded-full text-xs border border-[var(--line)] backdrop-blur-md hover:border-[var(--accent)] transition flex items-center gap-1.5"
                  style={{ background: "var(--glass)", color: "var(--mute)" }}
                >
                  <RotateCcw size={12} /> Retry
                </button>
                {lastInference ? (
                  <span className="px-2.5 py-1.5 rounded-full text-[10px] border border-[var(--line)] opacity-60 capitalize"
                    title="Actual model used for this response">
                    {lastInference.mode} · {lastInference.model}
                  </span>
                ) : null}
              </>
            )}
          </div>
        )}

        {(!response || responseDismissed) && (
          <div className="ghost flex gap-2 flex-wrap justify-center pointer-events-auto">
            {suggestions.map((s) => (
              <button
                key={s}
                disabled={generating}
                onClick={() => ask(s)}
                className="px-3.5 py-1.5 rounded-full text-[13px] border border-[var(--line)] backdrop-blur-md transition-colors hover:border-[var(--accent)] disabled:opacity-40 disabled:pointer-events-none"
                style={{ background: "var(--glass)", color: "var(--mute)" }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); ask(input); }}
          className="bar pointer-events-auto group w-full max-w-[600px] flex items-center gap-2 py-2 pl-5 pr-2 rounded-[22px] border border-[var(--line)] backdrop-blur-2xl shadow-[0_12px_40px_-18px_rgba(0,0,0,.55)] ring-1 ring-white/5 transition-all duration-300 focus-within:border-[var(--accent)] focus-within:shadow-[0_0_0_3px_rgba(143,166,255,.14)]"
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
            className="flex-1 min-w-0 bg-transparent border-0 outline-none py-2 text-[15px] tracking-wide caret-[var(--accent)] placeholder:opacity-40"
            style={{ color: "var(--ink)" }}
          />
          <input
            ref={fileRef}
            type="file"
            accept="image/*,video/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleAttachment(f);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            aria-label="Attach image or video"
            className="w-9 h-9 rounded-full border grid place-items-center opacity-60 transition-all duration-200 hover:opacity-100 hover:border-[var(--accent)] hover:bg-white/5 active:scale-95"
            style={{ borderColor: "var(--line)" }}
          >
            <Paperclip size={16} />
          </button>
          <button
            type="button"
            onClick={toggleMic}
            aria-pressed={listening}
            aria-label="Listen"
            className={`w-[42px] h-[42px] rounded-full border grid place-items-center transition-all duration-200 active:scale-95 ${
              listening ? "shadow-[0_0_0_4px_rgba(143,166,255,.18)] animate-pulse" : "opacity-60 hover:opacity-100 hover:bg-white/5"
            }`}
            style={listening
              ? { background: "var(--accent)", color: "var(--bg2)", borderColor: "transparent" }
              : { borderColor: "var(--line)" }}
          >
            <Mic size={18} />
          </button>
          <button
            type="submit"
            disabled={!input.trim() && !listening}
            aria-label="Send"
            className="w-[42px] h-[42px] rounded-full grid place-items-center border-0 transition-all duration-200 hover:scale-[1.05] active:scale-95 disabled:opacity-30 disabled:pointer-events-none"
            style={{ background: "var(--ink)", color: "var(--bg2)", boxShadow: "0 8px 22px -10px var(--accent)" }}
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
