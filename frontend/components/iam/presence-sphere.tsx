"use client";

import React from "react";

export type IAMState = "idle" | "listening" | "thinking" | "speaking" | "working";

export interface MemoryNode {
  text: string;
  hit?: boolean;
}

interface Props {
  state: IAMState;
  mode: "focus" | "recall" | "create";
  nodes: MemoryNode[];
}

const MODE_HUE: Record<string, number> = { focus: 215, recall: 280, create: 28 };

const STATE_TARGETS: Record<IAMState, Record<string, number>> = {
  idle: { amp: 0.03, spd: 0.15, rad: 1, glow: 0.35, wf: 1.2 },
  listening: { amp: 0.09, spd: 0.35, rad: 1.1, glow: 0.7, wf: 3 },
  thinking: { amp: 0.05, spd: 1.3, rad: 0.82, glow: 1, wf: 6 },
  speaking: { amp: 0.075, spd: 0.3, rad: 1.04, glow: 0.8, wf: 4 },
  working: { amp: 0.06, spd: 0.6, rad: 0.95, glow: 0.9, wf: 4.5 },
};

export function PresenceSphere({ state, mode, nodes }: Props) {
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const stateRef = React.useRef(state);
  const modeRef = React.useRef(mode);
  const nodesRef = React.useRef(nodes);

  React.useEffect(() => { stateRef.current = state; }, [state]);
  React.useEffect(() => { modeRef.current = mode; }, [mode]);
  React.useEffect(() => { nodesRef.current = nodes; }, [nodes]);

  React.useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

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

    const frame = (ts: number) => {
      const t = ts * 0.001;
      const dt = Math.min(t - last, 0.05);
      last = t;

      const st = stateRef.current;
      const target = STATE_TARGETS[st] ?? STATE_TARGETS.idle;
      for (const k in target) cur[k] += (target[k] - cur[k]) * Math.min(1, dt * 3);

      hueT = MODE_HUE[modeRef.current] ?? 215;
      hue += (hueT - hue) * Math.min(1, dt * 2.5);
      rot += dt * cur.spd;

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

      ctx.globalCompositeOperation = D ? "lighter" : "source-over";
      for (let i = 0; i < N; i++) {
        const p = P[i];
        const d = 1 + cur.amp * Math.sin(p.y * 5 + t * cur.wf + p.s * 2.2)
          + (st === "listening" ? 0.04 * Math.sin(t * 5 + p.s * 6) : 0);
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
        const an = n.a + t * n.sp;
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

      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("pointermove", onPointer);
    };
  }, []);

  return <canvas ref={canvasRef} aria-hidden="true" style={{ position: "fixed", inset: 0, width: "100%", height: "100%", display: "block" }} />;
}
