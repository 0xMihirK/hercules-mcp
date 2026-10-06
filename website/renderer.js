/** Independent 2D raster pipeline. Definitions and source provenance: README.md. */
import {
  clamp,
  hash,
  fbm,
  averageCell,
  luminance,
  spotlight,
  adjustColor,
} from "./thread-light.js";
export const RENDER_MODES = [
  "characters",
  "dither",
  "mosaic",
  "pixel",
  "dots",
  "cross",
  "diamond",
  "voxel",
  "lego",
  "mixed",
  "lines",
  "diagonal",
  "braille",
  "disco",
  "hexdump",
  "matrix",
  "rings",
  "hearts",
  "stars",
  "hexagons",
  "triangles",
  "bubbles",
  "hatch",
  "contour",
  "halfblocks",
];
const ramps = {
  standard: " .:-=+*#%@",
  blocks: " ░▒▓█",
  binary: " 01",
  code: " .:;{}[]<>/\\#@",
};
const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const blend = (a, b, t) => a + (b - a) * t;
const makeCanvas = () =>
  typeof document !== "undefined"
    ? document.createElement("canvas")
    : new OffscreenCanvas(1, 1);
const bayer = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5];
export function averageRect(data, width, height, x, y, w, h) {
  let r = 0,
    g = 0,
    b = 0,
    count = 0;
  for (
    let row = Math.max(0, Math.floor(y));
    row < Math.min(height, y + h);
    row++
  )
    for (
      let col = Math.max(0, Math.floor(x));
      col < Math.min(width, x + w);
      col++
    ) {
      const o = (row * width + col) * 4;
      r += data[o];
      g += data[o + 1];
      b += data[o + 2];
      count++;
    }
  return count ? [r / count, g / count, b / count] : [0, 0, 0];
}
export function animatedLuminance(light, x, y, time, recipe) {
  const amount = recipe.animIntensity?.enabled
    ? recipe.animIntensity.intensity / 100
    : 0;
  if (!recipe.animated || !amount) return light;
  const styles = {
    wave: Math.sin(time * 1.3 + x * 0.035 + y * 0.018),
    pulse: Math.sin(time * 1.7),
    shimmer: Math.sin(time * 2.3 + hash(x, y, 53) * Math.PI * 2),
    ripple: Math.sin(Math.hypot(x, y) * 0.045 - time * 2),
    flicker: hash(x, y, Math.floor(time * 12) + 1) * 2 - 1,
  };
  return clamp(
    light + (styles[recipe.animStyle] ?? styles.shimmer) * amount * 0.09,
  );
}
export function cellLuminance(light, edge, recipe) {
  const inverted = recipe.invert ? 1 - light : light;
  return clamp(
    inverted +
      (recipe.density / 100) * (1 - inverted) * 0.5 +
      (edge * recipe.edgeEmphasis) / 100,
  );
}
export function createRasterRenderer(canvas, recipe, size) {
  if (!RENDER_MODES.includes(recipe.renderMode))
    throw Error(`Unknown renderMode: ${recipe.renderMode}`);
  if (recipe.shaderSource.preset !== "smoke")
    throw Error("Only the supplied procedural smoke source is supported.");
  const ctx = canvas.getContext("2d", { alpha: true });
  if (!ctx) throw Error("Canvas2D unavailable");
  const source = makeCanvas(),
    field = makeCanvas(),
    effect = makeCanvas(),
    scratch = makeCanvas(),
    post = makeCanvas();
  const sc = source.getContext("2d", { willReadFrequently: true }),
    fc = field.getContext("2d");
  const ec = effect.getContext("2d"),
    tc = scratch.getContext("2d"),
    pc = post.getContext("2d");
  let width = 1,
    height = 1,
    resolution = 160,
    image,
    hatchImage,
    mask = null,
    destroyed = false,
    renderedFrames = 0,
    averageCost = 0,
    timings = {};
  const hatchTiles = new Map();
  const palette = recipe.shaderSource.colors.map(rgb);
  let ready = Promise.resolve();
  if (recipe.mask?.enabled && recipe.mask.dataUrl) {
    if (typeof Image !== "undefined") {
      ready = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
          mask = img;
          resolve();
        };
        img.onerror = reject;
        img.src = recipe.mask.dataUrl;
      });
    } else
      ready = fetch(recipe.mask.dataUrl)
        .then((r) => r.blob())
        .then(createImageBitmap)
        .then((img) => {
          mask = img;
        });
  }
  function resize(w, h) {
    width = Math.max(1, Math.round(w));
    height = Math.max(1, Math.round(h));
    for (const c of [canvas, source, effect, scratch, post]) {
      c.width = width;
      c.height = height;
    }
    field.width = Math.min(width, resolution);
    field.height = Math.max(1, Math.round((height * field.width) / width));
    image = fc.createImageData(field.width, field.height);
    hatchImage = ec.createImageData(width, height);
  }
  function sourceRaster(time, pointer) {
    const s = recipe.shaderSource,
      data = image.data,
      aspect = width / height,
      theta = ((s.rotate || 0) * Math.PI) / 180;
    const t = s.animated
      ? ((time * s.speed) / 100) * 0.19 * (s.motionReverse ? -1 : 1)
      : 0;
    for (let y = 0; y < field.height; y++)
      for (let x = 0; x < field.width; x++) {
        const nx = x / field.width,
          ny = y / field.height,
          ax = (nx - 0.5) * aspect,
          ay = ny - 0.5;
        const scale = (3.3 * 100) / Math.max(1, s.zoom),
          px =
            (ax * Math.cos(theta) - ay * Math.sin(theta)) * scale +
            s.offsetX / 100 +
            (t * (s.drift || 0)) / 100,
          py =
            (ax * Math.sin(theta) + ay * Math.cos(theta)) * scale +
            s.offsetY / 100;
        const qx = fbm(px + t * 0.25, py - t * 0.12, s.seed, 3),
          qy = fbm(px + 5.2 - t * 0.18, py + 1.3 + t * 0.2, s.seed + 31, 3);
        const cloud = fbm(
          px + (s.warp / 100) * 4.7 * qx + t * 0.15,
          py + (s.warp / 100) * 4.7 * qy - t * 0.19,
          s.seed + 67,
          2 + Math.round(s.detail / 25),
        );
        const ridge =
          1 -
          Math.abs(
            2 * fbm(px * 2.4 + qy * 3, py * 2.4 + qx * 3 + t, s.seed + 101, 2) -
              1,
          );
        let value = clamp(
          (((((cloud - 0.43) * 2.8 +
            ((ridge * s.paramA) / 100) * 0.26 +
            0.38 -
            0.5) *
            s.contrast) /
            50) *
            s.intensity) /
            50 +
            0.5 +
            (s.brightness - 50) / 100,
        );
        value = clamp(
          value +
            ((hash(x, y, s.seed + 223) - 0.5) * s.grain) / 250 +
            spotlight(nx, ny, pointer, s),
        );
        value *=
          1 -
          ((s.vignette || 0) / 100) *
            clamp(Math.hypot(nx - 0.5, ny - 0.5) * 1.4);
        const stop = value * (palette.length - 1),
          lower = Math.min(palette.length - 2, Math.floor(stop)),
          a = stop - lower,
          o = (y * field.width + x) * 4;
        const color = palette[lower].map((v, c) =>
            blend(v, palette[lower + 1][c], a),
          ),
          gray = luminance(...color);
        for (let c = 0; c < 3; c++)
          data[o + c] = clamp(blend(gray, color[c], s.saturation / 50), 0, 255);
        data[o + 3] = 255;
      }
    fc.putImageData(image, 0, 0);
    sc.clearRect(0, 0, width, height);
    sc.filter = `hue-rotate(${s.hue || 0}deg) blur(${(s.blur || 0) / 5}px)`;
    sc.drawImage(field, 0, 0, width, height);
    sc.filter = "none";
  }
  function primitive(mode, x, y, s, l, color, time, sampled) {
    const cx = x + s / 2,
      cy = y + s / 2,
      r = s * 0.45 * (0.18 + l * 0.82),
      seed = recipe.shaderSource.seed;
    ec.fillStyle = `rgb(${color.join(",")})`;
    ec.strokeStyle = ec.fillStyle;
    ec.lineWidth = 0.6 + l * 0.7;
    ec.beginPath();
    const polygon = (n, radius, rotation = 0) => {
      for (let i = 0; i < n; i++) {
        const a = rotation + (i * Math.PI * 2) / n;
        const px = cx + Math.cos(a) * radius,
          py = cy + Math.sin(a) * radius;
        i ? ec.lineTo(px, py) : ec.moveTo(px, py);
      }
      ec.closePath();
    };
    if (mode === "mixed" || mode === "disco") {
      const choices = ["dots", "cross", "diamond", "stars", "pixel"];
      return primitive(
        choices[
          Math.floor(
            hash(x, y, seed + (mode === "disco" ? Math.floor(time * 2) : 0)) *
              choices.length,
          )
        ],
        x,
        y,
        s,
        l,
        color,
        time,
        sampled,
      );
    }
    if (
      mode === "characters" ||
      mode === "hexdump" ||
      mode === "matrix" ||
      mode === "braille" ||
      mode === "halfblocks"
    ) {
      ec.textAlign = "center";
      ec.textBaseline = "middle";
      ec.font = `${s * (mode === "braille" ? 1.25 : 1)}px monospace`;
      let glyph = "";
      if (mode === "characters") {
        const chars =
          recipe.charSet === "custom"
            ? recipe.customChars || ramps.standard
            : ramps[recipe.charSet] || ramps.standard;
        glyph = chars[Math.min(chars.length - 1, Math.floor(l * chars.length))];
      }
      if (mode === "hexdump")
        glyph = "0123456789ABCDEF"[Math.min(15, Math.floor(l * 16))];
      if (mode === "matrix") {
        const col = Math.floor(x / s),
          head =
            (time * 8 + (hash(col, 0, seed) * height) / s) % (height / s + 12),
          tail = (head - y / s + height / s + 12) % (height / s + 12);
        if (tail > 12) return;
        ec.globalAlpha = l * (1 - tail / 13);
        ec.fillStyle = tail < 1 ? "#d7ffdb" : "#00dd64";
        glyph = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[
          Math.floor(hash(x, y, Math.floor(time * 5) + seed) * 36)
        ];
      }
      if (mode === "braille") {
        let bits = 0;
        const order = [0, 3, 1, 4, 2, 5, 6, 7];
        for (let row = 0; row < 4; row++)
          for (let col = 0; col < 2; col++) {
            const c = averageCell(
              sampled,
              width,
              height,
              x + (col * s) / 2,
              y + (row * s) / 4,
              Math.max(1, Math.round(s / 4)),
            );
            if (luminance(...c) / 255 > 0.3) bits |= 1 << order[row * 2 + col];
          }
        glyph = String.fromCharCode(0x2800 + bits);
      }
      if (mode === "halfblocks") {
        const a = averageRect(sampled, width, height, x, y, s, s / 2),
          b = averageRect(sampled, width, height, x, y + s / 2, s, s / 2);
        ec.fillStyle = `rgb(${a.join(",")})`;
        ec.fillRect(x, y, s, s / 2);
        ec.fillStyle = `rgb(${b.join(",")})`;
        ec.fillRect(x, y + s / 2, s, s / 2);
        return;
      }
      ec.fillText(glyph, cx, cy);
      ec.globalAlpha = 1;
      return;
    }
    if (mode === "dither") {
      if (
        l >
        (bayer[(Math.floor(y / s) % 4) * 4 + (Math.floor(x / s) % 4)] + 0.5) /
          16
      )
        ec.fillRect(x, y, s, s);
      return;
    }
    if (mode === "pixel" || mode === "mosaic") {
      ec.globalAlpha = l;
      ec.fillRect(
        x + (mode === "mosaic" ? 0.5 : 0),
        y + (mode === "mosaic" ? 0.5 : 0),
        s - (mode === "mosaic" ? 1 : 0),
        s - (mode === "mosaic" ? 1 : 0),
      );
      ec.globalAlpha = 1;
      return;
    }
    if (mode === "dots" || mode === "rings" || mode === "bubbles") {
      ec.arc(cx, cy, r, 0, Math.PI * 2);
      if (mode === "dots") ec.fill();
      else {
        ec.stroke();
        if (mode === "bubbles") {
          ec.globalAlpha = 0.3;
          ec.fill();
          ec.globalAlpha = 1;
          ec.beginPath();
          ec.arc(cx - r * 0.3, cy - r * 0.3, r * 0.25, 0, Math.PI * 2);
          ec.fill();
        }
      }
      return;
    }
    if (mode === "cross") {
      ec.moveTo(cx - r, cy);
      ec.lineTo(cx + r, cy);
      ec.moveTo(cx, cy - r);
      ec.lineTo(cx, cy + r);
      ec.stroke();
      return;
    }
    if (mode === "diamond" || mode === "hexagons") {
      polygon(
        mode === "diamond" ? 4 : 6,
        r,
        mode === "diamond" ? Math.PI / 2 : Math.PI / 6,
      );
      ec.fill();
      return;
    }
    if (mode === "stars") {
      for (let i = 0; i < 10; i++) {
        const a = (i * Math.PI) / 5 - Math.PI / 2,
          rr = i % 2 ? r * 0.4 : r;
        i
          ? ec.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr)
          : ec.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr);
      }
      ec.closePath();
      ec.fill();
      return;
    }
    if (mode === "hearts") {
      ec.moveTo(cx, cy + r);
      ec.bezierCurveTo(cx - r * 2, cy, cx - r, cy - r * 1.5, cx, cy - r * 0.4);
      ec.bezierCurveTo(cx + r, cy - r * 1.5, cx + r * 2, cy, cx, cy + r);
      ec.fill();
      return;
    }
    if (mode === "triangles") {
      ec.moveTo(x, y);
      ec.lineTo(x + s, y);
      ec.lineTo(x, y + s);
      ec.closePath();
      ec.fill();
      ec.globalAlpha = 0.55;
      ec.beginPath();
      ec.moveTo(x + s, y);
      ec.lineTo(x + s, y + s);
      ec.lineTo(x, y + s);
      ec.closePath();
      ec.fill();
      ec.globalAlpha = 1;
      return;
    }
    if (mode === "voxel") {
      polygon(6, r, Math.PI / 6);
      ec.fill();
      ec.strokeStyle = "rgba(0,0,0,.4)";
      ec.moveTo(cx, cy);
      ec.lineTo(cx, cy + r);
      ec.moveTo(cx, cy);
      ec.lineTo(cx + r * 0.86, cy - r * 0.5);
      ec.moveTo(cx, cy);
      ec.lineTo(cx - r * 0.86, cy - r * 0.5);
      ec.stroke();
      return;
    }
    if (mode === "lego") {
      ec.fillRect(x + 0.5, y + 0.5, s - 1, s - 1);
      ec.fillStyle = "rgba(255,255,255,.25)";
      ec.beginPath();
      ec.arc(cx, cy, s * 0.24, 0, Math.PI * 2);
      ec.fill();
      ec.strokeStyle = "rgba(0,0,0,.5)";
      ec.stroke();
      return;
    }
    if (mode === "contour") {
      const right = averageCell(
          sampled,
          width,
          height,
          Math.min(width - 1, x + s),
          y,
          s,
        ),
        down = averageCell(
          sampled,
          width,
          height,
          x,
          Math.min(height - 1, y + s),
          s,
        );
      for (let level = 0.125; level < 1; level += 0.125) {
        const a = luminance(...right) / 255,
          b = luminance(...down) / 255;
        if ((l - level) * (a - level) < 0) {
          const t = (level - l) / (a - l);
          ec.moveTo(x + s * t, y);
          ec.lineTo(x + s * t, y + s);
        }
        if ((l - level) * (b - level) < 0) {
          const t = (level - l) / (b - l);
          ec.moveTo(x, y + s * t);
          ec.lineTo(x + s, y + s * t);
        }
      }
      ec.stroke();
      return;
    }
    if (mode === "hatch") {
      ec.fillStyle = `rgba(${color.join(",")},.30)`;
      ec.fillRect(x, y, s, s);
      ec.fillStyle = ec.strokeStyle;
    }
    const count = Math.max(1, Math.round(1 + l * 4 + recipe.density / 25)),
      length = s * (0.3 + l * 0.7);
    for (let i = 0; i < count; i++) {
      const d = (i * s) / count;
      if (mode === "lines") {
        ec.moveTo(x, y + d);
        ec.lineTo(x + length, y + d);
      } else {
        ec.moveTo(x + d, y);
        ec.lineTo(x + Math.min(s, d + length), y + Math.min(length, s - d));
        if (mode === "hatch" && l > 0.34) {
          ec.moveTo(x, y + d);
          ec.lineTo(x + Math.min(length, s - d), y + Math.min(s, d + length));
        }
      }
    }
    if (mode === "hatch" && l > 0.62) {
      ec.moveTo(x, y + s);
      ec.lineTo(x + s, y);
    }
    ec.stroke();
  }
  function adjusted() {
    tc.clearRect(0, 0, width, height);
    const raster = ec.getImageData(0, 0, width, height),
      data = raster.data,
      lut = new Float32Array(256),
      sat = (recipe.saturation / 100) * (1 - recipe.grayscale / 100);
    for (let i = 0; i < 256; i++)
      lut[i] = clamp(
        ((i + recipe.brightness * 2.55 - 127.5) * recipe.contrast) / 100 +
          127.5,
        0,
        255,
      );
    const curve = recipe.toneCurve || [
        { x: 0, y: 0 },
        { x: 1, y: 1 },
      ],
      nonlinear = curve.some((point) => point.x !== point.y);
    const tone = (value) => {
      const v = value / 255;
      let index = 1;
      while (index < curve.length - 1 && curve[index].x < v) index++;
      const a = curve[index - 1],
        b = curve[index];
      return (
        clamp(blend(a.y, b.y, (v - a.x) / Math.max(0.0001, b.x - a.x))) * 255
      );
    };
    for (let o = 0; o < data.length; o += 4) {
      if (!data[o + 3]) continue;
      const r = lut[data[o]],
        g = lut[data[o + 1]],
        b = lut[data[o + 2]],
        gray = luminance(r, g, b);
      data[o] = nonlinear
        ? tone(gray + (r - gray) * sat)
        : gray + (r - gray) * sat;
      data[o + 1] = nonlinear
        ? tone(gray + (g - gray) * sat)
        : gray + (g - gray) * sat;
      data[o + 2] = nonlinear
        ? tone(gray + (b - gray) * sat)
        : gray + (b - gray) * sat;
    }
    tc.putImageData(raster, 0, 0);
    if (recipe.tintOpacity > 0) {
      tc.globalCompositeOperation = recipe.overlayBlend;
      tc.globalAlpha = recipe.tintOpacity / 100;
      tc.fillStyle = recipe.tint;
      tc.fillRect(0, 0, width, height);
      tc.globalAlpha = 1;
      tc.globalCompositeOperation = "source-over";
    }
    ec.clearRect(0, 0, width, height);
    ec.drawImage(scratch, 0, 0);
    const amount = recipe.blurAmount / 4,
      type = recipe.blurType;
    if (type === "off" || !amount) return;
    pc.clearRect(0, 0, width, height);
    if (
      type === "gaussian" ||
      type === "lens" ||
      type === "tilt-shift" ||
      type === "tiltShift" ||
      type === "progressive"
    ) {
      pc.filter = `blur(${amount}px)`;
      pc.drawImage(scratch, 0, 0);
      pc.filter = "none";
      if (type !== "gaussian") {
        pc.globalCompositeOperation = "destination-out";
        let gradient;
        if (type === "lens") {
          const r = (Math.min(width, height) * (recipe.lensFocus || 40)) / 100;
          gradient = pc.createRadialGradient(
            (width * recipe.blurCenterX) / 100,
            (height * recipe.blurCenterY) / 100,
            0,
            (width * recipe.blurCenterX) / 100,
            (height * recipe.blurCenterY) / 100,
            r,
          );
          gradient.addColorStop(0, "#000");
          gradient.addColorStop(0.65, "#000");
          gradient.addColorStop(1, "transparent");
        } else {
          gradient = pc.createLinearGradient(0, 0, 0, height);
          const center =
            (type === "progressive"
              ? recipe.progressivePosition
              : recipe.tiltPosition) / 100;
          if (type === "progressive") {
            gradient.addColorStop(
              0,
              recipe.progressiveReverse ? "transparent" : "#000",
            );
            gradient.addColorStop(
              clamp(center),
              recipe.progressiveReverse ? "#000" : "transparent",
            );
            gradient.addColorStop(
              1,
              recipe.progressiveReverse ? "#000" : "transparent",
            );
          } else {
            const span = (recipe.tiltFocus || 35) / 200,
              feather = (recipe.tiltFeather || 15) / 100;
            gradient.addColorStop(0, "transparent");
            gradient.addColorStop(
              clamp(center - span - feather),
              "transparent",
            );
            gradient.addColorStop(clamp(center - span), "#000");
            gradient.addColorStop(clamp(center + span), "#000");
            gradient.addColorStop(
              clamp(center + span + feather),
              "transparent",
            );
            gradient.addColorStop(1, "transparent");
          }
        }
        pc.fillStyle = gradient;
        pc.fillRect(0, 0, width, height);
        pc.globalCompositeOperation = "source-over";
      }
    } else {
      const cx = (width * recipe.blurCenterX) / 100,
        cy = (height * recipe.blurCenterY) / 100;
      for (let i = -5; i <= 5; i++) {
        pc.save();
        pc.globalAlpha = 1 / 11;
        if (type === "directional") {
          const a = (recipe.blurAngle * Math.PI) / 180,
            shift = recipe.directionalBothSides ? i : i + 5;
          pc.translate(
            ((shift * amount) / 5) * Math.cos(a),
            ((shift * amount) / 5) * Math.sin(a),
          );
        } else {
          pc.translate(cx, cy);
          if (type === "spin") pc.rotate((i * amount) / 1500);
          else pc.scale(1 + (i * amount) / 1000, 1 + (i * amount) / 1000);
          pc.translate(-cx, -cy);
        }
        pc.drawImage(scratch, 0, 0);
        pc.restore();
      }
    }
    if (
      type === "lens" ||
      type === "tilt-shift" ||
      type === "tiltShift" ||
      type === "progressive"
    )
      ec.drawImage(post, 0, 0);
    else {
      ec.clearRect(0, 0, width, height);
      ec.drawImage(post, 0, 0);
    }
  }
  function snapshot() {
    tc.clearRect(0, 0, width, height);
    tc.drawImage(effect, 0, 0);
  }
  function effects(time) {
    for (const key of [
      "scanLines",
      "vignette",
      "bloom",
      "chromatic",
      "filmGrain",
      "glitch",
      "halftone",
      "pixelate",
      "filmDust",
    ]) {
      const fx = recipe.pfx[key];
      if (!fx?.enabled || !fx.intensity) continue;
      const a = fx.intensity / 100;
      ec.save();
      if (key === "scanLines") {
        ec.fillStyle = `rgba(0,0,0,${a * 0.65})`;
        for (let y = (time * 8) % 4; y < height; y += 4)
          ec.fillRect(0, y, width, 1);
      }
      if (key === "vignette") {
        const g = ec.createRadialGradient(
          width / 2,
          height / 2,
          Math.min(width, height) * 0.18,
          width / 2,
          height / 2,
          Math.max(width, height) * 0.65,
        );
        g.addColorStop(0, "transparent");
        g.addColorStop(1, `rgba(0,0,0,${a})`);
        ec.fillStyle = g;
        ec.fillRect(0, 0, width, height);
      }
      if (key === "bloom") {
        snapshot();
        ec.globalCompositeOperation = "screen";
        ec.globalAlpha = a * 0.7;
        ec.filter = `blur(${3 + a * 12}px)`;
        ec.drawImage(scratch, 0, 0);
        ec.filter = "none";
      }
      if (key === "chromatic") {
        const original = ec.getImageData(0, 0, width, height),
          separated = ec.createImageData(width, height),
          shift = Math.max(1, Math.round(a * 6));
        for (let y = 0; y < height; y++)
          for (let x = 0; x < width; x++) {
            const o = (y * width + x) * 4,
              red = (y * width + clamp(x - shift, 0, width - 1)) * 4,
              blue = (y * width + clamp(x + shift, 0, width - 1)) * 4;
            separated.data[o] = original.data[red];
            separated.data[o + 1] = original.data[o + 1];
            separated.data[o + 2] = original.data[blue + 2];
            separated.data[o + 3] = Math.max(
              original.data[red + 3],
              original.data[o + 3],
              original.data[blue + 3],
            );
          }
        ec.putImageData(separated, 0, 0);
      }
      if (key === "filmGrain") {
        const tick = Math.floor(time * 18);
        for (let i = 0; i < (width * height) / 80; i++) {
          const x = hash(i, 1, tick) * width,
            y = hash(i, 2, tick) * height;
          ec.fillStyle = `rgba(${i % 2 ? "255,255,255" : "0,0,0"},${a * 0.3})`;
          ec.fillRect(x, y, 1.5, 1.5);
        }
      }
      if (key === "glitch") {
        snapshot();
        for (let i = 0; i < 5; i++) {
          const tick = Math.floor(time * 8),
            y = hash(i, 0, tick) * height,
            h = 2 + hash(i, 1, tick) * 20,
            shift = (hash(i, 2, tick) - 0.5) * a * width * 0.12;
          ec.drawImage(scratch, 0, y, width, h, shift, y, width, h);
        }
      }
      if (key === "halftone") {
        const gap = Math.max(3, Math.round(recipe.cellSize / 2)),
          tile = makeCanvas();
        tile.width = tile.height = gap;
        const tileCtx = tile.getContext("2d");
        tileCtx.fillStyle = `rgba(0,0,0,${a * 0.8})`;
        tileCtx.beginPath();
        tileCtx.arc(gap / 2, gap / 2, 0.7, 0, Math.PI * 2);
        tileCtx.fill();
        ec.fillStyle = ec.createPattern(tile, "repeat");
        ec.fillRect(0, 0, width, height);
      }
      if (key === "pixelate") {
        snapshot();
        const block = 2 + Math.round(a * 14);
        pc.clearRect(0, 0, width, height);
        pc.imageSmoothingEnabled = false;
        pc.drawImage(
          scratch,
          0,
          0,
          Math.ceil(width / block),
          Math.ceil(height / block),
        );
        ec.imageSmoothingEnabled = false;
        ec.clearRect(0, 0, width, height);
        ec.drawImage(
          post,
          0,
          0,
          Math.ceil(width / block),
          Math.ceil(height / block),
          0,
          0,
          width,
          height,
        );
        ec.imageSmoothingEnabled = true;
      }
      if (key === "filmDust") {
        const tick = Math.floor(time * 3);
        ec.fillStyle = `rgba(235,228,215,${a * 0.65})`;
        ec.strokeStyle = ec.fillStyle;
        for (let i = 0; i < 30 * a; i++) {
          const x = hash(i, 0, tick + 77) * width,
            y = hash(i, 1, tick + 77) * height;
          ec.beginPath();
          ec.arc(x, y, hash(i, 2, tick) * 2 + 0.4, 0, Math.PI * 2);
          ec.fill();
          if (i % 5 === 0) {
            ec.moveTo(x, y);
            ec.lineTo(x + 2, y + 15);
            ec.stroke();
          }
        }
      }
      ec.restore();
    }
  }
  /** @param {number} seconds @param {{x:number,y:number}|null} pointer */
  function renderAt(seconds = 0, pointer = null) {
    if (destroyed) return;
    const start = performance.now(),
      speed = recipe.animSpeed?.enabled ? recipe.animSpeed.intensity / 100 : 0,
      time = recipe.animated ? seconds * speed : 0;
    sourceRaster(time, pointer);
    const sourceEnd = performance.now();
    const sampled = sc.getImageData(0, 0, width, height).data,
      s = Math.max(2, Math.round(recipe.cellSize));
    ec.clearRect(0, 0, width, height);
    ec.globalCompositeOperation = recipe.styleBlend || "source-over";
    // Batching the monochrome hatch paths avoids tens of thousands of Canvas
    // state changes per frame while retaining an eight CSS-pixel sample grid.
    const hatchBuckets =
      recipe.renderMode === "hatch" &&
      (recipe.grayscale === 100 || recipe.saturation === 0)
        ? Array.from({ length: 32 }, () => [])
        : null;
    const fastHatch =
      hatchBuckets &&
      recipe.blurType === "off" &&
      !recipe.tintOpacity &&
      (recipe.toneCurve || []).every((point) => point.x === point.y);
    for (let y = 0; y < height; y += s)
      for (let x = 0; x < width; x += s) {
        if (hash(x, y, recipe.shaderSource.seed + 19) * 100 >= recipe.coverage)
          continue;
        const color = averageCell(sampled, width, height, x, y, s),
          raw = luminance(...color) / 255;
        let edge = 0;
        if (recipe.edgeEmphasis) {
          const n = averageCell(
            sampled,
            width,
            height,
            Math.min(width - 1, x + s),
            y,
            s,
          );
          edge = Math.abs(raw - luminance(...n) / 255);
        }
        const l = animatedLuminance(
            cellLuminance(raw, edge, recipe),
            x,
            y,
            time,
            recipe,
          ),
          ratio = l / Math.max(0.01, raw),
          adjusted = color.map((c) => clamp(c * ratio, 0, 255));
        if (hatchBuckets)
          hatchBuckets[Math.min(31, Math.round(l * 31))].push(x, y, l);
        else
          primitive(
            recipe.renderMode,
            x +
              (recipe.renderMode === "hexagons" && Math.floor(y / s) % 2
                ? s / 2
                : 0),
            y,
            s,
            l,
            adjusted,
            time,
            sampled,
          );
      }
    const hatchPixels = fastHatch
      ? new Uint32Array(hatchImage.data.buffer)
      : null;
    if (hatchPixels) hatchPixels.fill(0);
    if (hatchBuckets)
      for (let bin = 0; bin < hatchBuckets.length; bin++) {
        const cells = hatchBuckets[bin],
          rawShade = Math.round((bin / 31) * 255),
          shade = fastHatch
            ? adjustColor(rawShade, rawShade, rawShade, recipe)[0]
            : rawShade;
        if (!cells.length) continue;
        if (hatchPixels && hatchTiles.has(bin)) {
          const pixels = hatchTiles.get(bin);
          for (let i = 0; i < cells.length; i += 3) {
            const x = cells[i],
              y = cells[i + 1];
            for (let row = 0; row < s && y + row < height; row++)
              for (let col = 0; col < s && x + col < width; col++)
                hatchPixels[(y + row) * width + x + col] =
                  pixels[row * s + col];
          }
          continue;
        }
        const tile = makeCanvas();
        tile.width = tile.height = s;
        const tileCtx = tile.getContext("2d"),
          l = bin / 31;
        tileCtx.fillStyle = `rgba(${shade},${shade},${shade},.30)`;
        tileCtx.fillRect(0, 0, s, s);
        tileCtx.strokeStyle = `rgb(${shade},${shade},${shade})`;
        tileCtx.lineWidth = 0.6 + l * 0.7;
        tileCtx.beginPath();
        const count = Math.max(1, Math.round(1 + l * 4 + recipe.density / 25)),
          length = s * (0.3 + l * 0.7);
        for (let j = 0; j < count; j++) {
          const d = (j * s) / count;
          tileCtx.moveTo(d, 0);
          tileCtx.lineTo(Math.min(s, d + length), Math.min(length, s - d));
          if (l > 0.34) {
            tileCtx.moveTo(0, d);
            tileCtx.lineTo(Math.min(length, s - d), Math.min(s, d + length));
          }
        }
        if (l > 0.62) {
          tileCtx.moveTo(0, s);
          tileCtx.lineTo(s, 0);
        }
        tileCtx.stroke();
        if (hatchPixels) {
          const pixels = new Uint32Array(
            tileCtx.getImageData(0, 0, s, s).data.buffer,
          );
          hatchTiles.set(bin, pixels);
          for (let i = 0; i < cells.length; i += 3) {
            const x = cells[i],
              y = cells[i + 1];
            for (let row = 0; row < s && y + row < height; row++)
              for (let col = 0; col < s && x + col < width; col++)
                hatchPixels[(y + row) * width + x + col] =
                  pixels[row * s + col];
          }
        } else {
          ec.fillStyle = ec.createPattern(tile, "repeat");
          ec.beginPath();
          for (let i = 0; i < cells.length; i += 3)
            ec.rect(cells[i], cells[i + 1], s, s);
          ec.fill();
        }
      }
    if (hatchPixels) ec.putImageData(hatchImage, 0, 0);
    const gridEnd = performance.now();
    ec.globalCompositeOperation = "source-over";
    if (!fastHatch) adjusted();
    const adjustedEnd = performance.now();
    effects(time);
    const effectsEnd = performance.now();
    if (recipe.lights?.enabled)
      for (const point of recipe.lights.points) {
        const radius =
            (point.radius > 1 ? point.radius / 100 : point.radius) *
            Math.min(width, height),
          g = ec.createRadialGradient(
            point.x * width,
            point.y * height,
            0,
            point.x * width,
            point.y * height,
            Math.max(1, radius),
          );
        g.addColorStop(
          0,
          `rgba(255,255,255,${point.intensity > 1 ? point.intensity / 100 : point.intensity})`,
        );
        g.addColorStop(1, "transparent");
        ec.fillStyle = g;
        ec.globalCompositeOperation = "screen";
        ec.fillRect(0, 0, width, height);
        ec.globalCompositeOperation = "source-over";
      }
    ctx.clearRect(0, 0, width, height);
    if (recipe.bgMode !== "none") {
      ctx.save();
      ctx.globalAlpha = recipe.bgOpacity / 100;
      if (recipe.bgMode === "solid" || recipe.bgMode === "black") {
        ctx.fillStyle = "#000";
        ctx.fillRect(0, 0, width, height);
      } else {
        ctx.filter =
          recipe.bgMode === "blurred" ? `blur(${recipe.bgBlur}px)` : "none";
        ctx.drawImage(source, 0, 0);
      }
      ctx.restore();
    }
    ctx.drawImage(effect, 0, 0);
    if (mask) {
      pc.clearRect(0, 0, width, height);
      pc.drawImage(source, 0, 0);
      pc.globalCompositeOperation = recipe.mask.invert
        ? "destination-out"
        : "destination-in";
      pc.drawImage(mask, 0, 0, width, height);
      pc.globalCompositeOperation = "source-over";
      ctx.drawImage(post, 0, 0);
    }
    timings = {
      source: sourceEnd - start,
      grid: gridEnd - sourceEnd,
      adjustments: adjustedEnd - gridEnd,
      effects: effectsEnd - adjustedEnd,
      composite: performance.now() - effectsEnd,
    };
    averageCost = averageCost * 0.9 + (performance.now() - start) * 0.1;
    renderedFrames++;
    if (canvas.dataset) {
      canvas.dataset.frame = String(renderedFrames);
      canvas.dataset.renderMs = averageCost.toFixed(2);
    }
  }
  resize(size.width, size.height);
  return {
    renderAt,
    resize,
    ready,
    getStats: () => ({
      width,
      height,
      resolution,
      renderedFrames,
      averageCost,
      timings,
      destroyed,
    }),
    destroy() {
      destroyed = true;
      mask?.close?.();
      for (const c of [source, field, effect, scratch, post])
        c.width = c.height = 0;
    },
  };
}
export function createThreadLight(canvas, recipe) {
  const rect = () => canvas.getBoundingClientRect(),
    r = rect(),
    engine = createRasterRenderer(canvas, recipe, r);
  let running = true,
    destroyed = false,
    lastClock = null,
    lastTime = -Infinity,
    elapsed = 0,
    pointer = null;
  function renderAt(seconds = 0) {
    if (!destroyed) engine.renderAt(seconds, pointer);
  }
  function resize() {
    const r = rect();
    engine.resize(r.width, r.height);
    renderAt(elapsed);
  }
  const observer = new ResizeObserver(resize);
  observer.observe(canvas);
  renderAt(0);
  return {
    renderAt,
    resize,
    update(clock) {
      if (!running || destroyed) {
        lastClock = null;
        return;
      }
      if (lastClock !== null)
        elapsed += Math.min(0.1, (clock - lastClock) / 1000);
      lastClock = clock;
      const cost = engine.getStats().averageCost,
        fps =
          cost > 40
            ? 15
            : typeof window !== "undefined" && window.innerWidth < 800
              ? 20
              : 30;
      if (clock - lastTime < 1000 / fps) return;
      lastTime = clock;
      renderAt(elapsed);
    },
    pause() {
      running = false;
      lastClock = null;
    },
    resume() {
      if (!destroyed) running = true;
    },
    setPointer(value) {
      pointer = value;
    },
    getStats() {
      return { ...engine.getStats(), running, destroyed, elapsed };
    },
    destroy() {
      destroyed = true;
      running = false;
      observer.disconnect();
      engine.destroy();
    },
  };
}
