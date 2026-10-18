import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowDown } from "@phosphor-icons/react/ArrowDown";
import { Pause } from "@phosphor-icons/react/Pause";
import { Play } from "@phosphor-icons/react/Play";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { useReducedMotion } from "./lib/use-reduced-motion";
import Background from "./components/Background";
import NativePlayer from "./components/NativePlayer";
import StatBand from "./components/StatBand";
import ToolChains from "./components/ToolChains";
import ArchitectureScene from "./components/ArchitectureScene";
import EvidencePipeline from "./components/EvidencePipeline";
import Setup from "./components/Setup";
import facts from "./site-facts.json";
import bootstrap from "./bootstrap.json";
import type { NativeManifest } from "./native-types";

gsap.registerPlugin(ScrollTrigger);

const github = "https://github.com/0xMihirK/hercules-mcp";
const asset = (name: string) => `${import.meta.env.BASE_URL}assets/${name}`;

export default function App() {
  const reduced = useReducedMotion(),
    [paused, setPaused] = useState(false);
  const heroRef = useRef<HTMLElement>(null);
  const [manifest, setManifest] = useState<NativeManifest | null>(
    bootstrap.schemaVersion === 3 ? (bootstrap as unknown as NativeManifest) : null,
  );
  const recordingBase = asset(`${bootstrap.assetDirectory}/`);

  useEffect(() => {
    let frame = 0,
      live = true;
    const refresh = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        if (live) ScrollTrigger.refresh();
      });
    };
    const observer = new ResizeObserver(refresh);
    for (const element of document.querySelectorAll("#agents,#tools"))
      observer.observe(element);
    document.fonts.ready.then(() => {
      if (live) refresh();
    });
    return () => {
      live = false;
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    if (reduced || paused || !heroRef.current) return;
    const context = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(
        ".hero-line-inner",
        { y: 28, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.65, stagger: 0.08, clearProps: "all" },
      )
        .fromTo(
          ".hero-side",
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.55, clearProps: "all" },
          "-=0.4",
        )
        .fromTo(
          ".hero-stage",
          { y: 26, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.65, clearProps: "all" },
          "-=0.35",
        );
    }, heroRef);
    return () => context.revert();
  }, [reduced, paused]);

  useEffect(() => {
    if (typeof fetch !== "function") return;
    const controller = new AbortController();
    fetch(recordingBase + "manifest.json", {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((r) => {
        if (!r.ok) throw Error("Native manifest unavailable");
        return r.json();
      })
      .then((data) => {
        if (data.schemaVersion === 3 && data.realTools && !data.scriptedToolResults)
          setManifest(data);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [recordingBase]);

  return (
    <div className={`site${paused || reduced ? " motion-off" : ""}`}>
      <Background paused={paused} reduced={reduced} />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="site-header-inner wrap">
          <a href="#main" className="brand">
            <img src={asset("lion.svg")} width="30" height="30" alt="" />
            hercules<span>/ mcp</span>
          </a>
          <nav aria-label="Main">
            <a href="#agents">Live sessions</a>
            <a href="#tools">Capabilities</a>
            <a href="#architecture">How it works</a>
            <a href="#evidence">Evidence</a>
            <a href="#install">Setup</a>
          </nav>
          <div className="header-actions">
            <button
              className="motion-control"
              aria-pressed={paused}
              aria-label={paused ? "Resume page motion" : "Pause page motion"}
              onClick={() => setPaused((value) => !value)}
            >
              {paused ? (
                <Play size={16} aria-hidden="true" />
              ) : (
                <Pause size={16} aria-hidden="true" />
              )}
              <span>{paused ? "Resume motion" : "Pause motion"}</span>
            </button>
            <a className="header-github" href={github}>
              GitHub <ArrowUpRight size={16} aria-hidden="true" />
            </a>
          </div>
        </div>
      </header>
      <main id="main">
        <section ref={heroRef} className="hero" aria-labelledby="hero-title">
          <div className="hero-head wrap">
            <h1 id="hero-title">
              <span className="hero-line">
                <span className="hero-line-inner">A Kali workspace</span>
              </span>
              <span className="hero-line">
                <span className="hero-line-inner">for your AI agent.</span>
              </span>
            </h1>
            <div className="hero-side">
              <p className="hero-lede">
                Connect terminal-capable agents to {facts.catalog.full_tool_count}{" "}
                structured offensive-security tools, CloakBrowser automation, and
                Metasploit RPC inside an explicitly started, session-owned Kali
                Docker container—with bounded inline output and retained host
                workspace evidence.
              </p>
              <div className="hero-actions">
                <a className="button primary" href="#install">
                  Install with your agent <ArrowUpRight size={18} aria-hidden="true" />
                </a>
                <a className="button secondary" href={github}>
                  Explore the source <ArrowUpRight size={18} aria-hidden="true" />
                </a>
              </div>
            </div>
          </div>

          <div id="agents" className="hero-stage wrap" aria-label="Recorded native agent sessions">
            <div className="stage-topline">
              <div className="stage-topline-left">
                <span className="live-indicator" aria-hidden="true" />
                <strong>Native agent sessions</strong>
                <span className="recording-provenance">
                  Real Docker tool execution · scripted model prompts · 10 local-lab investigations
                </span>
              </div>
              <p className="stage-topline-note">
                Switch clients or select any investigation scenario below.
              </p>
            </div>
            <NativePlayer
              manifest={manifest}
              base={recordingBase}
              reduced={reduced}
              paused={paused}
            />
            <div className="session-note">
              <p>
                Tools execute in disposable local Docker labs and return real
                results. Model responses and decisions are scripted. No public
                targets are contacted.
              </p>
              <a href="#tools">
                Explore the capabilities <ArrowDown size={18} aria-hidden="true" />
              </a>
            </div>
          </div>
        </section>

        <StatBand
          catalog={facts.catalog}
          reduced={reduced}
          paused={paused}
        />
        <ToolChains
          catalog={facts.catalog}
          reduced={reduced}
          paused={paused}
        />
        <ArchitectureScene reduced={reduced} paused={paused} />
        <EvidencePipeline reduced={reduced} paused={paused} />
        <Setup prompt={facts.installationPrompt} />
      </main>
      <footer className="site-footer">
        <div className="footer-wordmark wrap" aria-hidden="true">
          HERCULES
        </div>
        <div className="site-footer-bar wrap">
          <a href="#main" className="brand">
            <img src={asset("lion.svg")} width="26" height="26" alt="" />
            hercules<span>/ mcp</span>
          </a>
          <p>Built for authorized security testing.</p>
          <div className="footer-links">
            <a href={github}>
              Source <ArrowUpRight size={16} />
            </a>
            <a href={`${github}/blob/main/website/CAPTURE.md`}>
              About the recordings <ArrowUpRight size={16} />
            </a>
            <a href={`${github}/blob/main/LICENSE`}>
              License <ArrowUpRight size={16} />
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
