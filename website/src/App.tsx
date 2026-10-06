import {
  lazy,
  Suspense,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { motion } from "motion/react";
import { useReducedMotion } from "./lib/use-reduced-motion";
import Background from "./components/Background";
import { categories, evidence, workflow } from "../demo.js";
const AgentTerminal = lazy(() => import("./components/AgentTerminal"));
const github = "https://github.com/0xMihirK/hercules-mcp";
const asset = (name: string) => `${import.meta.env.BASE_URL}assets/${name}`;
type Catalog = {
  full_tool_count: number;
  resource_count: number;
  capabilities: { key: string; category: string; mcp_tools: string[] }[];
};
const caseStudies = [
  {
    label: "Lifecycle",
    title: "Start when work begins.",
    text: "Connecting discovers the tools. An explicit call starts Kali. Repeated calls reuse the runtime, and an intentional stop keeps it stopped.",
    file: "hercules/core/docker_manager.py",
    icon: "▷",
    code: "system_start_container()",
  },
  {
    label: "Evidence",
    title: "Keep the full picture.",
    text: "Large responses stay bounded. Raw overflow remains in workspace artifacts, with separate flags for inline output and complete evidence.",
    file: "hercules/core/docker_manager.py",
    icon: "≡",
    code: "output_complete: false\nevidence_complete: true",
  },
  {
    label: "Ownership",
    title: "Give every client its own session.",
    text: "Workspaces, runtime ports, and exact process identities keep concurrent agents apart. Cleanup belongs to the client that created the container.",
    file: "hercules/core/orphan_guardian.py",
    icon: "⊞",
    code: "client → session → owned runtime",
  },
  {
    label: "Capabilities",
    title: "Build the tools you choose.",
    text: "One catalog controls the MCP surface and the binaries in Kali. Core services stay available; optional capabilities shape your environment.",
    file: "hercules/core/tool_catalog.py",
    icon: "⌘",
    code: "catalog → image → verified manifest",
  },
];
function tabKey(
  event: KeyboardEvent<HTMLButtonElement>,
  index: number,
  total: number,
  select: (index: number) => void,
) {
  const delta =
    event.key === "ArrowRight" || event.key === "ArrowDown"
      ? 1
      : event.key === "ArrowLeft" || event.key === "ArrowUp"
        ? -1
        : 0;
  if (!delta && event.key !== "Home" && event.key !== "End") return;
  event.preventDefault();
  const next =
    event.key === "Home"
      ? 0
      : event.key === "End"
        ? total - 1
        : (index + delta + total) % total;
  select(next);
  const tabs =
    event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>(
      '[role="tab"]',
    );
  tabs?.[next]?.focus();
}
function Reveal({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.12 }}
      transition={{ duration: reduced ? 0 : 0.65, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
function Heading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: ReactNode;
  description: string;
}) {
  return (
    <Reveal className="section-head">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
      </div>
      <p>{description}</p>
    </Reveal>
  );
}
export default function App() {
  const reduced = useReducedMotion(),
    [paused, setPaused] = useState(false);
  const [catalog, setCatalog] = useState<Catalog | null>(null),
    [install, setInstall] = useState("");
  const [category, setCategory] = useState("core"),
    [step, setStep] = useState(0),
    [proof, setProof] = useState<"compact" | "artifact">("compact");
  const [copied, setCopied] = useState(""),
    flow = useRef<HTMLElement>(null);
  const [scroll, setScroll] = useState(0);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}catalog.json`)
      .then((r) => {
        if (!r.ok) throw Error();
        return r.json();
      })
      .then(setCatalog)
      .catch(() => {});
    fetch(`${import.meta.env.BASE_URL}install.txt`)
      .then((r) => {
        if (!r.ok) throw Error();
        return r.text();
      })
      .then(setInstall)
      .catch(() => {});
  }, []);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        setScroll(window.scrollY);
        if (!reduced && !paused && innerWidth > 800 && flow.current) {
          const rect = flow.current.getBoundingClientRect(),
            range = flow.current.offsetHeight - innerHeight;
          if (rect.top <= 100 && rect.bottom > innerHeight * 0.7)
            setStep(
              Math.min(
                4,
                Math.max(
                  0,
                  Math.floor(((-rect.top + 100) / Math.max(1, range)) * 5),
                ),
              ),
            );
        }
      });
    };
    window.addEventListener("scroll", update, { passive: true });
    return () => {
      window.removeEventListener("scroll", update);
      cancelAnimationFrame(frame);
    };
  }, [reduced, paused]);
  async function copy() {
    try {
      await navigator.clipboard.writeText(install);
      setCopied("Copied. Paste it into your agent.");
    } catch {
      setCopied("Select the prompt and press Ctrl+C or ⌘C.");
    }
  }
  const activeCategory = categories[category as keyof typeof categories],
    current = workflow[step];
  return (
    <div className={paused || reduced ? "site motion-off" : "site"}>
      <Background paused={paused} reduced={!!reduced} />
      <div className="background-scrim" />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header wrap">
        <a href="#main" className="brand">
          <img src={asset("lion.png")} width="34" height="34" alt="" />
          hercules<span>/ mcp</span>
        </a>
        <nav aria-label="Main">
          <a href="#agents">Agents</a>
          <a href="#workflow">Workflow</a>
          <a href="#engineering">Engineering</a>
        </nav>
        <a className="header-github" href={github}>
          GitHub ↗
        </a>
      </header>
      <main id="main">
        <section className="hero wrap">
          <motion.div
            className="hero-content"
            initial={reduced ? false : { opacity: 0, y: 28 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: reduced ? 0 : 1, ease: [0.22, 1, 0.36, 1] }}
            style={{
              marginTop:
                reduced || paused ? undefined : Math.min(scroll * 0.1, 55),
            }}
          >
            <p className="eyebrow">
              <span className="live-dot" />
              Open source · Model Context Protocol
            </p>
            <h1>
              A Kali workspace
              <br />
              for your <em>AI agent.</em>
            </h1>
            <div className="hero-bottom">
              <p>
                Connect your agent to security tools.
                <br />
                Keep the runtime explicit.
                <br />
                Keep the evidence yours.
              </p>
              <div className="hero-actions">
                <a href="#install" className="button primary">
                  Install with your agent ↗
                </a>
                <a href={github} className="button secondary">
                  Explore the source ↗
                </a>
              </div>
            </div>
          </motion.div>
          <div className="hero-foot mono">
            <span>Python 3.11+ / Docker / Kali Linux</span>
            <a href="#agents">Meet your next workspace ↓</a>
            <button onClick={() => setPaused(!paused)} aria-pressed={paused}>
              {paused ? "▷ Resume motion" : "Ⅱ Pause motion"}
            </button>
          </div>
        </section>
        <div className="facts wrap">
          <div>
            <strong>{catalog?.full_tool_count ?? 46}</strong>
            <span>tools in the full profile</span>
          </div>
          <div>
            <strong>{catalog?.capabilities.length ?? 22}</strong>
            <span>capability bundles</span>
          </div>
          <div>
            <strong>{catalog?.resource_count ?? 7}</strong>
            <span>agent resources</span>
          </div>
          <div>
            <strong>MIT</strong>
            <span>yours to inspect and build on</span>
          </div>
        </div>
        <section id="agents" className="agents-section section-pad wrap">
          <Heading
            eyebrow="Your agent. Its own interface."
            title={
              <>
                Same Hercules.
                <br />
                Four ways in.
              </>
            }
            description="Watch the connection, inspect the MCP tools, then try a local-lab task. Explore each client’s commands and controls."
          />
          <div className="demo-notice mono">
            <span>
              <span className="live-dot" />
              Interactive browser replicas
            </span>
            <span>Illustrative local lab · execution is simulated</span>
          </div>
          <Suspense
            fallback={
              <div className="terminal-loading mono">
                Loading the terminal interfaces…
              </div>
            }
          >
            <div className="agent-grid">
              {(["claude", "codex", "opencode", "hermes"] as const).map(
                (client, i) => (
                  <AgentTerminal
                    key={client}
                    client={client}
                    offset={i * 0.65}
                    paused={paused}
                    reduced={!!reduced}
                    tools={catalog?.capabilities.flatMap((c) => c.mcp_tools)}
                  />
                ),
              )}
            </div>
          </Suspense>
          <p className="section-note">
            Click a terminal to take over. Its command menu, help, settings, and
            history are interactive. Enlarge a terminal for more room.
          </p>
        </section>
        <section
          id="workflow"
          className="workflow-section section-pad"
          ref={flow}
        >
          <div className="workflow-sticky wrap">
            <Heading
              eyebrow="From a tool call to a file you can inspect"
              title={
                <>
                  Follow the work.
                  <br />
                  Keep the evidence.
                </>
              }
              description="The agent chooses a tool. Hercules owns the session and routes the call. Kali runs it. The host workspace keeps the files."
            />
            <div
              className="flow-diagram"
              role="img"
              aria-label="Agent connects through STDIO to Hercules, which runs selected tools in Kali and retains evidence in a host workspace."
            >
              {[
                "AI agent",
                "Hercules MCP",
                "Kali runtime",
                "Host workspace",
              ].map((name, i) => (
                <div
                  key={name}
                  className={`flow-node ${i === Math.min(current.node, 3) || (step === 4 && i === 3) ? "active" : ""}`}
                >
                  <span className="flow-symbol">
                    {[">_", "H", "◇", "≡"][i]}
                  </span>
                  <strong>{name}</strong>
                  <small>
                    {
                      [
                        "Choose a tool",
                        "Own the session",
                        "Run selected tools",
                        "Retain the evidence",
                      ][i]
                    }
                  </small>
                  {i < 3 && (
                    <span className="flow-edge">
                      {["STDIO / MCP", "DOCKER", "FILES"][i]}
                      <b>→</b>
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div
              className="stage-tabs"
              role="tablist"
              aria-label="Workflow stages"
            >
              {["Connect", "Start", "Run", "Read", "Retain"].map((name, i) => (
                <button
                  role="tab"
                  id={`stage-${i}`}
                  aria-controls="workflow-panel"
                  tabIndex={step === i ? 0 : -1}
                  onKeyDown={(event) => tabKey(event, i, 5, setStep)}
                  aria-selected={step === i}
                  key={name}
                  onClick={() => setStep(i)}
                >
                  <span>0{i + 1}</span>
                  {name}
                </button>
              ))}
            </div>
            <div
              className="workflow-details"
              id="workflow-panel"
              role="tabpanel"
              aria-labelledby={`stage-${step}`}
            >
              <div>
                <p className="eyebrow copper">0{step + 1} / 05</p>
                <h3>{current.title}</h3>
                <p>{current.description}</p>
                <span className="state-tag mono">{current.state}</span>
              </div>
              <div className="response-box">
                <div className="response-header mono">
                  {current.name}
                  <span>ILLUSTRATIVE EXCERPT</span>
                </div>
                <div className="request-row">
                  <small>CALL</small>
                  <pre>{JSON.stringify(current.call, null, 2)}</pre>
                </div>
                <div className="request-row">
                  <small>RESULT</small>
                  <pre>{JSON.stringify(current.result, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </section>
        <section id="toolkit" className="toolkit-section section-pad wrap">
          <Heading
            eyebrow="Choose the capabilities your work needs"
            title={
              <>
                The tools you know.
                <br />
                An interface your agent can use.
              </>
            }
            description="Start with core services. Add reconnaissance, network, web, browser, or other capabilities to match your authorized scope."
          />
          <div className="catalog">
            <div
              className="category-tabs"
              role="tablist"
              aria-label="Tool categories"
            >
              {Object.entries(categories).map(([key, item]) => (
                <button
                  key={key}
                  role="tab"
                  id={`category-${key}`}
                  aria-controls="catalog-panel"
                  tabIndex={key === category ? 0 : -1}
                  onKeyDown={(event) =>
                    tabKey(
                      event,
                      Object.keys(categories).indexOf(key),
                      8,
                      (index) => setCategory(Object.keys(categories)[index]),
                    )
                  }
                  aria-selected={key === category}
                  onClick={() => setCategory(key)}
                >
                  {item.kicker}
                  <span>
                    {catalog?.capabilities
                      .filter((c) => c.category === key)
                      .flatMap((c) => c.mcp_tools).length ?? "—"}
                  </span>
                </button>
              ))}
            </div>
            <div
              className="catalog-detail"
              role="tabpanel"
              id="catalog-panel"
              aria-labelledby={`category-${category}`}
            >
              <p className="eyebrow copper">{activeCategory.kicker}</p>
              <h3>{activeCategory.title}</h3>
              <p>{activeCategory.description}</p>
              <div className="tool-chips">
                {catalog?.capabilities
                  .filter((c) => c.category === category)
                  .flatMap((c) => c.mcp_tools)
                  .map((name) => <span key={name}>{name}</span>) ?? (
                  <a href={`${github}#capabilities-and-mcp-surface`}>
                    Read the repository catalog ↗
                  </a>
                )}
              </div>
              <p className="mono backend-list">{activeCategory.backends}</p>
            </div>
          </div>
        </section>
        <section className="evidence-section section-pad wrap">
          <Reveal className="evidence-grid">
            <div>
              <p className="eyebrow">What the conversation leaves out</p>
              <h2>
                The answer stays small.
                <br />
                The evidence stays available.
              </h2>
              <p>
                A shortened response and lost evidence are different states.
                Hercules reports both, and makes larger files readable in
                bounded chunks.
              </p>
              <div className="evidence-controls">
                {(["compact", "artifact"] as const).map((key) => (
                  <button
                    key={key}
                    onClick={() => setProof(key)}
                    aria-pressed={key === proof}
                  >
                    {key === "compact"
                      ? "Bounded response"
                      : "Read the artifact"}
                  </button>
                ))}
              </div>
            </div>
            <div className="evidence-card">
              <div className="response-header mono">
                {evidence[proof].filename}
                <span>EXAMPLE</span>
              </div>
              <pre>{JSON.stringify(evidence[proof].content, null, 2)}</pre>
              <div className="evidence-foot mono">
                <span>
                  output_complete <b>false</b>
                </span>
                <span>
                  evidence_complete <b className="copper">true</b>
                </span>
              </div>
            </div>
          </Reveal>
        </section>
        <section
          id="engineering"
          className="engineering-section section-pad wrap"
        >
          <Heading
            eyebrow="Inside the repository"
            title={
              <>
                Built around the
                <br />
                parts that need care.
              </>
            }
            description="Lifecycle, ownership, output, and capabilities. Four engineering decisions you can follow into the code."
          />
          <div className="engineering-grid">
            {caseStudies.map((item) => (
              <Reveal className="engineering-item" key={item.label}>
                <div className="engineering-top">
                  <span className="engineering-icon">{item.icon}</span>
                  <span className="eyebrow">{item.label}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
                <pre>{item.code}</pre>
                <a
                  className="text-link"
                  href={`${github}/blob/main/${item.file}`}
                >
                  Read the implementation ↗
                </a>
              </Reveal>
            ))}
          </div>
          <p className="section-note">
            Use Hercules only against systems you have permission to test.
            Configure target scopes for structured tools. Raw shell commands and
            administrator escape hatches require your own care.
          </p>
        </section>
        <section id="install" className="install-section section-pad wrap">
          <Reveal>
            <p className="eyebrow">Bring Hercules to your agent</p>
            <h2>
              Your next workspace
              <br />
              starts with a prompt<span className="copper">.</span>
            </h2>
            <p className="install-description">
              Paste this into your terminal-capable AI agent. It follows the
              repository’s installation contract for your operating system and
              active client.
            </p>
            <div className="install-box">
              <div className="install-header">
                <span className="mono">INSTALL / UPDATE</span>
                <button
                  className="button primary"
                  disabled={!install}
                  onClick={copy}
                >
                  Copy installation prompt ⧉
                </button>
              </div>
              {install ? (
                <pre tabIndex={0}>{install}</pre>
              ) : (
                <p>
                  Loading the installation prompt.{" "}
                  <a href={`${github}#install-with-your-ai-agent`}>
                    Read it on GitHub ↗
                  </a>
                </p>
              )}
              <p className="copy-status" role="status">
                {copied}
              </p>
            </div>
            <div className="install-foot">
              <span>
                Git · uv · Docker · A client with local STDIO MCP support
              </span>
              <a href={`${github}/blob/main/install.md`}>
                Read the setup contract ↗
              </a>
            </div>
          </Reveal>
        </section>
      </main>
      <footer className="site-footer wrap">
        <a className="brand" href="#main">
          <img src={asset("lion.png")} alt="" width="32" height="32" />
          hercules<span>/ mcp</span>
        </a>
        <div>
          Built by <a href="https://github.com/0xMihirK">Mihir Katoch ↗</a>
          <span className="mono">MIT · Authorized use only</span>
        </div>
        <a href="#main">Back to top ↑</a>
      </footer>
    </div>
  );
}
