import { useRef, useState } from "react";
import { ArrowUpRight, Check, Copy } from "@phosphor-icons/react";

export default function Setup({ prompt }: { prompt: string }) {
  const [status,setStatus]=useState("");
  const details=useRef<HTMLDetailsElement>(null);
  async function copy(){
    try { await navigator.clipboard.writeText(prompt);setStatus("Installation prompt copied. Paste it into your terminal-capable agent."); }
    catch { if(details.current)details.current.open=true;setStatus("Clipboard access is unavailable. Select and copy the prompt below."); }
  }
  return <section id="install" className="chapter wrap setup-section" aria-labelledby="setup-title">
    <div className="chapter-heading"><h2 id="setup-title">Give your agent<br />a place to work.</h2><p>One canonical prompt guides installation for your actual environment. Your agent chooses a capability set, configures STDIO, and verifies the runtime locally.</p></div>
    <div className="setup-layout"><div className="setup-prerequisites"><h3>Start with the essentials.</h3><ul><li>Git and uv</li><li>A working Docker-compatible daemon</li><li>A terminal-capable agent with STDIO MCP support</li></ul><p>Windows, macOS, or Linux. A worker or custom integration can use the same MCP transport.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md">Read the installation contract <ArrowUpRight size={18} aria-hidden="true"/></a></div>
      <div className="setup-action"><h3>Copy. Install. Verify.</h3><p>Paste the prompt into your agent. It inspects existing setup, preserves configuration and evidence, and verifies an explicit container start and stop.</p><button className="button primary" onClick={copy}>{status.startsWith("Installation")?<Check size={20} aria-hidden="true"/>:<Copy size={20} aria-hidden="true"/>}Copy installation prompt</button><p className="copy-status" role="status">{status}</p><details ref={details}><summary>Read the complete prompt</summary><pre className="installation-prompt">{prompt}</pre></details></div>
    </div>
    <div className="setup-verify"><div><h3>Verify the loaded server.</h3><p>Use your client’s MCP inventory to confirm Hercules’s selected tools and resources. Connecting alone does not start Kali.</p></div><div><code>system_start_container → local verification → system_stop_container</code><p>The installing agent will tell you whether to reload MCP, start a new session, or restart your IDE.</p></div></div>
  </section>;
}
