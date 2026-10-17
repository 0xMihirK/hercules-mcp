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
    <div className="chapter-heading"><h2 id="setup-title">Give your agent<br />a place to work.</h2><p>One setup CLI handles installation, updates, and repair. Configure only your current agent; keep its preferences and evidence intact.</p></div>
    <div className="setup-layout"><div className="setup-prerequisites"><h3>Start with the essentials.</h3><ul><li>Git and uv for host setup</li><li>Docker when you prepare or use the runtime</li><li>A terminal-capable agent with STDIO MCP support</li></ul><p>Windows, macOS, or Linux. Full capabilities by default, existing selections preserved.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md">Read the setup guide <ArrowUpRight size={18} aria-hidden="true"/></a></div>
      <div className="setup-action"><h3>Copy. Install. Resume.</h3><p>Paste the prompt into your agent. Host setup checks a cold connection without starting Kali. Runtime downloads and local container testing are separate choices.</p><button className="button primary" onClick={copy}>{status.startsWith("Installation")?<Check size={20} aria-hidden="true"/>:<Copy size={20} aria-hidden="true"/>}Copy installation prompt</button><p className="copy-status" role="status">{status}</p><details ref={details}><summary>Read the complete prompt</summary><pre className="installation-prompt">{prompt}</pre></details></div>
    </div>
    <div className="setup-verify"><div><h3>Know what is ready.</h3><p>The summary separates host installation, client reload, runtime preparation, verification, and cleanup. Connecting alone does not start Kali.</p></div><div><code>status → install → runtime prepare → verify --runtime</code><p>Claude auto-mode denials stay stopped for your review. Setup never adds blanket permissions or replaces a running environment.</p></div></div>
  </section>;
}
