"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MODULE_H, VIEW_W, specFor } from "@/lib/geometry";
import { ClusterFace } from "./ClusterFace";
import {
  FACE_STYLES,
  FACE_STYLE_HINTS,
  FACE_STYLE_LABELS,
  parseFaceStyle,
  type FaceStyle,
} from "@/lib/faceStyle";
import { introDurationS, introPhaseAt, type IntroPhase } from "@/lib/intro";
import {
  SCENARIO_LABELS,
  SCENARIOS,
  START_ODO_KM,
  followDisplay,
  frameAt,
  integrateOdo,
  snapDisplay,
  type DisplayState,
  type Scenario,
} from "@/lib/mockDrive";
import { telemetryToDict, type Telemetry } from "@/lib/protocol";

const HZ_FEEL = 60;

function styleFromSearch(): FaceStyle {
  if (typeof window === "undefined") return "ap1";
  return parseFaceStyle(new URLSearchParams(window.location.search).get("style"));
}

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function HarnessApp({ displayOnly = false }: { displayOnly?: boolean }) {
  const [playing, setPlaying] = useState(true);
  const [scenario, setScenario] = useState<Scenario>("cruise");
  const [faceStyle, setFaceStyle] = useState<FaceStyle>("ap1");
  const [face, setFace] = useState<DisplayState>(() =>
    snapDisplay(frameAt(0, START_ODO_KM, "cruise"), START_ODO_KM),
  );
  const [raw, setRaw] = useState<Telemetry>(() => frameAt(0, START_ODO_KM, "cruise"));
  const [phase, setPhase] = useState<IntroPhase>("sweep");
  const [phaseT, setPhaseT] = useState(0);

  const playingRef = useRef(playing);
  const scenarioRef = useRef(scenario);
  const tRef = useRef(0);
  const bootRef = useRef(0);
  const skippedRef = useRef(false);
  const odoRef = useRef(START_ODO_KM);
  const tripOriginRef = useRef(START_ODO_KM);
  const faceRef = useRef(face);
  const rawRef = useRef(raw);

  useEffect(() => {
    // Client-only inputs (URL, media query) — applied after hydration on the
    // next frame so the SSR markup and first client render match.
    const frame = requestAnimationFrame(() => {
      setFaceStyle(styleFromSearch());
      if (prefersReducedMotion()) {
        skippedRef.current = true;
        setPhase("live");
        setPhaseT(1);
      }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    playingRef.current = playing;
  }, [playing]);

  useEffect(() => {
    scenarioRef.current = scenario;
  }, [scenario]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.code !== "Space" || event.repeat) return;
      if (event.target instanceof HTMLElement && event.target.closest("button, select, input, textarea, a")) return;
      if (skippedRef.current || bootRef.current >= introDurationS()) return;
      event.preventDefault();
      skippedRef.current = true;
      setPhase("live");
      setPhaseT(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    let raf = 0;
    let last = performance.now();
    let acc = 0;
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (playingRef.current) {
        tRef.current += dt;
        odoRef.current = integrateOdo(odoRef.current, rawRef.current.speed_kmh, dt);
        if (!skippedRef.current) bootRef.current += dt;
      }
      acc += dt;
      const step = 1 / HZ_FEEL;
      if (acc >= step || !playingRef.current) {
        const useDt = playingRef.current ? Math.min(acc, 0.05) : 0.08;
        acc = 0;
        const target = frameAt(tRef.current, odoRef.current, scenarioRef.current);
        const next = followDisplay(faceRef.current, target, useDt, tripOriginRef.current);
        faceRef.current = next;
        rawRef.current = target;
        setFace(next);
        setRaw(target);
        if (skippedRef.current) {
          setPhase("live");
          setPhaseT(1);
        } else {
          const intro = introPhaseAt(bootRef.current);
          setPhase(intro.phase);
          setPhaseT(intro.local);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const applyScenario = useCallback((next: Scenario) => {
    setScenario(next);
    tRef.current = 0;
    const target = frameAt(0, odoRef.current, next);
    rawRef.current = target;
    setRaw(target);
    const snapped = snapDisplay(target, tripOriginRef.current);
    faceRef.current = snapped;
    setFace(snapped);
  }, []);

  const applyStyle = useCallback((next: FaceStyle) => {
    setFaceStyle(next);
    skippedRef.current = prefersReducedMotion();
    bootRef.current = 0;
    setPhase(skippedRef.current ? "live" : "sweep");
    setPhaseT(skippedRef.current ? 1 : 0);
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    if (next === "ap1") url.searchParams.delete("style");
    else url.searchParams.set("style", next);
    window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }, []);

  const skipIntro = useCallback(() => {
    skippedRef.current = true;
    setPhase("live");
    setPhaseT(1);
  }, []);

  const replayIntro = useCallback(() => {
    skippedRef.current = false;
    bootRef.current = 0;
    setPhase("sweep");
    setPhaseT(0);
    setPlaying(true);
  }, []);

  const json = telemetryToDict(raw);
  const booting = phase !== "live";

  return (
    <div className={displayOnly ? "harness harness-display" : "harness studio-layout"}
      style={displayOnly ? { width: `min(100vw, calc(100dvh * ${VIEW_W / (MODULE_H + VIEW_W * specFor(faceStyle).crown_lip)}))` } : undefined}>
      {!displayOnly && <div className="workspace-heading">
        <div><p className="eyebrow">Instrument studio / 01</p><h1>The driver’s view.</h1>
          <p>Explore both faces, check the telltales and replay the startup.</p></div>
        <span className="status-tag"><i />{playing ? "Simulation running" : "Simulation paused"}</span>
      </div>}
      <section className="stage">
        {!displayOnly && <div className="stage-toolbar"><span>{FACE_STYLE_LABELS[faceStyle]} · {faceStyle === "ap1" ? "Straight gauges" : "Arched gauges"}</span><span>{phase === "live" ? "Live preview" : `Startup / ${phase}`}</span></div>}
        <ClusterFace face={face} style={faceStyle} phase={phase} phaseT={phaseT} />
        {!displayOnly && <div className="stage-footer"><span>7-inch OLED / Raspberry Pi</span><a href={`/display?style=${faceStyle}`}>Full screen preview ↗</a></div>}
      </section>
      {!displayOnly && <>
        <section className="desk studio-controls" aria-label="Harness controls">
          <div className="control-section"><p className="eyebrow">01 / Face</p>
            <div className="presets" role="group" aria-label="Face style">
              {FACE_STYLES.map((id) => <button key={id} type="button" className={id === faceStyle ? "preset on" : "preset"}
                onClick={() => applyStyle(id)} aria-pressed={id === faceStyle} title={FACE_STYLE_HINTS[id]}>{FACE_STYLE_LABELS[id]}</button>)}
            </div>
            <p className="control-hint">{faceStyle === "ap1" ? "1999–2003 reference · straight side gauges" : "2004+ reference · arched side gauges"}</p>
          </div>
          <div className="control-section"><p className="eyebrow">02 / Drive condition</p>
            <div className="presets" role="group" aria-label="Scenario presets">
              {SCENARIOS.map((id) => <button key={id} type="button" className={id === scenario ? "preset on" : "preset"}
                onClick={() => applyScenario(id)} aria-pressed={id === scenario}>{SCENARIO_LABELS[id]}</button>)}
            </div>
            <p className="control-hint">{scenario === "warn" ? "Low fuel, hot coolant and warning lamps." : "Simulated values. No vehicle connected."}</p>
          </div>
          <div className="control-section"><p className="eyebrow">03 / Playback</p><div className="presets">
            <button type="button" className="primary" onClick={() => setPlaying((p) => !p)} aria-pressed={playing}>{playing ? "Pause" : "Play"}</button>
            <button type="button" className="ghost" onClick={replayIntro}>Replay startup</button>
            {booting && <button type="button" className="ghost" onClick={skipIntro}>Skip boot</button>}
          </div><p className="control-hint">Custom lamp check, READY and reveal.</p></div>
        </section>
        <section className="telemetry-strip" aria-label="Live telemetry">
          <div><span>Engine</span><strong>{Math.round(face.rpm).toLocaleString("en-US")} <small>r/min</small></strong></div>
          <div><span>Speed</span><strong>{Math.round(face.speed_kmh)} <small>km/h</small></strong></div>
          <div><span>Coolant</span><strong>{Math.round(face.ect_c)} <small>°C</small></strong></div>
          <div><span>Fuel</span><strong>{Math.round(face.fuel_pct)} <small>%</small></strong></div>
          <div><span>Supply</span><strong>{face.batt_v.toFixed(1)} <small>V</small></strong></div>
        </section>
        <details className="protocol-details"><summary>Inspect telemetry <span>JSON · simulated</span></summary>
          <pre className="json" tabIndex={0} aria-label="Current protocol JSON">{JSON.stringify(json, null, 2)}</pre>
        </details>
      </>}
    </div>
  );
}
