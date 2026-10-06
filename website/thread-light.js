/** Independent Canvas2D recreation of the supplied thread-light hatch preset.
 * No photographs, video textures, shader libraries, or remote runtime assets.
 */
export const clamp = (value, min = 0, max = 1) =>
  Math.min(max, Math.max(min, value));
const mix = (a, b, amount) => a + (b - a) * amount;
const smooth = (value) => value * value * (3 - 2 * value);

export function hash(x, y, seed = 1) {
  let n =
    Math.imul(x | 0, 374761393) ^
    Math.imul(y | 0, 668265263) ^
    Math.imul(seed | 0, 1442695041);
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  return ((n ^ (n >>> 16)) >>> 0) / 4294967295;
}

export function valueNoise(x, y, seed = 1) {
  const ix = Math.floor(x),
    iy = Math.floor(y);
  const u = smooth(x - ix),
    v = smooth(y - iy);
  return mix(
    mix(hash(ix, iy, seed), hash(ix + 1, iy, seed), u),
    mix(hash(ix, iy + 1, seed), hash(ix + 1, iy + 1, seed), u),
    v,
  );
}

export function fbm(x, y, seed = 1, octaves = 4) {
  let value = 0,
    amplitude = 0.5,
    total = 0;
  for (let octave = 0; octave < octaves; octave++) {
    value += valueNoise(x, y, seed + octave * 17) * amplitude;
    total += amplitude;
    // Rotate each octave so grid axes do not become visible in the smoke.
    const nextX = x * 1.6 + y * 1.2 + 13.7;
    y = y * 1.6 - x * 1.2 + 8.9;
    x = nextX;
    amplitude *= 0.5;
  }
  return value / total;
}

export const luminance = (r, g, b) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

/** Average every source pixel in a cell, including partial boundary cells. */
export function averageCell(data, width, height, x, y, size) {
  let r = 0,
    g = 0,
    b = 0,
    count = 0;
  for (let row = y; row < Math.min(height, y + size); row++) {
    for (let column = x; column < Math.min(width, x + size); column++) {
      const offset = (row * width + column) * 4;
      r += data[offset];
      g += data[offset + 1];
      b += data[offset + 2];
      count++;
    }
  }
  return count ? [r / count, g / count, b / count] : [0, 0, 0];
}

/** Adjust a raster color in the requested brightness → contrast → saturation
 * → grayscale → tint order. Blur is a later canvas pass (off in this recipe).
 */
export function adjustColor(r, g, b, recipe) {
  const brightness = recipe.brightness * 2.55;
  const contrast = recipe.contrast / 100;
  r = clamp((r + brightness - 127.5) * contrast + 127.5, 0, 255);
  g = clamp((g + brightness - 127.5) * contrast + 127.5, 0, 255);
  b = clamp((b + brightness - 127.5) * contrast + 127.5, 0, 255);
  const gray = luminance(r, g, b);
  const saturation = recipe.saturation / 100;
  r = mix(gray, r, saturation);
  g = mix(gray, g, saturation);
  b = mix(gray, b, saturation);
  const grayscale = recipe.grayscale / 100;
  const grayAfterSaturation = luminance(r, g, b);
  r = mix(r, grayAfterSaturation, grayscale);
  g = mix(g, grayAfterSaturation, grayscale);
  b = mix(b, grayAfterSaturation, grayscale);
  if (recipe.tintOpacity > 0) {
    const tint = parseColor(recipe.tint),
      amount = recipe.tintOpacity / 100;
    const blend =
      recipe.overlayBlend === "multiply"
        ? (channel, color) => (channel * color) / 255
        : (channel, color) => color;
    r = mix(r, blend(r, tint[0]), amount);
    g = mix(g, blend(g, tint[1]), amount);
    b = mix(b, blend(b, tint[2]), amount);
  }
  return [r, g, b];
}

function parseColor(hex) {
  return [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
}

export function spotlight(x, y, pointer, source) {
  if (!pointer || !source.mouseReactive || source.cursorEffect !== "spotlight")
    return 0;
  const radius = Math.max(0.01, source.cursorRadius / 100);
  const distance =
    ((x - pointer.x) ** 2 + (y - pointer.y) ** 2) / (radius * radius);
  return Math.exp(-distance * 5) * (source.cursorStrength / 100) * 0.3;
}

function smoke(x, y, time, source) {
  const scale = (3.3 * 100) / source.zoom;
  const angle = (source.rotate * Math.PI) / 180;
  const rx = x * Math.cos(angle) - y * Math.sin(angle);
  const ry = x * Math.sin(angle) + y * Math.cos(angle);
  const px = rx * scale + source.offsetX / 100;
  const py = ry * scale + source.offsetY / 100;
  const t = source.animated
    ? time * (source.speed / 100) * 0.19 * (source.motionReverse ? -1 : 1)
    : 0;
  const warp = (source.warp / 100) * 4.7;
  const qx = fbm(px + t * 0.25, py - t * 0.12, source.seed, 3);
  const qy = fbm(px + 5.2 - t * 0.18, py + 1.3 + t * 0.2, source.seed + 31, 3);
  const octaves = 2 + Math.round(source.detail / 25);
  const cloud = fbm(
    px + warp * qx + t * 0.15,
    py + warp * qy - t * 0.19,
    source.seed + 67,
    octaves,
  );
  // A second turbulent ridge creates thin folds inside the broad smoke masses.
  const ridge =
    1 -
    Math.abs(
      2 *
        valueNoise(
          px * 2.4 + qy * 3,
          py * 2.4 + qx * 3 + t,
          source.seed + 101,
        ) -
        1,
    );
  const field =
    (cloud - 0.43) * 2.8 + ridge * (source.paramA / 100) * 0.26 + 0.38;
  return clamp(
    (field - 0.5) * (source.contrast / 50) * (source.intensity / 50) +
      0.5 +
      (source.brightness - 50) / 100,
  );
}

export {
  createThreadLight,
  createRasterRenderer,
  RENDER_MODES,
} from "./renderer.js";
