/** Faithful contour conversion of the supplied PNG, without generated lettering.
 * Uses sharp already bundled by Next.js. Run from frontend/ with the source path.
 */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import sharp from "sharp";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const directory = path.join(root, "public/branding");
const input = process.argv[2] || path.join(directory, "shift-reference.png");
const original = await fs.readFile(input);
const { data, info } = await sharp(original)
  .removeAlpha()
  .raw()
  .toBuffer({ resolveWithObject: true });
const { width, height, channels } = info;
const threshold = 110.5;
const value = (x, y) => data[(y * width + x) * channels];
const key = (p) => p.map((v) => v.toFixed(3)).join(",");
const points = new Map();
const graph = new Map();
function edge(a, b) {
  const va = value(...a),
    vb = value(...b);
  const t = (threshold - va) / (vb - va);
  return [a[0] + (b[0] - a[0]) * t + 0.5, a[1] + (b[1] - a[1]) * t + 0.5];
}
function connect(a, b) {
  const ka = key(a),
    kb = key(b);
  points.set(ka, a);
  points.set(kb, b);
  if (!graph.has(ka)) graph.set(ka, []);
  if (!graph.has(kb)) graph.set(kb, []);
  graph.get(ka).push(kb);
  graph.get(kb).push(ka);
}
for (let y = 0; y < height - 1; y++) {
  for (let x = 0; x < width - 1; x++) {
    const corners = [
      [x, y],
      [x + 1, y],
      [x + 1, y + 1],
      [x, y + 1],
    ];
    const crosses = [];
    for (let i = 0; i < 4; i++) {
      if (
        value(...corners[i]) >= threshold !==
        value(...corners[(i + 1) % 4]) >= threshold
      ) {
        crosses.push(edge(corners[i], corners[(i + 1) % 4]));
      }
    }
    if (crosses.length === 2) connect(...crosses);
    else if (crosses.length === 4)
      throw new Error(
        "Ambiguous contour; inspect the source rather than alter its geometry.",
      );
  }
}
function distance(p, a, b) {
  const dx = b[0] - a[0],
    dy = b[1] - a[1];
  const t = Math.max(
    0,
    Math.min(
      1,
      ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy || 1),
    ),
  );
  return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
}
function simplify(list, epsilon = 0.2) {
  if (list.length < 3) return list;
  let max = 0,
    index = 0;
  for (let i = 1; i < list.length - 1; i++) {
    const d = distance(list[i], list[0], list.at(-1));
    if (d > max) {
      max = d;
      index = i;
    }
  }
  return max > epsilon
    ? [
        ...simplify(list.slice(0, index + 1), epsilon).slice(0, -1),
        ...simplify(list.slice(index), epsilon),
      ]
    : [list[0], list.at(-1)];
}
const visited = new Set();
const contours = [];
for (const start of graph.keys()) {
  if (visited.has(start)) continue;
  const list = [];
  let current = start,
    previous = null;
  do {
    if (visited.has(current)) throw new Error("Open or overlapping contour");
    visited.add(current);
    list.push(points.get(current));
    const neighbors = graph.get(current);
    if (neighbors.length !== 2)
      throw new Error("Invalid outline; refusing to invent geometry");
    const next = neighbors.find((k) => k !== previous);
    previous = current;
    current = next;
  } while (current !== start);
  contours.push(simplify([...list, list[0]]).slice(0, -1));
}
contours.sort(
  (a, b) => Math.min(...a.map((p) => p[0])) - Math.min(...b.map((p) => p[0])),
);
if (contours.length !== 5)
  throw new Error(
    `Expected five source letter shapes, found ${contours.length}`,
  );
const all = contours.flat();
const left = Math.floor(Math.min(...all.map((p) => p[0]))),
  top = Math.floor(Math.min(...all.map((p) => p[1])));
const right = Math.ceil(Math.max(...all.map((p) => p[0]))),
  bottom = Math.ceil(Math.max(...all.map((p) => p[1])));
const padding = 16;
const outputWidth = right - left + padding * 2,
  outputHeight = bottom - top + padding * 2;
const draw = (offsetX, offsetY) =>
  contours
    .map(
      (c) =>
        "M" +
        c
          .map(
            (p) =>
              `${+(p[0] - offsetX).toFixed(2)},${+(p[1] - offsetY).toFixed(2)}`,
          )
          .join("L") +
        "Z",
    )
    .join("");
const shape = draw(left - padding, top - padding);
const css = await fs.readFile(path.join(root, "src/app/globals.css"), "utf8");
const token = (name) => {
  const color = css.match(
    new RegExp(`--${name}:\\s*(#[a-fA-F0-9]{6})\\s*;`),
  )?.[1];
  if (!color) throw new Error(`Missing semantic palette token ${name}`);
  return color;
};
const svg = (fill) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${outputWidth}" height="${outputHeight}" viewBox="0 0 ${outputWidth} ${outputHeight}" role="img" aria-label="SHIFT"><title>SHIFT</title><path fill="${fill}" fill-rule="evenodd" d="${shape}"/></svg>\n`;
// Compare silhouettes at original resolution before publishing any asset.
const check = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><path fill="white" fill-rule="evenodd" d="${draw(0, 0)}"/></svg>`;
const rendered = await sharp(Buffer.from(check)).ensureAlpha().raw().toBuffer();
let intersection = 0,
  union = 0;
for (let i = 0; i < width * height; i++) {
  const source = data[i * channels] >= threshold,
    vector = rendered[i * 4 + 3] >= 128;
  if (source && vector) intersection++;
  if (source || vector) union++;
}
const overlap = intersection / union;
if (overlap < 0.98) throw new Error(`Outline comparison failed: ${overlap}`);
await fs.mkdir(directory, { recursive: true });
await fs.writeFile(path.join(directory, "shift-reference.png"), original);
await fs.writeFile(path.join(directory, "shift-logo.svg"), svg(token("gold")));
await fs.writeFile(
  path.join(directory, "shift-logo-light.svg"),
  svg(token("primary-active")),
);
await fs.writeFile(
  path.join(directory, "shift-logo.manifest.json"),
  JSON.stringify(
    {
      width: outputWidth,
      height: outputHeight,
      variants: {
        dark: "/branding/shift-logo.svg",
        light: "/branding/shift-logo-light.svg",
      },
      source: {
        file: "shift-reference.png",
        sha256: createHash("sha256").update(original).digest("hex"),
        width,
        height,
        transparent: false,
      },
      conversion: {
        method: "Source-pixel contour trace; no generated typography",
        threshold,
        simplification_pixels: 0.2,
        clear_space_pixels: padding,
        letter_contours: contours.length,
        silhouette_overlap: overlap,
      },
    },
    null,
    2,
  ) + "\n",
);
console.log(
  JSON.stringify({
    width: outputWidth,
    height: outputHeight,
    letter_contours: contours.length,
    silhouette_overlap: overlap,
  }),
);
