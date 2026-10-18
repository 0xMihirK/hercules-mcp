export const VERTEX_SHADER_SOURCE = `#version 300 es
precision highp float;
out vec2 v_uv;
void main() {
  vec2 pos = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
  v_uv = pos;
  gl_Position = vec4(pos * 2.0 - 1.0, 0.0, 1.0);
}
`;

export const FRAGMENT_SHADER_SOURCE = `#version 300 es
precision highp float;
in vec2 v_uv;
out vec4 fragColor;

uniform vec2 u_res;
uniform float u_time;
uniform vec2 u_pointer;
uniform float u_intensity;
uniform float u_scroll;

float hash21(vec2 p) {
  p = fract(p * vec2(234.34, 435.345));
  p += dot(p, p + 34.23);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash21(i + vec2(0.0, 0.0)), hash21(i + vec2(1.0, 0.0)), u.x),
    mix(hash21(i + vec2(0.0, 1.0)), hash21(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

mat2 rot = mat2(0.80, 0.60, -0.60, 0.80);

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * noise(p);
    p = rot * p * 2.03 + vec2(11.7, 7.3);
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = v_uv;
  float aspect = u_res.x / max(u_res.y, 1.0);
  vec2 p = (uv - 0.5) * vec2(aspect, 1.0);

  float t = u_time * 0.13;
  float scrollShift = u_scroll * 0.4;

  // Domain-warped molten smoke field
  vec2 q = vec2(
    fbm(p * 1.55 + vec2(0.0, t * 0.75 - scrollShift)),
    fbm(p * 1.55 + vec2(4.2, -t * 0.6 + scrollShift * 0.5))
  );

  vec2 r = vec2(
    fbm(p * 2.15 + 2.3 * q + vec2(1.7, t * 0.95)),
    fbm(p * 2.15 + 2.3 * q + vec2(8.3, -t * 0.8))
  );

  float cloud = fbm(p * 1.65 + 2.0 * r - vec2(0.0, t * 0.5));
  float plume = smoothstep(0.24, 0.82, cloud);

  // Sharp glowing volcanic magma veins along turbulent ridges
  float ridge1 = 1.0 - abs(noise(p * 3.6 + r * 2.2 - vec2(0.0, t * 1.1)) * 2.0 - 1.0);
  float ridge2 = 1.0 - abs(noise(p * 6.4 - q * 1.8 + vec2(t * 0.7, 0.0)) * 2.0 - 1.0);
  float vein = pow(clamp(ridge1, 0.0, 1.0), 4.0) * (0.45 + 0.55 * plume);
  float fineVein = pow(clamp(ridge2, 0.0, 1.0), 5.5) * plume;

  // Keep center reading column dark enough for effortless white-text contrast
  // while letting rich ember plumes and veins frame the stage and margins
  float radial = length(p * vec2(0.72, 0.9));
  float stageFrame = mix(0.62, 1.08, smoothstep(0.15, 0.82, radial));

  // Pointer heat bloom
  vec2 ptr = (vec2(u_pointer.x, 1.0 - u_pointer.y) - 0.5) * vec2(aspect, 1.0);
  float ptrDist = length(p - ptr);
  float cursorHeat = exp(-ptrDist * ptrDist * 5.0) * 0.28;

  // Rising ember motes / sparks
  vec2 sparkGrid = p * 15.0 - vec2(q.x * 1.6, u_time * 0.75 + scrollShift * 2.5);
  vec2 sparkId = floor(sparkGrid);
  vec2 sparkLocal = fract(sparkGrid) - 0.5;
  float sparkSeed = hash21(sparkId);
  vec2 sparkOffset = vec2(fract(sparkSeed * 13.7) - 0.5, fract(sparkSeed * 29.3) - 0.5) * 0.55;
  float sparkDist = length(sparkLocal - sparkOffset);
  float sparkMask = step(0.84, sparkSeed) * smoothstep(0.10, 0.012, sparkDist);
  float sparkPulse = 0.4 + 0.6 * sin(u_time * 3.0 + sparkSeed * 62.8);
  float sparks = sparkMask * sparkPulse;

  float heat = clamp((plume * 0.72 + cursorHeat) * stageFrame * u_intensity, 0.0, 1.0);

  // Ember Noir palette: deep obsidian void -> smoldering crimson-coal -> burnt copper -> vivid ember
  vec3 cVoid   = vec3(0.024, 0.027, 0.035); // #060709
  vec3 cCoal   = vec3(0.125, 0.038, 0.020); // #200a05
  vec3 cCrimson= vec3(0.380, 0.095, 0.032); // #611808
  vec3 cCopper = vec3(0.760, 0.240, 0.075); // #c23d13
  vec3 cEmber  = vec3(1.000, 0.416, 0.169); // #ff6a2b
  vec3 cSpark  = vec3(1.000, 0.720, 0.440); // #ffb870

  vec3 col = cVoid;
  col = mix(col, cCoal,    smoothstep(0.08, 0.34, heat));
  col = mix(col, cCrimson, smoothstep(0.28, 0.62, heat));
  col = mix(col, cCopper,  smoothstep(0.55, 0.92, heat));

  // Add glowing magma veins and rising sparks
  col += cEmber * (vein * 0.58 + fineVein * 0.34) * u_intensity;
  col += mix(cEmber, cSpark, 0.6) * sparks * 0.68 * u_intensity;

  // Soft top/bottom vignette and film grain
  float grain = (hash21(gl_FragCoord.xy + fract(u_time) * 100.0) - 0.5) * 0.016;
  col = clamp(col + grain, 0.0, 0.88);

  fragColor = vec4(col, 1.0);
}
`;

export interface EmberFieldController {
  frame: (timeMs: number) => number;
  resize: (width?: number, height?: number) => void;
  setPointer: (point: { x: number; y: number }) => void;
  setIntensity: (intensity: number) => void;
  setScroll: (scrollProgress: number) => void;
  destroy: () => void;
}

export function createEmberField(
  canvas: HTMLCanvasElement | OffscreenCanvas,
): EmberFieldController | null {
  if (!canvas || typeof canvas.getContext !== "function") return null;
  let gl: WebGL2RenderingContext | null = null;
  try {
    gl = canvas.getContext("webgl2", {
      alpha: false,
      antialias: false,
      depth: false,
      stencil: false,
      premultipliedAlpha: false,
      preserveDrawingBuffer: false,
      powerPreference: "low-power",
    }) as WebGL2RenderingContext | null;
  } catch {
    return null;
  }
  if (!gl) return null;

  const compile = (type: number, source: string) => {
    const shader = gl!.createShader(type);
    if (!shader) return null;
    gl!.shaderSource(shader, source);
    gl!.compileShader(shader);
    if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
      gl!.deleteShader(shader);
      return null;
    }
    return shader;
  };

  const vs = compile(gl.VERTEX_SHADER, VERTEX_SHADER_SOURCE);
  const fs = compile(gl.FRAGMENT_SHADER, FRAGMENT_SHADER_SOURCE);
  if (!vs || !fs) {
    if (vs) gl.deleteShader(vs);
    if (fs) gl.deleteShader(fs);
    return null;
  }

  const program = gl.createProgram();
  if (!program) return null;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  gl.deleteShader(vs);
  gl.deleteShader(fs);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    return null;
  }

  const vao = gl.createVertexArray();
  const uRes = gl.getUniformLocation(program, "u_res");
  const uTime = gl.getUniformLocation(program, "u_time");
  const uPointer = gl.getUniformLocation(program, "u_pointer");
  const uIntensity = gl.getUniformLocation(program, "u_intensity");
  const uScroll = gl.getUniformLocation(program, "u_scroll");

  let targetPointer = { x: 0.72, y: 0.26 };
  let currentPointer = { x: 0.72, y: 0.26 };
  let targetIntensity = 1.0;
  let currentIntensity = 1.0;
  let targetScroll = 0.0;
  let currentScroll = 0.0;
  let width = 640;
  let height = 360;
  let destroyed = false;

  const resize = (nextW?: number, nextH?: number) => {
    if (destroyed || !gl) return;
    const dpr =
      typeof window !== "undefined" ? Math.min(window.devicePixelRatio || 1, 1.5) : 1;
    const scale = 0.6 * dpr;
    const clientW =
      nextW ??
      ("clientWidth" in canvas && canvas.clientWidth ? canvas.clientWidth : 1280);
    const clientH =
      nextH ??
      ("clientHeight" in canvas && canvas.clientHeight ? canvas.clientHeight : 720);
    width = Math.max(240, Math.min(1440, Math.round(clientW * scale)));
    height = Math.max(160, Math.min(900, Math.round(clientH * scale)));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    gl.viewport(0, 0, width, height);
  };

  resize();

  const frame = (timeMs: number): number => {
    if (destroyed || !gl) return 0;
    const t0 = performance.now();
    currentPointer.x += (targetPointer.x - currentPointer.x) * 0.08;
    currentPointer.y += (targetPointer.y - currentPointer.y) * 0.08;
    currentIntensity += (targetIntensity - currentIntensity) * 0.08;
    currentScroll += (targetScroll - currentScroll) * 0.1;

    gl.useProgram(program);
    gl.bindVertexArray(vao);
    gl.uniform2f(uRes, width, height);
    gl.uniform1f(uTime, timeMs * 0.001);
    gl.uniform2f(uPointer, currentPointer.x, currentPointer.y);
    gl.uniform1f(uIntensity, currentIntensity);
    gl.uniform1f(uScroll, currentScroll);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.bindVertexArray(null);
    return performance.now() - t0;
  };

  return {
    frame,
    resize,
    setPointer(point) {
      targetPointer = {
        x: Math.max(0, Math.min(1, point.x)),
        y: Math.max(0, Math.min(1, point.y)),
      };
    },
    setIntensity(value) {
      targetIntensity = Math.max(0.45, Math.min(1.25, value));
    },
    setScroll(progress) {
      targetScroll = Math.max(0, Math.min(1, progress));
    },
    destroy() {
      if (destroyed || !gl) return;
      destroyed = true;
      if (vao) gl.deleteVertexArray(vao);
      gl.deleteProgram(program);
    },
  };
}
