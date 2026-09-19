import { HarnessApp } from "@/components/HarnessApp";

export default function Home() {
  return (
    <div className="shell">
      <p className="disclaimer" role="note">
        Unofficial DIY · not Honda · odometer is display-only
      </p>

      <header className="masthead">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/docs/assets/honda-h-mark.svg"
          alt="Honda H-mark"
          width={56}
          height={56}
        />
        <img
          src="/docs/assets/s2000-badge-on-dark.svg"
          alt="S2000 wordmark"
          className="s2000-badge"
          height={28}
        />
        <div>
          <h1>S2000 Digital Dash</h1>
          <p>Web cluster harness · AP1 / AP2 face styles · frozen JSON protocol</p>
        </div>
      </header>

      <main>
        <HarnessApp />
      </main>

      <footer className="colophon">
        <p>
          Selectable AP1 (straight TEMP/FUEL) or AP2 (arched side gauges) face.
          Not a product, not car-ready, not a replacement for the factory cluster.
        </p>
        <p>
          <a href="https://github.com/johnnyhuy/s2000-digital-dash">
            johnnyhuy/s2000-digital-dash
          </a>
          {" · "}
          <a href="/harness">/harness</a>
        </p>
      </footer>
    </div>
  );
}
