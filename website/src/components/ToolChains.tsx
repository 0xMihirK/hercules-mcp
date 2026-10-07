import { useMemo, useState } from "react";
import { ArrowRight, CaretDown, MagnifyingGlass } from "@phosphor-icons/react";

export type Catalog = { full_tool_count: number; resource_count: number; capabilities: { key: string; category: string; mcp_tools: string[]; description?: string }[] };
const chains = [
  { name: "Network", brief: "Turn reachable services into a verified inventory.", tools: ["recon_dns", "nmap_scan", "network_curl", "workspace_write_file"], evidence: ["DNS answers", "Scan XML", "HTTP responses", "Inventory report"], decision: "An open port is a lead. Verify the service before assessing applicability.", case: "Network inventory / service assessment" },
  { name: "Web", brief: "Discover, cross-check, then confirm in a browser.", tools: ["fuzz_dirs", "web_scan", "nuclei_run", "browser_snapshot"], evidence: ["Discovered routes", "Fingerprint", "Matcher results", "Browser evidence"], decision: "Independent observations confirm the debug endpoint; a normal 404 rejects the backup guess.", case: "Website assessment / remediation recheck" },
  { name: "CTF", brief: "Follow the evidence through each hidden layer.", tools: ["shell_exec", "ctf_binwalk", "workspace_read_file", "shell_exec"], evidence: ["Packet clues", "Carrier signatures", "Archive manifest", "Verified flag digest"], decision: "A rejected key changes the hypothesis. The manifest checksum separates the recovered flag from the decoy.", case: "Layered forensic CTF / web CTF" },
  { name: "Reporting", brief: "Reconcile findings and leave a reproducible trail.", tools: ["workspace_read_file", "shell_check_job", "workspace_write_file", "system_stop_container"], evidence: ["Paged artifacts", "Job diagnostics", "Markdown + HTML", "Preserved workspace"], decision: "Distinguish fresh observations from supplied inputs. Verify the saved report before cleaning up its runtime.", case: "Evidence to report / background-job recovery" },
];

export default function ToolChains({ catalog }: { catalog: Catalog | null }) {
  const [open, setOpen] = useState("Network"), [query, setQuery] = useState("");
  const tools = useMemo(() => [...new Set(catalog?.capabilities.flatMap(c => c.mcp_tools) || [])].filter(t => t.toLowerCase().includes(query.toLowerCase())), [catalog, query]);
  return <section id="tools" className="chapter wrap">
    <div className="chapter-heading"><h2>Tools that work<br />better together.</h2><p>Discovery changes the next question. Verification changes the answer. Hercules keeps the tool calls and their evidence in one workspace.</p></div>
    <div className="chains">{chains.map(chain => <article className={open === chain.name ? "chain is-open" : "chain"} key={chain.name}>
      <h3><button aria-expanded={open === chain.name} aria-controls={`chain-${chain.name}`} onClick={() => setOpen(open === chain.name ? "" : chain.name)}><span>{chain.name}</span><span className="chain-brief">{chain.brief}</span><CaretDown size={22} aria-hidden="true" /></button></h3>
      <div id={`chain-${chain.name}`} hidden={open !== chain.name} className="chain-content">
        <ol className="chain-flow">{chain.tools.map((tool, i) => <li key={i}><code>{tool}</code><span>{chain.evidence[i]}</span>{i < 3 && <ArrowRight aria-hidden="true" size={20} />}</li>)}</ol>
        <div className="chain-decision"><p>{chain.decision}</p><span>{chain.case}</span></div>
      </div>
    </article>)}</div>
    <details className="catalog"><summary>Explore the complete tool catalog <span>{catalog ? `${catalog.full_tool_count} tools · ${catalog.resource_count} resources` : "Loading source catalog"}</span><CaretDown size={20} aria-hidden="true" /></summary>
      <div className="catalog-body"><label className="search"><MagnifyingGlass size={20} aria-hidden="true" /><span className="sr-only">Search MCP tools</span><input type="search" placeholder="Search by tool name" value={query} onChange={e => setQuery(e.target.value)} /></label><p>{tools.length} matching tools. Installed capabilities determine which tools your server exposes.</p><ul className="tool-catalog">{tools.map(tool => <li key={tool}><code>{tool}</code></li>)}</ul>{!tools.length && catalog && <p>No matching tools. Try “browser”, “shell” or “workspace”.</p>}</div>
    </details>
  </section>;
}
