import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight } from "@phosphor-icons/react/ArrowRight";
import { ArrowUpRight } from "@phosphor-icons/react/ArrowUpRight";
import { Check } from "@phosphor-icons/react/Check";
import { FunnelSimple } from "@phosphor-icons/react/FunnelSimple";
import { WarningCircle } from "@phosphor-icons/react/WarningCircle";
import specimen from "../../assets/filter-example.json";

gsap.registerPlugin(ScrollTrigger);

export type Measurement = {
  tool: string;
  rawCharacters: number;
  inlineResponseCharacters: number;
  characterReduction: number;
  rawTokenEstimate: number;
  inlineTokenEstimate: number;
  outputComplete: boolean;
  evidenceComplete: boolean;
  outputFiltered: boolean;
  rawArtifact: string;
  file?: string;
  caseTitle?: string;
};

const rawLines = specimen.raw.trimEnd().split("\n");
const kept = new Set(specimen.filtered.trimEnd().split("\n"));
const reductionPct = Math.round(
  (1 - specimen.filtered.length / specimen.raw.length) * 100,
);

export default function EvidencePipeline({
  reduced,
  paused,
}: {
  reduced: boolean;
  paused: boolean;
}) {
  const root = useRef<HTMLElement>(null),
    [filtered, setFiltered] = useState(true);

  useEffect(() => {
    if (reduced || paused || !root.current) return;
    setFiltered(false);
    const trigger = ScrollTrigger.create({
      trigger: root.current.querySelector(".filter-demonstration"),
      start: "top 72%",
      once: true,
      onEnter: () => setFiltered(true),
    });
    return () => trigger.kill();
  }, [reduced, paused]);

  useEffect(() => {
    if (!root.current) return;
    const context = gsap.context(() => {
      if (reduced || paused) {
        gsap.set(".filter-noise", { opacity: filtered ? 0.22 : 1 });
        return;
      }
      const timeline = gsap.timeline();
      timeline.to(".filter-noise", {
        opacity: filtered ? 0.2 : 1,
        scaleY: filtered ? 0.92 : 1,
        duration: 0.45,
        stagger: 0.04,
        ease: "power2.out",
      });
      timeline.fromTo(
        ".filter-kept",
        { x: filtered ? -10 : 0 },
        { x: 0, duration: 0.55, stagger: 0.08, ease: "power3.out" },
        0.12,
      );
    }, root);
    return () => context.revert();
  }, [filtered, reduced, paused]);

  return (
    <section
      id="evidence"
      ref={root}
      className="chapter wrap evidence-section"
      aria-labelledby="evidence-title"
    >
      <div className="feature-heading feature-heading--split">
        <h2 id="evidence-title">
          Keep the finding.
          <br />
          Lose the routine noise.
        </h2>
        <p>
          Hercules filters known scanner chatter before it reaches your agent.
          Actionable findings and scan-completion warnings remain in context
          while full raw output is written to disk.
        </p>
      </div>
      <div
        className="pipeline-flow-bar"
        data-ui
        aria-label="Hercules output and evidence pipeline"
      >
        <div className="pipeline-stage">
          <span className="pipeline-stage-step">Raw stdout</span>
          <strong>Tool execution</strong>
          <small>Banners, progress ticks, findings</small>
        </div>
        <ArrowRight size={18} aria-hidden="true" />
        <div className="pipeline-stage is-highlight">
          <span className="pipeline-stage-step">Stream filter</span>
          <strong>
            <code>filter_nikto()</code>
          </strong>
          <small>Strips known routine chatter ({reductionPct}% smaller)</small>
        </div>
        <ArrowRight size={18} aria-hidden="true" />
        <div className="pipeline-stage">
          <span className="pipeline-stage-step">Inline response</span>
          <strong>Agent context</strong>
          <small>Findings + diagnostic flags</small>
        </div>
        <ArrowRight size={18} aria-hidden="true" />
        <div className="pipeline-stage">
          <span className="pipeline-stage-step">Workspace file</span>
          <strong>Raw artifact saved</strong>
          <small>
            <code>/opt/workspace/*.log</code>
          </small>
        </div>
      </div>
      <div className="filter-demonstration">
        <div className="filter-example" data-ui>
          <div className="filter-example-bar">
            <div className="filter-bar-title">
              <span>
                {filtered ? "Filtered response" : "Original scanner output"}
              </span>
              <code className="filter-metrics">
                {filtered
                  ? `${kept.size} of ${rawLines.length} lines kept · −${reductionPct}% chars`
                  : `${rawLines.length} lines · ${specimen.raw.length} chars`}
              </code>
            </div>
            <button onClick={() => setFiltered((value) => !value)}>
              <FunnelSimple size={18} />
              {filtered ? "Compare original" : "Apply filter"}
            </button>
          </div>
          <div
            className="filter-output-lines"
            role="group"
            aria-label={
              filtered ? "Filtered scanner example" : "Original scanner example"
            }
          >
            {rawLines.map((line, i) => {
              const isKept = kept.has(line);
              const isWarning = line.includes("WARNING");
              return (
                <div
                  key={i}
                  aria-hidden={!isKept && filtered}
                  className={
                    isKept
                      ? "filter-kept" + (isWarning ? " is-warning" : "")
                      : "filter-noise"
                  }
                >
                  <span className="line-num">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    className={
                      "line-tag " +
                      (isKept
                        ? isWarning
                          ? "tag-warn"
                          : "tag-kept"
                        : "tag-dropped")
                    }
                  >
                    {isKept ? (isWarning ? "WARN" : "KEPT") : "NOISE"}
                  </span>
                  <code>{line}</code>
                </div>
              );
            })}
          </div>
          <p className="filter-example-note">
            Illustrative lab input, processed by the actual Hercules{" "}
            <code>filter_nikto</code> filter.
          </p>
        </div>
        <div className="filter-explanation">
          <div className="filter-explanation-top">
            <FunnelSimple size={34} />
            <h3>
              A shorter response.
              <br />
              The finding stays.
            </h3>
            <p>
              Removing routine text saves context tokens. Compare the original
              and filtered output: banners and timestamps disappear; the finding
              and incomplete-scan warning stay visible.
            </p>
          </div>
          <div className="filter-keeps">
            <span>
              <Check size={18} />
              Finding retained
            </span>
            <span>
              <WarningCircle size={18} />
              Incomplete scan disclosed
            </span>
          </div>
          <div className="filter-flags-box" data-ui>
            <span className="filter-flags-title">Response envelope flags</span>
            <div className="filter-flag-row">
              <code>output_filtered: true</code>
              <span>Chatter stripped before returning</span>
            </div>
            <div className="filter-flag-row">
              <code>output_complete: true</code>
              <span>Inline text was not truncated</span>
            </div>
            <div className="filter-flag-row">
              <code>evidence_complete: true</code>
              <span>Full raw log saved in workspace</span>
            </div>
          </div>
          <p className="output-limit-inline">
            Filters remove characterized noise while separate size limits bound
            large responses and retain complete files on disk.
          </p>
          <a
            className="text-link"
            href="https://github.com/0xMihirK/hercules-mcp#output-artifacts-sessions-and-workspaces"
          >
            How output filtering works <ArrowUpRight size={18} />
          </a>
        </div>
      </div>
    </section>
  );
}
