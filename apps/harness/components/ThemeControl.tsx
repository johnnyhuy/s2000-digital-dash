"use client";

import { useEffect, useState } from "react";

type Theme = "system" | "light" | "dark";
const key = "s2000-web-theme";

export function ThemeControl() {
  const [theme, setTheme] = useState<Theme>("system");
  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      try {
        const saved = localStorage.getItem(key);
        if (saved === "light" || saved === "dark") {
          document.documentElement.dataset.theme = saved;
          setTheme(saved);
        }
      } catch { /* System theme also works with storage disabled. */ }
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function change(next: Theme) {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem(key, next); } catch { /* Session-only choice. */ }
  }

  return <label className="theme-control">Appearance
    <select aria-label="Appearance" value={theme} onChange={(e) => change(e.target.value as Theme)}>
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
  </label>;
}
