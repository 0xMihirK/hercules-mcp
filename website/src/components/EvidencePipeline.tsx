import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, DownloadSimple } from "@phosphor-icons/react";
gsap.registerPlugin(ScrollTrigger);
export type Measurement = { tool: string; rawCharacters: number; inlineResponseCharacters: number; characterReduction: number; rawTokenEstimate: number; inlineTokenEstimate: number; outputComplete: boolean; evidenceComplete: boolean; outputFiltered: boolean; rawArtifact: string; file?: string; caseTitle?: string };
const stages = ["Raw output", "Preserved diagnostics", "Filtered findings", "Bounded response", "Readable artifacts"];

export default function EvidencePipeline({ reduced, paused, measurement, base }: { reduced: boolean; paused: boolean; measurement: Measurement | null; base: string }) {
  const root = useRef<HTMLElement>(null);
  useEffect(() => {
    if (reduced || paused || !root.current) return;
    const media = gsap.matchMedia();
    media.add("(min-width: 1000px)", () => {
      const context = gsap.context(() => {
        const timeline=gsap.timeline({scrollTrigger:{trigger:root.current,start:"top 85%",end:"center center",scrub:.7}});
        timeline.fromTo(".evidence-illustration",{scale:.8},{scale:1,ease:"none",duration:1},0);
        timeline.fromTo(".pipeline-stage",{opacity:.4,y:12},{opacity:1,y:0,stagger:.15,duration:.4,ease:"none"},0);
      }, root);
      return () => context.revert();
    });
    return () => media.revert();
  }, [reduced, paused]);
  return <section id="evidence" ref={root} className="chapter wrap evidence-section">
    <div className="chapter-heading"><h2>Less noise in context.<br />More evidence on disk.</h2><p>Tool-specific filters extract useful findings. Bounded responses keep the conversation manageable, while raw artifacts preserve the diagnostics you may need next.</p></div>
    <ol className="output-pipeline">{stages.map((stage,i) => <li className="pipeline-stage" key={stage}><span>{stage}</span>{i < 4 && <ArrowRight size={20} aria-hidden="true" />}</li>)}</ol>
    <div className="evidence-layout"><div className="evidence-paper"><img className="evidence-illustration" src={`${import.meta.env.BASE_URL}assets/illustrations/evidence-stack.png`} width="1536" height="1024" alt="Graphite and copper illustration of layered report pages and preserved evidence." loading="lazy" decoding="async" /><span>Illustration · evidence layers</span></div><div className="evidence-explanation">
      <h3>Measure the response.<br />Keep the original.</h3>
      {measurement ? <><p className="measurement-source">Measured from a real local <code>{measurement.tool}</code> call. Includes serialized response metadata.</p><div className="character-comparison"><div><span>Raw output</span><strong>{measurement.rawCharacters.toLocaleString()}</strong><small>characters · ~{measurement.rawTokenEstimate.toLocaleString()} tokens</small></div><ArrowRight size={24} aria-hidden="true" /><div><span>Inline response</span><strong>{measurement.inlineResponseCharacters.toLocaleString()}</strong><small>characters · ~{measurement.inlineTokenEstimate.toLocaleString()} tokens</small></div></div><p>{measurement.characterReduction > 0 ? `${measurement.characterReduction}% fewer characters in this response.` : "This response’s metadata adds characters; reduction varies by tool and output."} Token estimates use characters ÷ 4, rounded up. They are approximate.</p>{measurement.file && <a className="text-link" href={base + measurement.file} download><DownloadSimple size={20} aria-hidden="true" />Inspect the raw artifact</a>}</> : <p>Measurements will appear with validated lab artifacts. No estimated savings are presented as measured results.</p>}
      {measurement?.caseTitle && <p className="measurement-case">Capture: {measurement.caseTitle}. This is one observed call, not an average or a promised saving.</p>}
      {measurement && !measurement.outputFiltered && <p className="measurement-case">This call demonstrates response bounding. Semantic filtering was not applied.</p>}
      <dl className="completeness"><div><dt><code>output_complete</code>{measurement && <span className="complete-value">{String(measurement.outputComplete)}</span>}</dt><dd>Whether the inline response contains the full tool output.</dd></div><div><dt><code>evidence_complete</code>{measurement && <span className="complete-value">{String(measurement.evidenceComplete)}</span>}</dt><dd>Whether the available artifacts preserve the captured evidence.</dd></div></dl><p>Neither flag proves that an investigation is exhaustive. Reports should state scope, rejected leads and untested assumptions.</p>
    </div></div>
  </section>;
}
