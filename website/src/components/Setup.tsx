import { useRef, useState } from "react";
import { ArrowRight, ArrowUpRight, Check, Copy, ChatText, PlugsConnected } from "@phosphor-icons/react";
export default function Setup({prompt}:{prompt:string}){
  const [status,setStatus]=useState(""),details=useRef<HTMLDetailsElement>(null);
  async function copy(){
    try{await navigator.clipboard.writeText(prompt);setStatus("Prompt copied. Paste it into your coding agent.");}
    catch{if(details.current)details.current.open=true;setStatus("Select and copy the complete prompt below.");}
  }
  return <section id="install" className="chapter wrap installation-section" aria-labelledby="setup-title">
    <div className="installation-heading"><h2 id="setup-title">Install with<br/><em>one prompt.</em></h2><div><p>Paste the prompt into a coding agent with terminal access. It checks prerequisites, helps choose the security tools, and configures Hercules.</p><button className="button primary" onClick={copy}>{status.startsWith("Prompt copied")?<Check size={21}/>:<Copy size={21}/>}Copy installation prompt</button><p className="copy-status" role="status">{status}</p></div></div>
    <ol className="installation-path"><li><Copy size={31}/><h3>Copy the prompt.</h3><p>Use the same prompt on Windows, macOS, or Linux.</p></li><li><ChatText size={31}/><h3>Paste into your agent.</h3><p>Your agent checks prerequisites and asks which security tools you need.</p></li><li><PlugsConnected size={31}/><h3>Connect and verify.</h3><p>Confirm Hercules is loaded. Start its Docker container when you need tools.</p></li></ol>
    <div className="installation-bottom"><p>Windows, macOS, or Linux. Git, uv, Docker, and a terminal-capable agent with STDIO MCP support.</p><a className="text-link" href="https://github.com/0xMihirK/hercules-mcp/blob/main/install.md">Full setup guide <ArrowUpRight size={18}/></a></div>
    <details ref={details} className="prompt-disclosure"><summary>Read the installation prompt <ArrowRight size={17}/></summary><pre className="installation-prompt">{prompt}</pre></details>
  </section>;
}
