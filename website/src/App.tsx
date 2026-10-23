import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { BeerStein } from "@phosphor-icons/react/BeerStein";
import { useReducedMotion } from "./lib/use-reduced-motion";
import Background from "./components/Background";
import NativePlayer from "./components/NativePlayer";
import StatBand from "./components/StatBand";
import DeferredArchitecture from "./components/DeferredArchitecture";
import Setup from "./components/Setup";
import facts from "./site-facts.json";
import bootstrap from "./bootstrap.json";
import type { NativeManifest } from "./native-types";

gsap.registerPlugin(ScrollTrigger);

const github = "https://github.com/0xMihirK/hercules-mcp";
const support = "https://buymeacoffee.com/mihirkatoch";
const asset = (name: string) => `${import.meta.env.BASE_URL}assets/${name}`;

export default function App() {
  const reduced = useReducedMotion();
  const heroRef = useRef<HTMLElement>(null);
  const [manifest, setManifest] = useState<NativeManifest>(bootstrap as NativeManifest);
  const [catalogError, setCatalogError] = useState(false);
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const recordingBase = asset(`${bootstrap.assetDirectory}/`);

  useEffect(() => {
    const controller = new AbortController();
    fetch(recordingBase + bootstrap.catalogFile, { signal: controller.signal })
      .then(response => { if (!response.ok) throw Error("Playback catalog unavailable"); return response.json(); })
      .then(data => {
        if (data.schemaVersion !== 3 || !data.realTools || data.scriptedToolResults || !Array.isArray(data.recordings) || !data.recordings.length) throw Error("Invalid playback catalog");
        if (!controller.signal.aborted) setManifest(data);
      })
      .catch(() => { if (!controller.signal.aborted) setCatalogError(true); });
    return () => controller.abort();
  }, [recordingBase, catalogAttempt]);

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
    for (const element of document.querySelectorAll("#agents,.deferred-architecture"))
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
    if (reduced || !heroRef.current) return;
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
  }, [reduced]);

  return (
    <div className={`site${reduced ? " motion-off" : ""}`}>
      <Background paused={false} reduced={reduced} />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <div className="site-header-inner wrap">
          <a href="#main" className="brand">
            <img src={asset("lion.png")} width="30" height="30" alt="" />
            hercules<span>/ mcp</span>
            <span className="brand-beta-tag">BETA</span>
          </a>
          <nav aria-label="Main">
            <a href="#agents">Live sessions</a>
            <a href="#architecture">How it works</a>
            <a href="#install">Setup</a>
          </nav>
          <div className="header-actions">
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
                structured offensive-security tools, Obscura automation, and
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
            {catalogError && <p role="alert">Recordings could not load. <button className="button secondary" onClick={() => { setCatalogError(false); setCatalogAttempt(value => value + 1); }}>Retry recordings</button></p>}
            <NativePlayer
              manifest={manifest}
              base={recordingBase}
              reduced={reduced}
              paused={false}
            />
          </div>
        </section>

        <StatBand
          catalog={facts.catalog}
          reduced={reduced}
          paused={false}
        />
        <DeferredArchitecture reduced={reduced} />
        <Setup prompt={facts.installationPrompt} />
      </main>
      <footer className="site-footer">
        <div className="footer-wordmark wrap" aria-hidden="true">
          HERCULES
        </div>
        <div className="site-footer-bar wrap">
          <a href="#main" className="brand">
            <img src={asset("lion.png")} width="26" height="26" alt="" />
            hercules<span>/ mcp</span>
            <span className="brand-beta-tag">BETA</span>
          </a>
          <p>Built for authorized security testing.</p>
          <div className="footer-links">
            <a href={github}>
              Source <ArrowUpRight size={16} />
            </a>
            <a href={`${github}/blob/website/website/CAPTURE.md`}>
              About the recordings <ArrowUpRight size={16} />
            </a>
            <a href={`${github}/blob/main/LICENSE`}>
              License <ArrowUpRight size={16} />
            </a>
          </div>
        </div>
        <a className="footer-toast wrap" href={support} aria-label="Buy me a beer on Buy Me a Coffee">
          <span className="footer-toast-icon" aria-hidden="true"><BeerStein size={30} weight="duotone" /></span>
          <span className="footer-toast-copy"><span>Open source, on tap.</span><strong>Buy me a beer</strong></span>
          <ArrowUpRight size={23} aria-hidden="true" />
        </a>
      </footer>
    </div>
  );
}
