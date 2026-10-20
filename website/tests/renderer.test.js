import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  hash,
  valueNoise,
  fbm,
  averageCell,
  adjustColor,
  spotlight,
} from "../thread-light.js";

const recipe = JSON.parse(
  await readFile(new URL("../recipe.json", import.meta.url), "utf8"),
);

test("procedural noise is repeatable, seeded, bounded, and spatially continuous", () => {
  assert.equal(hash(4, 6, 1), hash(4, 6, 1));
  assert.notEqual(hash(4, 6, 1), hash(4, 6, 2));
  for (const x of [-3.2, 0, 0.1, 2.8, 200.9]) {
    const value = fbm(x, x + 0.8, 1);
    assert.ok(value >= 0 && value <= 1);
    assert.equal(value, fbm(x, x + 0.8, 1));
    assert.ok(
      Math.abs(valueNoise(x, 0.42, 1) - valueNoise(x + 0.0001, 0.42, 1)) <
        0.001,
    );
  }
});

test("cell sampling averages all pixels and handles partial right/bottom cells", () => {
  const pixels = new Uint8ClampedArray([
    0, 10, 20, 255, 100, 110, 120, 255, 200, 210, 220, 255, 20, 30, 40, 255,
    120, 130, 140, 255, 220, 230, 240, 255,
  ]);
  assert.deepEqual(averageCell(pixels, 3, 2, 0, 0, 2), [60, 70, 80]);
  assert.deepEqual(averageCell(pixels, 3, 2, 2, 0, 2), [210, 220, 230]);
});

test("color adjustment applies contrast before grayscale and tint after grayscale", () => {
  const value = adjustColor(0, 120, 255, recipe);
  assert.equal(value[0], value[1]);
  assert.equal(value[1], value[2]);
  const expected = 0.2126 * 0 + 0.7152 * 116.25 + 0.0722 * 255;
  assert.ok(Math.abs(value[0] - expected) < 0.0001);
  const tinted = adjustColor(120, 120, 120, {
    ...recipe,
    contrast: 100,
    tint: "#ff0000",
    tintOpacity: 100,
  });
  assert.deepEqual(tinted, [120, 0, 0]);
});

test("spotlight brightens near the pointer and is inactive without pointer or reactivity", () => {
  const source = recipe.shaderSource;
  assert.ok(
    spotlight(0.5, 0.5, { x: 0.5, y: 0.5 }, source) >
      spotlight(0, 0, { x: 0.5, y: 0.5 }, source),
  );
  assert.equal(spotlight(0.5, 0.5, null, source), 0);
  assert.equal(
    spotlight(
      0.5,
      0.5,
      { x: 0.5, y: 0.5 },
      { ...source, mouseReactive: false },
    ),
    0,
  );
});

test("the approved configuration remains procedural smoke/hatch with only halftone enabled", () => {
  assert.equal(recipe.cellSize, 8);
  assert.equal(recipe.renderMode, "hatch");
  assert.equal(recipe.shaderSource.preset, "smoke");
  assert.equal(recipe.shaderSource.seed, 1);
  assert.deepEqual(
    Object.entries(recipe.pfx)
      .filter(([, value]) => value.enabled)
      .map(([name]) => name),
    ["halftone"],
  );
  assert.equal(recipe.bgMode, "none");
  assert.equal(recipe.mask.enabled, false);
  assert.equal(recipe.lights.enabled, false);
  assert.equal(recipe.tintOpacity, 0);
});
