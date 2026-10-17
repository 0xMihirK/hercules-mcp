import { useRef, useState } from "react";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { Copy } from "@phosphor-icons/react/Copy";
import { ChatText } from "@phosphor-icons/react/ChatText";
import { PlugsConnected } from "@phosphor-icons/react/PlugsConnected";
export default function Setup({prompt}:{prompt:string}){
  const [status,setStatus]=useState(""),details=useRef<HTMLDetailsElement>(null);
  async function copy(){
    try{await navigator.clipboard.writeText(prompt);setStatus("Prompt copied. Paste it into your coding agent.");}
    catch{if(details.current)details.current.open=true;setStatus("Select and copy the complete prompt below.");}
  }
  return <section id="install" className="chapter wrap installation-section" aria-labelledby="setup-title">
    <div className="installation-heading"><h2 id="setup-title">Install with<br/><em>one prompt.</em></h2><div><p>One setup CLI installs, updates, or repairs Hercules for your current agent. Keep existing preferences and evidence intact.</p><button className="button primary" onClick={copy}>{status.startsWith("Prompt copied")?<Check size={21}/>:<Copy size={21}/>}Copy installation prompt</button><p className="copy-status" role="status">{status}</p></div></div>
    <ol className="installation-path"><li><Copy size={31}/><h3>Copy the prompt.</h3><p>Use the same prompt on Windows, macOS, or Linux. Full capabilities by default; existing selections stay unchanged.</p></li><li><ChatText size={31}/><h3>Paste into your agent.</h3><p>Configure only your current client. Host setup checks a cold connection without starting Kali. Claude auto-mode denials stay stopped for your review.</p></li><li><PlugsConnected size={31}/><h3>Connect and verify.</h3><p>Reload your client when instructed. Runtime downloads and local container tests are separate choices, not part of registration repair.</p></li></ol>
    <div className="installation-bottom"><p>Git, uv, and a terminal-capable STDIO MCP agent for host setup. Docker when preparing or using the runtime. The summary separates installation, client reload, runtime readiness, verification, and cleanup.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md">Full setup guide <ArrowUpRight size={18}/></a></div>
    <details ref={details} className="prompt-disclosure"><summary>Read the installation prompt <ArrowRight size={17}/></summary><pre className="installation-prompt">{prompt}</pre></details>
  </section>;
}
