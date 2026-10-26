/* eslint-disable @typescript-eslint/no-require-imports -- Compile the real TSX with Next's installed compiler. */
const fs = require("node:fs");
const path = require("node:path");
const Module = require("node:module");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const { transformSync } = require("next/dist/build/swc");

const root = path.resolve(__dirname, "..");
const resolve = Module._resolveFilename;
Module._resolveFilename = function (request, parent, ...rest) {
  return resolve.call(this, request.startsWith("@/") ? path.join(root, request.slice(2)) : request, parent, ...rest);
};
for (const extension of [".ts", ".tsx"]) {
  require.extensions[extension] = (module, filename) => {
    const output = transformSync(fs.readFileSync(filename, "utf8"), {
      filename, module: { type: "commonjs" },
      jsc: { target: "es2022", parser: { syntax: "typescript", tsx: extension === ".tsx" },
        transform: { react: { runtime: "automatic" } } },
    });
    module._compile(output.code, filename);
  };
}
const { ClusterFace } = require("../components/ClusterFace.tsx");
const face = { rpm: 6420, speed_kmh: 98, fuel_pct: 41, ect_c: 89, batt_v: 14.05,
  odo_km: 142857.3, trip_km: 128.4, lamps: { turn_l: true, high_beam: true } };
const render = (rpm) => renderToStaticMarkup(React.createElement(ClusterFace, { face: { ...face, rpm } }));
const tach = (rpm) => render(rpm).match(/<g[^>]*class="tach-fill"[^>]*>(.*?)<\/g>/s)?.[1] || "";
for (const [low, high, next] of [[0, 199.9, 200], [3200, 3399.9, 3400], [8000, 8199.9, 8200]]) {
  assert.equal(tach(low), tach(high));
  assert.notEqual(tach(high), tach(next));
}
assert.equal((render(6420).match(/viewBox="0 0 (?:49|18|47|46|48|43) 43"/g) || []).length, 10);
if (process.argv[2] && process.argv[2] !== "--check") {
  const dest = path.resolve(process.argv[2]);
  fs.mkdirSync(dest, { recursive: true });
  const markup = render(6420);
  const svg = markup.slice(markup.indexOf("<svg "), markup.lastIndexOf("</svg>") + 6)
    .replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="444" ');
  fs.writeFileSync(path.join(dest, "ap1-live.svg"), svg + "\n");
  fs.writeFileSync(path.join(dest, "ap1-live.json"), JSON.stringify({
    svg_sha256: crypto.createHash("sha256").update(svg + "\n").digest("hex"),
    ui_module: [0, 18 + (444 - (1000 / 2.35 + 18)) / 2, 1000, 1000 / 2.35],
    style: "ap1", capture_method: "React server renderer; SVG rasterization, no browser CSS",
  }, null, 2) + "\n");
  // SDL's SVG loader does not support nested viewports. Next already depends
  // on sharp/librsvg, which renders the actual nested glyph/icon SVGs.
  require("sharp")(Buffer.from(svg)).png().toFile(path.join(dest, "ap1-live.png")).then(() => {
    const filename = path.join(dest, "ap1-live.json");
    const metadata = JSON.parse(fs.readFileSync(filename, "utf8"));
    metadata.image_sha256 = crypto.createHash("sha256").update(fs.readFileSync(path.join(dest, "ap1-live.png"))).digest("hex");
    fs.writeFileSync(filename, JSON.stringify(metadata, null, 2) + "\n");
  }).catch((error) => {
    process.stderr.write(String(error) + "\n"); process.exitCode = 1;
  });
}
process.stdout.write("React SVG capture and discrete-cell checks passed\n");
