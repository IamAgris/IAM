"use client";

import React from "react";

export type IAMState = "idle" | "listening" | "thinking" | "speaking" | "working";

export interface MemoryNode {
  text: string;
  hit?: boolean;
}

export interface SourceNode {
  id: string;
  title: string;
  domain: string;
  url: string;
  state: "discovered" | "opened" | "extracted" | "stored";
  recalled?: boolean;
  kind?: "source" | "cluster";
  clusterName?: string;
  freshnessState?: string;
  freshnessLabel?: string;
  credibility?: number;
}

export interface KnowledgeConnection {
  id?: string;
  from: string;
  to: string;
  from_cluster?: string | null;
  to_cluster?: string | null;
  relation?: string;
  label?: string;
  created_at?: string;
}

export interface KnowledgeCluster {
  name: string;
  count: number;
  node_id: string;
}

export interface FreshnessInfo {
  state: "current" | "needs_review" | "stale" | "historical" | "unverified" | "contradicted";
  label: string;
  confidence: number;
  last_checked_at: string | null;
}

export interface SphereActivity {
  event_type: string;
  label?: string;
  sourceCount?: number;
  memoryCount?: number;
  activityId?: string;
  sourceId?: string;
  updatedAt: number;
}

interface Props {
  state: IAMState;
  mode: "focus" | "recall" | "create";
  nodes: MemoryNode[];
  activity?: SphereActivity | null;
  sourceNodes?: SourceNode[];
  connections?: KnowledgeConnection[];
  clusters?: KnowledgeCluster[];
  graphConnections?: KnowledgeConnection[];
  freshness?: Record<string, FreshnessInfo>;
  onNodeHover?: (node: SourceNode | null, x?: number, y?: number) => void;
  onNodeSelect?: (node: SourceNode) => void;
}

const MODE_HUE: Record<string, number> = { focus: 215, recall: 280, create: 28 };

const STATE_TARGETS: Record<IAMState, Record<string, number>> = {
  idle: { amp: 0.03, spd: 0.15, rad: 1, glow: 0.35, wf: 1.2 },
  listening: { amp: 0.09, spd: 0.35, rad: 1.1, glow: 0.7, wf: 3 },
  thinking: { amp: 0.05, spd: 1.3, rad: 0.82, glow: 1, wf: 6 },
  speaking: { amp: 0.075, spd: 0.3, rad: 1.04, glow: 0.8, wf: 4 },
  working: { amp: 0.06, spd: 0.6, rad: 0.95, glow: 0.9, wf: 4.5 },
};

export function PresenceSphere({
  state,
  mode,
  nodes,
  activity,
  sourceNodes = [],
  connections = [],
  clusters = [],
  graphConnections = [],
  freshness = {},
  onNodeHover,
  onNodeSelect,
}: Props) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const stateRef = React.useRef(state);
  const modeRef = React.useRef(mode);
  const nodesRef = React.useRef(nodes);
  const activityRef = React.useRef(activity ?? null);
  const sourcesRef = React.useRef(sourceNodes);
  const connectionsRef = React.useRef(connections);
  const clustersRef = React.useRef(clusters);
  const graphRef = React.useRef(graphConnections);
  const freshnessRef = React.useRef(freshness);
  const hoverRef = React.useRef(onNodeHover);
  const selectRef = React.useRef(onNodeSelect);
  const hitRef = React.useRef<Array<SourceNode & { x: number; y: number }>>([]);

  React.useEffect(() => { stateRef.current = state; }, [state]);
  React.useEffect(() => { modeRef.current = mode; }, [mode]);
  React.useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  React.useEffect(() => { activityRef.current = activity ?? null; }, [activity]);
  React.useEffect(() => { sourcesRef.current = sourceNodes; }, [sourceNodes]);
  React.useEffect(() => { connectionsRef.current = connections; }, [connections]);
  React.useEffect(() => { clustersRef.current = clusters; }, [clusters]);
  React.useEffect(() => { graphRef.current = graphConnections; }, [graphConnections]);
  React.useEffect(() => { freshnessRef.current = freshness; }, [freshness]);
  React.useEffect(() => { hoverRef.current = onNodeHover; }, [onNodeHover]);
  React.useEffect(() => { selectRef.current = onNodeSelect; }, [onNodeSelect]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let W = 0, H = 0, cx = 0, cy = 0, R = 0;
    let mx = 0, my = 0;
    let raf = 0;
    let last = 0;
    let rot = 0;
    let hue = MODE_HUE[modeRef.current] ?? 215;
    let hueT = hue;

    const cur: Record<string, number> = { ...STATE_TARGETS.idle };

    const isDark = () => {
      const t = document.documentElement.dataset.theme;
      return t ? t === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    };

    const size = () => {
      const d = Math.min(window.devicePixelRatio || 1, 2);
      W = window.innerWidth;
      H = window.innerHeight;
      canvas.width = W * d;
      canvas.height = H * d;
      ctx.setTransform(d, 0, 0, d, 0, 0);
      cx = W / 2;
      cy = H * 0.4;
      R = Math.min(W * 0.9, H * 0.62) * 0.27;
    };

    const onResize = () => size();
    const onPointer = (e: PointerEvent) => {
      mx = e.clientX / W - 0.5;
      my = e.clientY / H - 0.5;
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onPointer);
    size();

    // Particle sphere (Fibonacci distribution)
    const N = 1100;
    const P: { x: number; y: number; z: number; s: number }[] = [];
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = i * 2.39996;
      P.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r, s: Math.random() });
    }

    const orbitalNodes = nodesRef.current.map((n, i) => ({
      ...n,
      a: (i / Math.max(nodesRef.current.length, 1)) * Math.PI * 2,
      r: 1.6 + (i % 3) * 0.15,
      sp: (i % 2 === 0 ? 0.08 : -0.07),
      g: 0,
    }));

    // Live research source nodes — keyed by node id so updates never rebuild
    // the particle sphere or restart the animation loop.
    const sourceStates: Record<string, { a: number; r: number; g: number; x: number; y: number }> = {};
    const clusterPositions: Record<string, { x: number; y: number }> = {};

    const frame = (ts: number) => {
      const t = ts * 0.001;
      const dt = Math.min(t - last, 0.05);
      last = t;
      // Reduced motion: keep the sphere visible and informative, but still.
      const animT = reducedMotion ? 0 : t;

      const st = stateRef.current;
      const target = STATE_TARGETS[st] ?? STATE_TARGETS.idle;
      for (const k in target) cur[k] += (target[k] - cur[k]) * Math.min(1, dt * 3);

      hueT = MODE_HUE[modeRef.current] ?? 215;
      hue += (hueT - hue) * Math.min(1, dt * 2.5);
      if (!reducedMotion) rot += dt * cur.spd;

      const D = isDark();
      const L = D ? 66 : 42;
      const cr = Math.cos(rot), sr = Math.sin(rot);
      const tilt = 0.35 + my * 0.4, ct = Math.cos(tilt), st2 = Math.sin(tilt);

      ctx.clearRect(0, 0, W, H);
      const ox = cx + mx * 30, oy = cy + my * 20;

      // Core glow
      const gr = ctx.createRadialGradient(ox, oy, 0, ox, oy, R * 1.9 * cur.rad);
      gr.addColorStop(0, `hsla(${hue},90%,${D ? 60 : 70}%,${0.22 * cur.glow})`);
      gr.addColorStop(1, `hsla(${hue},90%,60%,0)`);
      ctx.fillStyle = gr;
      ctx.fillRect(0, 0, W, H);

      // Orbit rings
      ctx.strokeStyle = `hsla(${hue},70%,${L}%,.14)`;
      ctx.lineWidth = 1;
      [1.6, 1.95].forEach((f) => {
        ctx.beginPath();
        ctx.ellipse(ox, oy, R * f, R * f * 0.42, 0, 0, 6.2832);
        ctx.stroke();
      });

      // Live research scan rings — outward when IAM is actively searching.
      const act = activityRef.current;
      const researching = act && act.event_type.startsWith("research.") && act.event_type !== "research.completed";
      if (researching && !reducedMotion) {
        const age = (Date.now() - act.updatedAt) / 1000;
        for (let k = 0; k < 3; k++) {
          const phase = ((age * 0.45 + k / 3) % 1);
          const alpha = (1 - phase) * 0.22;
          ctx.strokeStyle = `hsla(${hue},90%,${L}%,${alpha})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.ellipse(ox, oy, R * (1.05 + phase * 1.5), R * (1.05 + phase * 1.5) * 0.46, 0, 0, 6.2832);
          ctx.stroke();
        }
      }

      ctx.globalCompositeOperation = D ? "lighter" : "source-over";
      for (let i = 0; i < N; i++) {
        const p = P[i];
        const d = 1 + cur.amp * Math.sin(p.y * 5 + animT * cur.wf + p.s * 2.2)
          + (st === "listening" ? 0.04 * Math.sin(animT * 5 + p.s * 6) : 0);
        const x = p.x * cr - p.z * sr;
        const z0 = p.x * sr + p.z * cr;
        const y1 = p.y * ct - z0 * st2;
        const z = p.y * st2 + z0 * ct;
        const sc = (R * cur.rad * d) / (1 - z * 0.3);
        const a = (0.18 + 0.82 * (z + 1) / 2) * (D ? 0.9 : 0.8);
        ctx.fillStyle = `hsla(${hue + y1 * 45},92%,${L}%,${a})`;
        const s = 1 + (z + 1) * 0.7;
        ctx.fillRect(ox + x * sc, oy + y1 * sc, s, s);
      }
      ctx.globalCompositeOperation = "source-over";

      // Orbiting memory nodes
      const fs = W < 600 ? 11 : 13;
      ctx.font = `300 ${fs}px 'Space Grotesk', sans-serif`;
      orbitalNodes.forEach((n) => {
        const an = n.a + animT * n.sp;
        const x = ox + Math.cos(an) * R * n.r;
        const y = oy + Math.sin(an) * R * n.r * 0.42;
        const front = Math.sin(an) > 0;
        n.g += ((n.hit ? 1 : 0) - n.g) * Math.min(1, dt * 3);
        if (n.g > 0.02) {
          ctx.strokeStyle = `hsla(${hue},90%,${L}%,${0.7 * n.g})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.quadraticCurveTo((x + ox) / 2, (y + oy) / 2 - 30 * n.g, ox, oy);
          ctx.stroke();
        }
        ctx.fillStyle = `hsla(${hue},90%,${D ? 75 : 40}%,${0.5 + 0.5 * n.g})`;
        ctx.beginPath();
        ctx.arc(x, y, 3 + 4 * n.g, 0, 6.2832);
        ctx.fill();
        ctx.fillStyle = D ? `rgba(225,230,255,${0.28 + 0.7 * n.g})` : `rgba(20,26,58,${0.35 + 0.65 * n.g})`;
        ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
        if (front || n.g > 0.1) {
          ctx.fillText(n.text, x + (Math.cos(an) > 0 ? 12 : -12), y + 4);
        }
      });

      // Live source nodes from public research events.
      const sources = sourcesRef.current;
      hitRef.current = [];
      sources.forEach((s, i) => {
        if (!sourceStates[s.id]) {
          sourceStates[s.id] = {
            a: (i * 2.39996) % (Math.PI * 2),
            r: 1.35 + (i % 4) * 0.13,
            g: 0,
            x: 0,
            y: 0,
          };
        }
        const ss = sourceStates[s.id];
        const an = ss.a + animT * (i % 2 === 0 ? 0.05 : -0.045);
        ss.x = ox + Math.cos(an) * R * ss.r;
        ss.y = oy + Math.sin(an) * R * ss.r * 0.5;
        const fresh = freshnessRef.current[s.id];
        const fstate = fresh?.state;
        const nodeHue = fstate === "contradicted" ? 2
          : fstate === "unverified" || fstate === "needs_review" ? 38
          : fstate === "historical" || fstate === "stale" ? hue - 12
          : hue + (s.recalled ? 30 : 0);
        const freshnessWeight = fstate === "contradicted" ? 0.7
          : fstate === "historical" ? 0.4
          : fstate === "stale" ? 0.55
          : fstate === "needs_review" ? (reducedMotion ? 1 : 0.75 + 0.25 * Math.sin(t * 3))
          : 1;
        const targetGlow = (s.recalled ? 1.25
          : s.state === "stored" ? 1
          : s.state === "extracted" ? 0.85
          : s.state === "opened" ? 0.6 : 0.3) * freshnessWeight;
        ss.g += (targetGlow - ss.g) * Math.min(1, dt * 2);
        const front = Math.sin(an) > 0;

        if (s.recalled) {
          ctx.strokeStyle = `hsla(${hue + 25},95%,${L}%,0.22)`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(ss.x, ss.y);
          ctx.quadraticCurveTo((ss.x + ox) / 2, (ss.y + oy) / 2 - 12, ox, oy);
          ctx.stroke();
        }

        ctx.fillStyle = `hsla(${nodeHue},95%,${D ? 72 : 45}%,${Math.min(1, 0.35 + 0.65 * ss.g)})`;
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, 2.5 + 3.5 * ss.g, 0, 6.2832);
        ctx.fill();
        if (fstate === "contradicted") {
          ctx.strokeStyle = "hsla(2,90%,65%,0.75)";
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.arc(ss.x, ss.y, 8, 0.2, Math.PI - 0.2);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(ss.x, ss.y, 8, Math.PI + 0.2, 6.0832);
          ctx.stroke();
        } else if (fstate === "needs_review" || fstate === "unverified") {
          ctx.strokeStyle = `hsla(38,90%,65%,${reducedMotion ? 0.5 : 0.3 + 0.25 * Math.sin(t * 3)})`;
          ctx.lineWidth = 1;
          ctx.setLineDash([3, 3]);
          ctx.beginPath();
          ctx.arc(ss.x, ss.y, 7.5, 0, 6.2832);
          ctx.stroke();
          ctx.setLineDash([]);
        }
        if (front || ss.g > 0.6) {
          ctx.fillStyle = D ? `rgba(225,230,255,${0.3 + 0.6 * ss.g})` : `rgba(20,26,58,${0.4 + 0.6 * ss.g})`;
          ctx.font = `300 ${W < 600 ? 9 : 10}px 'Space Grotesk', sans-serif`;
          ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
          ctx.fillText(s.domain.slice(0, 22), ss.x + (Math.cos(an) > 0 ? 8 : -8), ss.y + 3);
        }
        hitRef.current.push({
          ...s,
          freshnessState: fstate,
          freshnessLabel: fresh?.label,
          x: ss.x,
          y: ss.y,
        });
      });

      // Persistent topic clusters from verified public knowledge.
      clustersRef.current.forEach((c, i) => {
        const an = (i / Math.max(clustersRef.current.length, 1)) * Math.PI * 2 + animT * 0.018;
        const radius = 2.05 + (i % 2) * 0.12;
        const x = ox + Math.cos(an) * R * radius;
        const y = oy + Math.sin(an) * R * radius * 0.5;
        clusterPositions[c.name] = { x, y };
        clusterPositions[c.node_id] = { x, y };
        ctx.fillStyle = `hsla(${hue + 35},90%,${D ? 68 : 42}%,0.42)`;
        ctx.beginPath();
        ctx.arc(x, y, 4.5, 0, 6.2832);
        ctx.fill();
        ctx.strokeStyle = `hsla(${hue + 35},80%,${L}%,0.25)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, 6.2832);
        ctx.stroke();
        if (c.count > 0) {
          ctx.fillStyle = D ? "rgba(225,230,255,0.7)" : "rgba(20,26,58,0.7)";
          ctx.font = `300 ${W < 600 ? 9 : 11}px 'Space Grotesk', sans-serif`;
          ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
          ctx.fillText(`${c.name} · ${c.count}`, x + (Math.cos(an) > 0 ? 12 : -12), y + 3);
        }
        hitRef.current.push({
          id: c.node_id,
          title: `${c.name} cluster`,
          domain: `${c.count} knowledge nodes`,
          url: "",
          state: "stored",
          kind: "cluster",
          clusterName: c.name,
          x,
          y,
        });
      });

      // Persistent links between topic clusters.
      graphRef.current.forEach((link) => {
        const a = clusterPositions[link.from_cluster || link.from];
        const b = clusterPositions[link.to_cluster || link.to];
        if (!a || !b) return;
        ctx.strokeStyle = `hsla(${hue + 35},85%,${L}%,0.28)`;
        ctx.lineWidth = 1.3;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo((a.x + b.x) / 2, (a.y + b.y) / 2 - 24, b.x, b.y);
        ctx.stroke();
      });

      // Knowledge connections discovered between sources.
      ctx.lineWidth = 1;
      connectionsRef.current.forEach((c) => {
        const a = sourceStates[c.from];
        const b = sourceStates[c.to];
        if (!a || !b) return;
        ctx.strokeStyle = `hsla(${hue},85%,${L}%,0.18)`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo((a.x + b.x) / 2, (a.y + b.y) / 2 - 18, b.x, b.y);
        ctx.stroke();
      });

      // Information flowing inward after a source is stored.
      if (act?.event_type === "research.memory_stored") {
        const age = (Date.now() - act.updatedAt) / 1000;
        if (age < 2 && act.sourceId && sourceStates[act.sourceId]) {
          const ss = sourceStates[act.sourceId];
          for (let k = 0; k < 6; k++) {
            const p = ((age * 0.7 + k / 6) % 1);
            const x = ss.x + (ox - ss.x) * p;
            const y = ss.y + (oy - ss.y) * p;
            ctx.fillStyle = `hsla(${hue},95%,${D ? 80 : 50}%,${(1 - p) * 0.7})`;
            ctx.beginPath();
            ctx.arc(x, y, 1.6, 0, 6.2832);
            ctx.fill();
          }
        }
      }

      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointer);
    };
  }, []);

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const hit = hitRef.current.find(
      (n) => Math.hypot(n.x - e.clientX, n.y - e.clientY) < 18,
    );
    e.currentTarget.style.cursor = hit ? "pointer" : "default";
    hoverRef.current?.(hit ?? null, e.clientX, e.clientY);
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const hit = hitRef.current.find(
      (n) => Math.hypot(n.x - e.clientX, n.y - e.clientY) < 18,
    );
    if (hit) selectRef.current?.(hit);
  };

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      onPointerMove={handlePointerMove}
      onPointerLeave={() => hoverRef.current?.(null)}
      onClick={handleClick}
      style={{ position: "fixed", inset: 0, width: "100%", height: "100%", display: "block", pointerEvents: "auto" }}
    />
  );
}
