"use client";

import { useEffect, useRef, useState, type DetailedHTMLProps, type HTMLAttributes } from "react";
import type { ModelViewerElement } from "@google/model-viewer";

declare module "react" {
  // React custom-element typing requires JSX namespace augmentation.
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": DetailedHTMLProps<HTMLAttributes<ModelViewerElement>, ModelViewerElement> & {
        src: string; alt: string; "camera-controls"?: boolean; "touch-action"?: string;
        "camera-orbit"?: string; "shadow-intensity"?: string; exposure?: string;
        "interaction-prompt"?: string; loading?: string;
      };
    }
  }
}

const layers = [
  ["01", "Front frame", "Open aperture for the whole digital face.", "#6c6c71"],
  ["02", "7-inch OLED", "Panel envelope and embedded AP1 preview.", "#414b61"],
  ["03", "Vented enclosure", "Service opening and cable escape.", "#85858b"],
  ["04", "Pi + display electronics", "Board, ports, GPIO and cooler clearance.", "#359a68"],
  ["05", "Removable carrier", "Pi standoffs and controller tie slots.", "#c68a32"],
  ["06", "Rear cover", "Ventilation and carrier attachment.", "#b0ada5"],
];

export default function SetupViewer() {
  const [mode, setMode] = useState<"assembled" | "exploded" | "electronics">("exploded");
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [fullscreen, setFullscreen] = useState(false);
  const viewer = useRef<ModelViewerElement>(null);
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    const el = viewer.current;
    const ready = () => { setLoaded(true); setError(""); };
    const failed = () => setError("3D could not load. Download the model below to inspect it locally.");
    el?.addEventListener("load", ready);
    el?.addEventListener("error", failed);
    import("@google/model-viewer").catch(() => { if (alive) failed(); });
    const changed = () => setFullscreen(document.fullscreenElement === stage.current);
    document.addEventListener("fullscreenchange", changed);
    return () => { alive = false; el?.removeEventListener("load", ready); el?.removeEventListener("error", failed); document.removeEventListener("fullscreenchange", changed); };
  }, []);

  function choose(next: "assembled" | "exploded" | "electronics") {
    if (next === mode) return;
    setLoaded(false); setError(""); setMode(next);
  }
  function camera(orbit: string) {
    if (!viewer.current || !loaded) return;
    viewer.current.cameraOrbit = orbit;
    viewer.current.cameraTarget = "auto auto auto";
    viewer.current.jumpCameraToGoal();
  }
  async function expand() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await stage.current?.requestFullscreen();
    } catch { setError("Fullscreen is unavailable in this browser. Orbit and zoom still work here."); }
  }

  return <div className="setup-layout">
    <div className="workspace-heading"><div><p className="eyebrow">Hardware studio / 02</p><h1>Behind the display.</h1>
      <p>Explore the enclosure, screen stack and Raspberry Pi installation.</p></div><span className="status-tag">Layout prototype</span></div>
    <div className="setup-stage" ref={stage}>
      <div className="model-toolbar"><div className="presets" role="group" aria-label="Assembly mode">
        {(["assembled", "exploded", "electronics"] as const).map((m) => <button className={mode === m ? "preset on" : "preset"} aria-pressed={mode === m} key={m} onClick={() => choose(m)}>{m}</button>)}
      </div><button className="ghost" onClick={expand}>{fullscreen ? "Exit fullscreen" : "Expand 3D"}</button></div>
      <model-viewer ref={viewer} src={`/models/setup-${mode}.glb`} alt={`${mode} prototype of the OLED display, enclosure, Raspberry Pi carrier and rear cover`}
        camera-controls touch-action="pan-y" camera-orbit="50deg 70deg 110%" shadow-intensity="0.5" exposure="1.1" interaction-prompt="none" loading="eager" />
      {!loaded && !error && <p className="model-status" role="status">Loading assembly…</p>}
      {error && <p className="model-error" role="alert">{error}</p>}
      <div className="model-toolbar model-bottom"><span>Drag to orbit · scroll to zoom</span><div className="presets" role="group" aria-label="Camera view">
        <button className="ghost" onClick={() => camera("0deg 90deg 105%")}>Front</button>
        <button className="ghost" onClick={() => camera("180deg 90deg 105%")}>Rear</button>
        <button className="ghost" onClick={() => camera("50deg 70deg 110%")}>Reset view</button>
      </div></div>
    </div>
    <aside className="assembly-guide" aria-label="Assembly layers"><p className="eyebrow">Inside the assembly</p>
      <ol>{layers.map(([n, title, desc, colour]) => <li key={n}><span style={{borderColor: colour}}>{n}</span><div><h2>{title}</h2><p>{desc}</p></div></li>)}</ol>
      <div className="model-downloads"><a href={`/models/setup-${mode}.glb`} download>Download {mode} GLB ↓</a><a href="/models/setup-prototype.zip" download>CAD source + prototype STLs ↓</a></div>
    </aside>
    <div className="setup-notes"><div><p className="eyebrow">Display</p><strong>7-inch OLED</strong><p>164 × 100 mm module assumed. Confirm the panel drawing before fabrication.</p></div>
      <div><p className="eyebrow">Compute</p><strong>Raspberry Pi 5 reference</strong><p>85 × 56 mm board. Connectors and cooler are approximate clearance models.</p></div>
      <div><p className="eyebrow">Fit status</p><strong>Bench prototype</strong><p>No verified vehicle mounts, cable routing or thermal validation. Screen image is illustrative.</p></div></div>
  </div>;
}
