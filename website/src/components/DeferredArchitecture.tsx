import { useEffect, useRef, useState } from "react";
import type ArchitectureScene from "./ArchitectureScene";

export default function DeferredArchitecture({ reduced }: { reduced: boolean }) {
  const host = useRef<HTMLDivElement>(null);
  const [Scene, setScene] = useState<typeof ArchitectureScene | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true, loading = false;
    const load = () => {
      if (loading) return;
      loading = true;
      import("./ArchitectureScene").then(module => {
        if (live) setScene(() => module.default);
      }).catch(() => { if (live) setFailed(true); });
    };
    const anchor = () => { if (location.hash === "#architecture") load(); };
    if (typeof IntersectionObserver !== "function") {
      load();
      return () => { live = false; };
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { observer.disconnect(); load(); }
    }, { rootMargin: "800px" });
    observer.observe(host.current!);
    window.addEventListener("hashchange", anchor);
    anchor();
    return () => { live = false; observer.disconnect(); window.removeEventListener("hashchange", anchor); };
  }, []);
  return <div ref={host} className="deferred-architecture">
    {Scene ? <Scene reduced={reduced} paused={false} /> :
      <section id="architecture" className="chapter architecture architecture-placeholder" aria-labelledby="architecture-title" aria-busy={!failed}>
        <div className="wrap">
          <div className="feature-heading architecture-heading">
            <div><h2 id="architecture-title">Powerful tools.<br />A separate workspace.</h2></div>
            <p>Your agent coordinates the investigation. Hercules brings browser control and Kali tools together in Docker, manages their workspaces, and filters the output returned to your agent.</p>
          </div>
          {failed && <p role="alert">The architecture diagram could not load. <button className="button secondary" onClick={() => location.reload()}>Reload page</button></p>}
        </div>
      </section>}
  </div>;
}
