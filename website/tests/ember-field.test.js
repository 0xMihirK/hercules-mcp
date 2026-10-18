import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

const source = await readFile(
  new URL("../src/ember-field.ts", import.meta.url),
  "utf8",
);
const code = ts.transpileModule(source, {
  compilerOptions: {
    target: ts.ScriptTarget.ES2022,
    module: ts.ModuleKind.ES2022,
  },
}).outputText;
const {
  VERTEX_SHADER_SOURCE,
  FRAGMENT_SHADER_SOURCE,
  createEmberField,
} = await import(
  "data:text/javascript;base64," + Buffer.from(code).toString("base64")
);

test("ember-field shaders define WebGL2 GLSL 300 es sources and uniforms", () => {
  assert.match(VERTEX_SHADER_SOURCE, /^#version 300 es/);
  assert.match(FRAGMENT_SHADER_SOURCE, /^#version 300 es/);
  for (const uniform of [
    "u_res",
    "u_time",
    "u_pointer",
    "u_intensity",
    "u_scroll",
  ]) {
    assert.ok(
      FRAGMENT_SHADER_SOURCE.includes(`uniform `) &&
        FRAGMENT_SHADER_SOURCE.includes(uniform),
      `missing uniform ${uniform}`,
    );
  }
});

test("createEmberField returns null when WebGL2 is unavailable so Canvas2D fallback runs", () => {
  assert.equal(createEmberField(null), null);
  assert.equal(createEmberField({ getContext: () => null }), null);
  assert.equal(
    createEmberField({
      getContext: () => {
        throw new Error("WebGL disabled");
      },
    }),
    null,
  );
});

test("createEmberField drives uniforms and cleans up resources on a WebGL2 context", () => {
  const calls = [];
  const gl = {
    VERTEX_SHADER: 0x8b31,
    FRAGMENT_SHADER: 0x8b30,
    COMPILE_STATUS: 0x8b81,
    LINK_STATUS: 0x8b82,
    TRIANGLES: 0x0004,
    createShader: (type) => ({ type }),
    shaderSource: () => {},
    compileShader: () => {},
    getShaderParameter: () => true,
    deleteShader: () => calls.push("deleteShader"),
    createProgram: () => ({ id: "prog" }),
    attachShader: () => {},
    linkProgram: () => {},
    getProgramParameter: () => true,
    deleteProgram: () => calls.push("deleteProgram"),
    createVertexArray: () => ({ id: "vao" }),
    deleteVertexArray: () => calls.push("deleteVertexArray"),
    getUniformLocation: (_, name) => name,
    viewport: (x, y, w, h) => calls.push(["viewport", w, h]),
    useProgram: () => {},
    bindVertexArray: () => {},
    uniform2f: (loc, x, y) => calls.push([loc, x, y]),
    uniform1f: (loc, v) => calls.push([loc, v]),
    drawArrays: (mode, first, count) => calls.push(["drawArrays", count]),
  };
  const canvas = {
    width: 0,
    height: 0,
    clientWidth: 1280,
    clientHeight: 720,
    getContext: (kind) => (kind === "webgl2" ? gl : null),
  };
  const controller = createEmberField(canvas);
  assert.ok(controller);
  controller.setPointer({ x: 0.25, y: 0.75 });
  controller.setIntensity(1.1);
  controller.setScroll(0.5);
  const cost = controller.frame(1000);
  assert.ok(cost >= 0);
  assert.ok(calls.some((entry) => Array.isArray(entry) && entry[0] === "drawArrays" && entry[1] === 3));
  controller.destroy();
  assert.ok(calls.includes("deleteProgram"));
  assert.ok(calls.includes("deleteVertexArray"));
});
