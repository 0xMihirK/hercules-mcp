import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { TerminalWindow } from "@phosphor-icons/react/TerminalWindow";
import { Stack } from "@phosphor-icons/react/Stack";
import { Books } from "@phosphor-icons/react/Books";
export type CatalogItem = {
  key: string;
  category: string;
  description: string;
  mandatory: boolean;
  mcp_tools: string[];
  backend_binaries: string[];
  wordlists: string[];
  metasploit: boolean;
  browser: boolean;
  note: string;
};

export type CatalogData = {
  full_tool_count: number;
  without_metasploit_tool_count: number;
  resource_count: number;
  categories: { key: string; title: string }[];
  capabilities: CatalogItem[];
};

gsap.registerPlugin(ScrollTrigger);

export default function StatBand({
  catalog,
  reduced,
  paused,
}: {
  catalog: CatalogData;
  reduced: boolean;
  paused: boolean;
}) {
  const root = useRef<HTMLElement>(null);

  useEffect(() => {
    if (reduced || paused || !root.current) return;
    const context = gsap.context(() => {
      const numbers = gsap.utils.toArray<HTMLElement>(".stat-value");
      numbers.forEach((el) => {
        const target = Number(el.dataset.target || el.textContent || "0");
        if (!target) return;
        const counter = { val: 0 };
        gsap.fromTo(
          counter,
          { val: 0 },
          {
            val: target,
            duration: 0.65,
            ease: "power2.out",
            snap: { val: 1 },
            scrollTrigger: {
              trigger: root.current,
              start: "top 92%",
              once: true,
            },
            onUpdate() {
              el.textContent = String(Math.round(counter.val));
            },
            onComplete() {
              el.textContent = String(target);
            },
          },
        );
      });
      gsap.fromTo(
        ".stat-cell",
        { y: 18, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.55,
          stagger: 0.06,
          ease: "power3.out",
          clearProps: "all",
          scrollTrigger: {
            trigger: root.current,
            start: "top 92%",
            once: true,
          },
        },
      );
    }, root);
    return () => context.revert();
  }, [reduced, paused]);

  return (
    <section
      ref={root}
      className="stat-band"
      aria-label="Hercules MCP architecture summary"
    >
      <dl className="stat-band-grid wrap">
        <div className="stat-cell">
          <dt>Registered MCP tools</dt>
          <dd>
            <strong
              className="stat-value"
              data-target={catalog.full_tool_count}
            >
              {catalog.full_tool_count}
            </strong>
            <span>
              {catalog.without_metasploit_tool_count} without Metasploit
            </span>
          </dd>
          <span className="stat-illustration" aria-hidden="true"><TerminalWindow size={40} weight="regular" /></span>
        </div>
        <div className="stat-cell">
          <dt>Capability bundles</dt>
          <dd>
            <strong
              className="stat-value"
              data-target={catalog.capabilities.length}
            >
              {catalog.capabilities.length}
            </strong>
            <span>Across {catalog.categories.length} security domains</span>
          </dd>
          <span className="stat-illustration" aria-hidden="true"><Stack size={40} weight="regular" /></span>
        </div>
        <div className="stat-cell">
          <dt>Agent resources</dt>
          <dd>
            <strong className="stat-value" data-target={catalog.resource_count}>
              {catalog.resource_count}
            </strong>
            <span>PEAS · PowerUp · GTFOBins · LOLBAS</span>
          </dd>
          <span className="stat-illustration" aria-hidden="true"><Books size={40} weight="regular" /></span>
        </div>
      </dl>
    </section>
  );
}
