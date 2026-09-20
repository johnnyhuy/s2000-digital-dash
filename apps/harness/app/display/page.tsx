import { HarnessApp } from "@/components/HarnessApp";

/** Aspect-preserving OLED preview. Telemetry is still simulated. */
export default function Display() {
  return <main className="display-preview"><HarnessApp displayOnly /></main>;
}
