export type Client = "claude" | "codex" | "opencode" | "hermes";
export type PixelCapture = { index: string; indexSha256: string; width: number; height: number; fps: number };
export type NativeRecording = {
  file: string; sha256: string; client: Client; scenario: string;
  columns: number; rows: number; duration: number; displayStart?: number;
  chapters: Record<string, number>; pixels: PixelCapture;
  still?: string; stillSha256?: string;
  entrance?: { file: string; sha256: string; at: number };
  completedStill?: string; completedStillAt?: number; completedStillSha256?: string;
};
export type NativeManifest = {
  schemaVersion: number; playbackSpeed: number;
  realTools: boolean; scriptedToolResults: boolean;
  cases: Record<string, { title: string; objective: string }>;
  clients: Record<Client, { version: string }>;
  recordings: NativeRecording[];
};
export const clients: { id: Client; name: string }[] = [{id:"claude",name:"Claude Code"},{id:"codex",name:"Codex"},{id:"opencode",name:"OpenCode"},{id:"hermes",name:"Hermes"}];
