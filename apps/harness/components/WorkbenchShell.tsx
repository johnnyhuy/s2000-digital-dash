import Link from "next/link";
import type { ReactNode } from "react";
import { ThemeControl } from "./ThemeControl";

export function WorkbenchShell({ active, children }: { active: "cluster" | "setup"; children: ReactNode }) {
  return <div className="shell workbench">
    <header className="workbench-header">
      <Link className="workbench-brand" href="/" aria-label="S2000 Digital Dash home">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/docs/assets/honda-h-mark.svg" alt="" width={34} height={34} />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="s2000-badge" src="/docs/assets/s2000-badge-on-dark.svg" alt="S2000" width={190} height={20} />
        <span>Digital dash <small>Bench studio</small></span>
      </Link>
      <ThemeControl />
    </header>
    <nav className="workspace-nav" aria-label="Workspace">
      <Link href="/" aria-current={active === "cluster" ? "page" : undefined}><span>01</span> Cluster</Link>
      <Link href="/setup" aria-current={active === "setup" ? "page" : undefined}><span>02</span> 3D setup</Link>
      <a className="display-link" href="/display">Open OLED preview <span aria-hidden>↗</span></a>
    </nav>
    <main className="workspace-main">{children}</main>
    <footer className="workspace-footer">
      <span>Unofficial DIY · simulated telemetry · display-only odometer</span>
      <a href="https://github.com/johnnyhuy/s2000-digital-dash">Source & build notes ↗</a>
    </footer>
  </div>;
}
