/** Poster first; decoding and buffering wait until the player is nearby. */
export function nearViewport(element, signal) {
  return new Promise((resolve, reject) => {
    let observer;
    const cleanup = () => { observer?.disconnect(); signal.removeEventListener("abort", cancel); };
    const cancel = () => { cleanup(); reject(new DOMException("Discarded capture", "AbortError")); };
    if (signal.aborted) { cancel(); return; }
    if (typeof IntersectionObserver !== "function") { resolve(); return; }
    signal.addEventListener("abort", cancel, { once: true });
    observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { cleanup(); resolve(); }
    }, { rootMargin: "300px" });
    observer.observe(element);
  });
}
