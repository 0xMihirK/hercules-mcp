import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { CatalogData } from "./ToolChains";

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
          <dd>
            <strong
              className="stat-value"
              data-target={catalog.full_tool_count}
            >
              {catalog.full_tool_count}
            </strong>
            <span>
              {catalog.without_metasploit_tool_count} with SKIP_METASPLOIT
            </span>
          </dd>
          <dt>Registered MCP tools</dt>
        </div>
        <div className="stat-cell">
          <dd>
            <strong
              className="stat-value"
              data-target={catalog.capabilities.length}
            >
              {catalog.capabilities.length}
            </strong>
            <span>Across {catalog.categories.length} security domains</span>
          </dd>
          <dt>Capability bundles</dt>
        </div>
        <div className="stat-cell">
          <dd>
            <strong className="stat-value" data-target={catalog.resource_count}>
              {catalog.resource_count}
            </strong>
            <span>NSE, Nuclei, PEAS, GTFOBins, LOLBAS</span>
          </dd>
          <dt>Agent resources</dt>
        </div>
        <div className="stat-cell">
          <dd>
            <strong className="stat-value" data-target={120}>
              120
            </strong>
            <span>4 native clients · 10 investigations</span>
          </dd>
          <dt>Validated lab sessions</dt>
        </div>
      </dl>
    </section>
  );
}
