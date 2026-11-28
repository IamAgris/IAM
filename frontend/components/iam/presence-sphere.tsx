"use client";

import React from "react";
import dynamic from "next/dynamic";
import { WORLD_LAND } from "@/lib/world-outline";

// Real interactive tiles are loaded client-only (MapLibre needs `window`).
// The offline vector basemap remains the fallback if tiles cannot load.
const GeoMap = dynamic(() => import("./geo-map"), { ssr: false });

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
  from_node?: string;
  to_node?: string;
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

export interface MapPlace {
  name: string;
  latitude: number;
  longitude: number;
  country_code: string | null;
  place_type: string;
  source: string;
  confidence: number;
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
  mapMode?: boolean;
  mapPlaces?: MapPlace[];
  dark?: boolean;
  onNodeHover?: (node: SourceNode | null, x?: number, y?: number) => void;
  onNodeSelect?: (node: SourceNode) => void;
  selectedId?: string | null;
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
  mapMode = false,
  mapPlaces = [],
  dark = false,
  onNodeHover,
  onNodeSelect,
  selectedId = null,
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
  const mapRef = React.useRef(mapMode);
  const mapPlacesRef = React.useRef(mapPlaces);
  const hoverRef = React.useRef(onNodeHover);
  const selectRef = React.useRef(onNodeSelect);
  const hitRef = React.useRef<Array<SourceNode & { x: number; y: number }>>([]);
  const drawRef = React.useRef<(() => void) | null>(null);
  const resizeRef = React.useRef<(() => void) | null>(null);
  const focusedIndexRef = React.useRef(-1);
  const selectedRef = React.useRef<string | null>(selectedId);
  const viewRef = React.useRef({ yaw: 0, pitch: 0.3, zoom: 1 });
  const dragRef = React.useRef({ active: false, x: 0, y: 0, moved: false });
  const pointersRef = React.useRef(new Map<number, { x: number; y: number }>());
  const pinchRef = React.useRef<{ dist: number; zoom: number } | null>(null);
  const reducedMotion = typeof window !== "undefined"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  React.useEffect(() => { stateRef.current = state; }, [state]);
  React.useEffect(() => { modeRef.current = mode; }, [mode]);
  React.useEffect(() => { nodesRef.current = nodes; }, [nodes]);
  React.useEffect(() => { activityRef.current = activity ?? null; }, [activity]);
  React.useEffect(() => { sourcesRef.current = sourceNodes; }, [sourceNodes]);
  React.useEffect(() => { connectionsRef.current = connections; }, [connections]);
  React.useEffect(() => { clustersRef.current = clusters; }, [clusters]);
  React.useEffect(() => { graphRef.current = graphConnections; }, [graphConnections]);
  React.useEffect(() => { freshnessRef.current = freshness; }, [freshness]);
  React.useEffect(() => { mapRef.current = mapMode; }, [mapMode]);
  React.useEffect(() => { mapPlacesRef.current = mapPlaces; }, [mapPlaces]);
  React.useEffect(() => { hoverRef.current = onNodeHover; }, [onNodeHover]);
  React.useEffect(() => { selectRef.current = onNodeSelect; }, [onNodeSelect]);
  React.useEffect(() => { selectedRef.current = selectedId; }, [selectedId]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let W = 0, H = 0, cx = 0, cy = 0, R = 0, baseR = 0;
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
      const compact = W < 600;
      baseR = Math.min(W * (compact ? 0.78 : 0.9), H * (compact ? 0.5 : 0.62)) * 0.27;
      R = baseR * viewRef.current.zoom;
    };

    const onResize = () => size();
    const onVisible = () => {
      if (!document.hidden) {
        size();
        drawRef.current?.();
      }
    };
    const onPointer = (e: PointerEvent) => {
      mx = e.clientX / W - 0.5;
      my = e.clientY / H - 0.5;
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("pointermove", onPointer);
    resizeRef.current = size;
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

    // Memory nodes can change after mount — rebuild their orbits from live refs
    // each frame while preserving angle/glow state by label.
    const orbitalStates: Record<string, { a: number; g: number }> = {};

    // Live research source nodes — keyed by node id so updates never rebuild
    // the particle sphere or restart the animation loop.
    const sourceStates: Record<string, {
      a: number; r: number; g: number; x: number; y: number; born: number;
    }> = {};
    const clusterPositions: Record<string, { x: number; y: number }> = {};
    const linkBirths: Record<string, number> = {};

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

      if (mapRef.current) {
        const mw = Math.min(W * 0.86, 1040);
        const mh = mw / 2;
        const left = (W - mw) / 2;
        const top = Math.max(90, H * 0.2);
        ctx.strokeStyle = `hsla(${hue},60%,${L}%,0.16)`;
        ctx.lineWidth = 1;
        for (let lon = -180; lon <= 180; lon += 30) {
          const x = left + ((lon + 180) / 360) * mw;
          ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + mh); ctx.stroke();
        }
        for (let lat = -90; lat <= 90; lat += 30) {
          const y = top + ((90 - lat) / 180) * mh;
          ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + mw, y); ctx.stroke();
        }
        ctx.strokeStyle = `hsla(${hue},70%,${L}%,0.4)`;
        ctx.strokeRect(left, top, mw, mh);

        // Land outlines (offline vector basemap) — makes this a real map, not just a grid.
        const project = (lon: number, lat: number): [number, number] => [
          left + ((lon + 180) / 360) * mw,
          top + ((90 - lat) / 180) * mh,
        ];
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = `hsla(${hue + 20},55%,${D ? 78 : 38}%,0.55)`;
        ctx.fillStyle = `hsla(${hue + 20},40%,${D ? 70 : 45}%,0.12)`;
        for (const ring of WORLD_LAND) {
          if (ring.length < 3) continue;
          ctx.beginPath();
          ring.forEach(([lon, lat], i) => {
            const [x, y] = project(lon, lat);
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          });
          ctx.closePath();
          ctx.fill();
          ctx.stroke();
        }

        hitRef.current = [];
        mapPlacesRef.current.forEach((p, i) => {
          const x = left + ((p.longitude + 180) / 360) * mw;
          const y = top + ((90 - p.latitude) / 180) * mh;
          ctx.fillStyle = `hsla(${hue + 30},90%,${D ? 70 : 45}%,0.85)`;
          ctx.beginPath(); ctx.arc(x, y, 4, 0, 6.2832); ctx.fill();
          if (i < 12) {
            ctx.fillStyle = D ? "rgba(225,230,255,.75)" : "rgba(20,26,58,.75)";
            ctx.font = `300 ${W < 600 ? 9 : 11}px 'Space Grotesk', sans-serif`;
            ctx.fillText(p.name.slice(0, 24), x + 8, y + 3);
          }
          hitRef.current.push({
            id: `place-${i}-${p.name}`,
            title: p.name,
            domain: p.country_code || p.place_type,
            url: "",
            state: "stored",
            kind: "source",
            x,
            y,
          });
        });
        ctx.fillStyle = D ? "rgba(225,230,255,.55)" : "rgba(20,26,58,.55)";
        ctx.font = `300 ${W < 600 ? 10 : 12}px 'Space Grotesk', sans-serif`;
        ctx.fillText(`GEOSPATIAL VIEW · ${mapPlacesRef.current.length} places`, left, top - 12);
        const focusedPlace = hitRef.current[focusedIndexRef.current];
        if (focusedPlace) {
          ctx.strokeStyle = `hsla(${hue},95%,${D ? 80 : 45}%,0.9)`;
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          ctx.arc(focusedPlace.x, focusedPlace.y, 10, 0, 6.2832);
          ctx.stroke();
        }
        raf = reducedMotion ? 0 : requestAnimationFrame(frame);
        return;
      }

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
      const memoryNodes = nodesRef.current;
      memoryNodes.forEach((n, i) => {
        if (!orbitalStates[n.text]) {
          orbitalStates[n.text] = {
            a: (i / Math.max(memoryNodes.length, 1)) * Math.PI * 2,
            g: 0,
          };
        }
        const st = orbitalStates[n.text];
        const sp = i % 2 === 0 ? 0.08 : -0.07;
        const radius = (W < 600 ? 1.3 : 1.6) + (i % 3) * (W < 600 ? 0.1 : 0.15);
        const an = st.a + animT * sp;
        const x = ox + Math.cos(an) * R * radius;
        const y = oy + Math.sin(an) * R * radius * 0.42;
        const front = Math.sin(an) > 0;
        st.g += ((n.hit ? 1 : 0) - st.g) * Math.min(1, dt * 3);
        if (st.g > 0.02) {
          ctx.strokeStyle = `hsla(${hue},90%,${L}%,${0.7 * st.g})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.quadraticCurveTo((x + ox) / 2, (y + oy) / 2 - 30 * st.g, ox, oy);
          ctx.stroke();
        }
        ctx.fillStyle = `hsla(${hue},90%,${D ? 75 : 40}%,${0.5 + 0.5 * st.g})`;
        ctx.beginPath();
        ctx.arc(x, y, 3 + 4 * st.g, 0, 6.2832);
        ctx.fill();
        ctx.fillStyle = D ? `rgba(225,230,255,${0.28 + 0.7 * st.g})` : `rgba(20,26,58,${0.35 + 0.65 * st.g})`;
        ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
        if (
          (front || st.g > 0.1)
          && x > (W < 600 ? 125 : 70)
          && x < W - (W < 600 ? 125 : 70)
        ) {
          ctx.fillText(
            W < 600 ? n.text.slice(0, 14) : n.text,
            x + (Math.cos(an) > 0 ? 12 : -12),
            y + 4,
          );
        }
      });

      // Live source nodes from public research events.
      const sources = sourcesRef.current;
      const labelledDomains = new Set<string>();
      hitRef.current = [];
      sources.forEach((s, i) => {
        if (!sourceStates[s.id]) {
          sourceStates[s.id] = {
            a: (i * 2.39996) % (Math.PI * 2),
            r: (W < 600 ? 1.15 : 1.35) + (i % 4) * (W < 600 ? 0.1 : 0.13),
            g: 0,
            x: 0,
            y: 0,
            born: reducedMotion ? -10 : t,
          };
        }
        const ss = sourceStates[s.id];
        const an = ss.a + animT * (i % 2 === 0 ? 0.05 : -0.045) + viewRef.current.yaw;
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

        const bornAge = t - ss.born;
        const arriving = !reducedMotion && bornAge >= 0 && bornAge < 1.4;
        ctx.fillStyle = `hsla(${nodeHue},95%,${D ? 72 : 45}%,${Math.min(1, 0.35 + 0.65 * ss.g)})`;
        ctx.beginPath();
        ctx.arc(ss.x, ss.y, (2.5 + 3.5 * ss.g) * (arriving ? 0.6 + bornAge * 0.5 : 1), 0, 6.2832);
        ctx.fill();
        if (arriving) {
          const phase = bornAge / 1.4;
          ctx.strokeStyle = `hsla(${nodeHue},95%,${D ? 78 : 42}%,${(1 - phase) * 0.7})`;
          ctx.lineWidth = 1.2;
          ctx.beginPath();
          ctx.arc(ss.x, ss.y, 5 + phase * 22, 0, 6.2832);
          ctx.stroke();
        }
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
        if (
          (front || ss.g > 0.6)
          && !labelledDomains.has(s.domain)
          && ss.x > (W < 600 ? 125 : 70)
          && ss.x < W - (W < 600 ? 125 : 70)
        ) {
          labelledDomains.add(s.domain);
          ctx.fillStyle = D ? `rgba(225,230,255,${0.3 + 0.6 * ss.g})` : `rgba(20,26,58,${0.4 + 0.6 * ss.g})`;
          ctx.font = `300 ${W < 600 ? 9 : 10}px 'Space Grotesk', sans-serif`;
          ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
          ctx.fillText(
            s.domain.slice(0, W < 600 ? 10 : 22),
            ss.x + (Math.cos(an) > 0 ? 8 : -8),
            ss.y + 3,
          );
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
        const an = (i / Math.max(clustersRef.current.length, 1)) * Math.PI * 2 + animT * 0.018 + viewRef.current.yaw;
        const radius = (W < 600 ? 1.7 : 2.05) + (i % 2) * (W < 600 ? 0.08 : 0.12);
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
        if (c.count > 0 && x > (W < 600 ? 105 : 70) && x < W - (W < 600 ? 105 : 70)) {
          ctx.fillStyle = D ? "rgba(225,230,255,0.7)" : "rgba(20,26,58,0.7)";
          ctx.font = `300 ${W < 600 ? 9 : 11}px 'Space Grotesk', sans-serif`;
          ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
          ctx.fillText(
            `${W < 600 ? c.name.slice(0, 12) : c.name} · ${c.count}`,
            x + (Math.cos(an) > 0 ? 12 : -12),
            y + 3,
          );
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

      // Stored provenance links also name public source domains as clusters.
      // Give those clusters positions too, otherwise their links silently
      // disappear from the canvas even though the relationship is recorded.
      const linkedClusters = new Set<string>();
      graphRef.current.forEach((link) => {
        for (const name of [link.from_cluster, link.to_cluster]) {
          if (name && !clusterPositions[name]) linkedClusters.add(String(name));
        }
      });
      const linked = Array.from(linkedClusters);
      linked.forEach((name, i) => {
        const total = clustersRef.current.length + linked.length;
        const idx = clustersRef.current.length + i;
        const an = (idx / Math.max(total, 1)) * Math.PI * 2 + animT * 0.018 + viewRef.current.yaw;
        const radius = (W < 600 ? 1.7 : 2.05) + (idx % 2) * (W < 600 ? 0.08 : 0.12);
        const x = ox + Math.cos(an) * R * radius;
        const y = oy + Math.sin(an) * R * radius * 0.5;
        clusterPositions[name] = { x, y };
        ctx.fillStyle = `hsla(${hue + 35},90%,${D ? 68 : 42}%,0.38)`;
        ctx.beginPath();
        ctx.arc(x, y, 3.5, 0, 6.2832);
        ctx.fill();
        ctx.strokeStyle = `hsla(${hue + 35},80%,${L}%,0.22)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, 6.2832);
        ctx.stroke();
        ctx.fillStyle = D ? "rgba(225,230,255,0.6)" : "rgba(20,26,58,0.6)";
        if (x > (W < 600 ? 105 : 70) && x < W - (W < 600 ? 105 : 70)) {
          ctx.font = `300 ${W < 600 ? 8 : 9}px 'Space Grotesk', sans-serif`;
          ctx.textAlign = Math.cos(an) > 0 ? "left" : "right";
          ctx.fillText(name.slice(0, W < 600 ? 12 : 22), x + (Math.cos(an) > 0 ? 10 : -10), y + 3);
        }
        hitRef.current.push({
          id: `cluster:${name}`,
          title: `${name} cluster`,
          domain: "public source cluster",
          url: "",
          state: "stored",
          kind: "cluster",
          clusterName: name,
          x,
          y,
        });
      });

      // Bow a link's control point away from the sphere centre so connections
      // wrap around the particle shell instead of cutting straight through it.
      const bowedControl = (a: { x: number; y: number }, b: { x: number; y: number }) => {
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        let dx = mx - ox;
        let dy = my - oy;
        let len = Math.hypot(dx, dy);
        if (len < 1) {
          dx = -(b.y - a.y);
          dy = b.x - a.x;
          len = Math.hypot(dx, dy) || 1;
        }
        // Always push the control point beyond the midpoint, even when both
        // endpoints are already outside the shell; otherwise far links render
        // as a straight line.
        const target = Math.max(R * 1.35, len + Math.min(70, R * 0.35));
        const scale = target / len;
        return { x: ox + dx * scale, y: oy + dy * scale };
      };

      // Persistent links between topic clusters.
      graphRef.current.forEach((link) => {
        const a = clusterPositions[link.from_cluster || link.from];
        const b = clusterPositions[link.to_cluster || link.to];
        if (!a || !b) return;
        ctx.strokeStyle = `hsla(${hue + 35},90%,${L}%,0.55)`;
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        const ctrl = bowedControl(a, b);
        ctx.quadraticCurveTo(ctrl.x, ctrl.y, b.x, b.y);
        ctx.stroke();
      });

      // Source → cluster provenance is drawn only where a stored link records
      // that relationship. Proximity alone is never presented as evidence.
      graphRef.current.forEach((link) => {
        const sourceId = link.from_node || link.to_node;
        const clusterName = link.from_cluster || link.to_cluster;
        const ss = sourceId ? sourceStates[sourceId] : null;
        const cluster = clusterName ? clusterPositions[clusterName] : null;
        if (!ss || !cluster) return;
        ctx.strokeStyle = `hsla(${hue},80%,${L}%,0.28)`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(ss.x, ss.y);
        const ctrl = bowedControl(ss, cluster);
        ctx.quadraticCurveTo(ctrl.x, ctrl.y, cluster.x, cluster.y);
        ctx.stroke();
      });

      // Knowledge connections discovered between sources.
      ctx.lineWidth = 1;
      connectionsRef.current.forEach((c) => {
        const a = sourceStates[c.from];
        const b = sourceStates[c.to];
        if (!a || !b) return;
        const key = `${c.from}-${c.to}`;
        if (linkBirths[key] === undefined) {
          linkBirths[key] = reducedMotion ? -10 : t;
        }
        const age = t - linkBirths[key];
        const arriving = !reducedMotion && age >= 0 && age < 1.2;
        ctx.strokeStyle = `hsla(${hue},90%,${L}%,${0.42 * (arriving ? Math.min(1, age * 2.5) : 1)})`;
        ctx.lineWidth = 1.4;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        const ctrl = bowedControl(a, b);
        ctx.quadraticCurveTo(ctrl.x, ctrl.y, b.x, b.y);
        ctx.stroke();
        if (arriving) {
          const phase = age / 1.2;
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          ctx.fillStyle = `hsla(${hue},95%,${D ? 82 : 40}%,${(1 - phase) * 0.9})`;
          ctx.beginPath();
          ctx.arc(mx, my, 2 + phase * 5, 0, 6.2832);
          ctx.fill();
        }
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

      const focused = hitRef.current[focusedIndexRef.current];
      if (focused) {
        ctx.strokeStyle = `hsla(${hue},95%,${D ? 80 : 45}%,0.9)`;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(focused.x, focused.y, 11, 0, 6.2832);
        ctx.stroke();
      }
      raf = reducedMotion ? 0 : requestAnimationFrame(frame);
    };
    drawRef.current = () => frame(performance.now());
    // Paint synchronously once: backgrounded tabs may throttle the first RAF,
    // which otherwise leaves an empty canvas when the page becomes visible.
    frame(performance.now());

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("pointermove", onPointer);
    };
  }, []);

  // With reduced motion there is no animation loop — redraw only when data changes.
  React.useEffect(() => {
    if (reducedMotion) drawRef.current?.();
  }, [reducedMotion, state, mode, nodes, activity, sourceNodes, connections, clusters, graphConnections, freshness]);

  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    e.currentTarget.setPointerCapture(e.pointerId);
    if (pointersRef.current.size === 1) {
      dragRef.current = { active: true, x: e.clientX, y: e.clientY, moved: false };
    } else if (pointersRef.current.size === 2) {
      const [a, b] = Array.from(pointersRef.current.values());
      pinchRef.current = {
        dist: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        zoom: viewRef.current.zoom,
      };
      dragRef.current.active = false;
    }
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (pointersRef.current.has(e.pointerId)) {
      pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    }
    if (pointersRef.current.size >= 2 && pinchRef.current) {
      const [a, b] = Array.from(pointersRef.current.values());
      const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1;
      const next = Math.max(
        0.7,
        Math.min(1.8, pinchRef.current.zoom * (dist / pinchRef.current.dist)),
      );
      if (next !== viewRef.current.zoom) {
        viewRef.current.zoom = next;
        resizeRef.current?.();
        if (reducedMotion) drawRef.current?.();
      }
      return;
    }
    const d = dragRef.current;
    if (d.active) {
      const dx = e.clientX - d.x;
      const dy = e.clientY - d.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
      viewRef.current.yaw += dx * 0.006;
      viewRef.current.pitch = Math.max(
        -0.9,
        Math.min(0.9, viewRef.current.pitch + dy * 0.005),
      );
      d.x = e.clientX;
      d.y = e.clientY;
      if (reducedMotion) drawRef.current?.();
      return;
    }
    const hit = hitRef.current.find(
      (n) => Math.hypot(n.x - e.clientX, n.y - e.clientY) < 22,
    );
    e.currentTarget.style.cursor = hit ? "pointer" : "default";
    hoverRef.current?.(hit ?? null, e.clientX, e.clientY);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    pointersRef.current.delete(e.pointerId);
    if (pointersRef.current.size < 2) pinchRef.current = null;
    if (pointersRef.current.size === 0) {
      dragRef.current.active = false;
    } else if (pointersRef.current.size === 1) {
      const [point] = Array.from(pointersRef.current.values());
      dragRef.current = { active: true, x: point.x, y: point.y, moved: true };
    }
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
  };

  const handleWheel = (e: React.WheelEvent<HTMLCanvasElement>) => {
    const next = Math.max(
      0.7,
      Math.min(1.8, viewRef.current.zoom * Math.exp(-e.deltaY * 0.001)),
    );
    if (next === viewRef.current.zoom) return;
    viewRef.current.zoom = next;
    resizeRef.current?.();
    if (reducedMotion) drawRef.current?.();
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (dragRef.current.moved) {
      dragRef.current.moved = false;
      return;
    }
    const hit = hitRef.current.find(
      (n) => Math.hypot(n.x - e.clientX, n.y - e.clientY) < 22,
    );
    if (hit) selectRef.current?.(hit);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLCanvasElement>) => {
    const items = hitRef.current;
    if (!items.length) return;
    if (e.key === "Escape") {
      focusedIndexRef.current = -1;
      hoverRef.current?.(null);
      e.preventDefault();
      return;
    }
    let index = focusedIndexRef.current;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") index = (index + 1) % items.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") index = (index <= 0 ? items.length : index) - 1;
    else if (e.key === "Enter" || e.key === " ") {
      const chosen = items[index < 0 ? 0 : index];
      if (chosen) selectRef.current?.(chosen);
      e.preventDefault();
      return;
    } else return;
    focusedIndexRef.current = index;
    const node = items[index];
    hoverRef.current?.(node, node.x, node.y);
    if (reducedMotion) drawRef.current?.();
    e.preventDefault();
  };

  const handleMapSelect = React.useCallback(
    (place: MapPlace) => {
      onNodeSelect?.({
        id: `place-${place.name}`,
        title: place.name,
        domain: place.country_code || place.place_type,
        url: "",
        state: "stored",
        kind: "source",
      });
    },
    [onNodeSelect]
  );

  return (
    <>
      <canvas
        ref={canvasRef}
        tabIndex={mapMode ? -1 : 0}
        role="img"
        aria-label="IAM intelligence sphere. Use arrow keys to inspect source and cluster nodes, Enter to open, Escape to clear."
        onKeyDown={handleKeyDown}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={() => hoverRef.current?.(null)}
        onWheel={handleWheel}
        onClick={handleClick}
        style={{
          position: "fixed", inset: 0, width: "100%", height: "100%", display: "block",
          touchAction: "none",
          opacity: mapMode ? 0 : 1,
          pointerEvents: mapMode ? "none" : "auto",
        }}
      />
      {mapMode && (
        <div className="pointer-events-auto" style={{ position: "fixed", inset: 0, zIndex: 1 }}>
          <GeoMap places={mapPlaces} dark={dark} onSelect={handleMapSelect} />
        </div>
      )}
    </>
  );
}
