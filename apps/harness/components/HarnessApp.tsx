"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

export function HarnessApp() {
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

  const json = telemetryToDict(raw);
  const booting = phase !== "live";

  return (
    <div className="harness">
      <section className="stage">
        <ClusterFace face={face} style={faceStyle} phase={phase} phaseT={phaseT} />
      </section>

      <section className="desk" aria-label="Harness controls">
        <div className="desk-row">
          <button
            type="button"
            className="primary"
            onClick={() => setPlaying((p) => !p)}
            aria-pressed={playing}
          >
            {playing ? "Pause" : "Play"}
          </button>
          {booting ? (
            <button type="button" className="ghost" onClick={skipIntro}>
              Skip boot
            </button>
          ) : null}
          <div className="presets" role="group" aria-label="Face style">
            {FACE_STYLES.map((id) => (
              <button
                key={id}
                type="button"
                className={id === faceStyle ? "preset on" : "preset"}
                onClick={() => applyStyle(id)}
                aria-pressed={id === faceStyle}
                title={FACE_STYLE_HINTS[id]}
              >
                {FACE_STYLE_LABELS[id]}
              </button>
            ))}
          </div>
          <div className="presets" role="group" aria-label="Scenario presets">
            {SCENARIOS.map((id) => (
              <button
                key={id}
                type="button"
                className={id === scenario ? "preset on" : "preset"}
                onClick={() => applyScenario(id)}
                aria-pressed={id === scenario}
              >
                {SCENARIO_LABELS[id]}
              </button>
            ))}
          </div>
        </div>

        <div className="desk-meta">
          <p>
            Client mock at ~{HZ_FEEL} Hz feel · frozen fields{" "}
            <code>rpm speed_kmh fuel_pct ect_c batt_v odo_km lamps</code>
          </p>
          <p>
            {playing ? "Live" : "Paused"} · {phase} · {FACE_STYLE_LABELS[faceStyle]} ·{" "}
            {SCENARIO_LABELS[scenario]} · {Math.round(face.rpm)} r/min · {Math.round(face.speed_kmh)} km/h
          </p>
        </div>
        <p className="desk-hint">
          {FACE_STYLE_HINTS[faceStyle]}
          {booting ? " · Space skips boot" : ""}
        </p>

        <pre className="json" tabIndex={0} aria-label="Current protocol JSON">
          {JSON.stringify(json, null, 2)}
        </pre>
      </section>
    </div>
  );
}
