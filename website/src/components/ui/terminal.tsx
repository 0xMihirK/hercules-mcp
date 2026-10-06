"use client";
// Adapted from the user's supplied Terminal component. Native client screens
// use the body slot; the original sequential typing exports remain available.
import {
  Children,
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { motion, useInView, type HTMLMotionProps } from "motion/react";
import { useReducedMotion } from "@/lib/use-reduced-motion";
import { cn } from "@/lib/utils";
type Sequence = {
  active: number;
  started: boolean;
  paused: boolean;
  complete: (index: number) => void;
};
const SequenceContext = createContext<Sequence | null>(null);
const IndexContext = createContext<number>(0);
export function Terminal({
  children,
  className,
  sequence = true,
  startOnView = true,
  paused = false,
  header,
  body,
  playbackKey = 0,
}: {
  children?: ReactNode;
  className?: string;
  sequence?: boolean;
  startOnView?: boolean;
  paused?: boolean;
  header?: ReactNode;
  body?: ReactNode;
  playbackKey?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.15 });
  const [active, setActive] = useState(0);
  useEffect(() => setActive(0), [playbackKey]);
  return (
    <SequenceContext.Provider
      value={
        sequence
          ? {
              active,
              started: !startOnView || inView,
              paused,
              complete: (index) =>
                setActive((current) =>
                  current === index ? current + 1 : current,
                ),
            }
          : null
      }
    >
      <div ref={ref} className={cn("terminal-shell", className)}>
        {header ?? (
          <div className="terminal-chrome">
            <i />
            <i />
            <i />
          </div>
        )}
        {body ?? (
          <pre>
            <code>
              {Children.toArray(children).map((child, index) => (
                <IndexContext.Provider
                  key={`${playbackKey}-${index}`}
                  value={index}
                >
                  {child}
                </IndexContext.Provider>
              ))}
            </code>
          </pre>
        )}
      </div>
    </SequenceContext.Provider>
  );
}
export function TypingAnimation({
  children,
  duration = 60,
  delay = 0,
  startOnView = true,
  className,
}: {
  children: string;
  duration?: number;
  delay?: number;
  startOnView?: boolean;
  className?: string;
}) {
  const sequence = useContext(SequenceContext),
    index = useContext(IndexContext);
  const ref = useRef<HTMLSpanElement>(null),
    inView = useInView(ref, { once: true });
  const reduced = useReducedMotion(),
    [length, setLength] = useState(0);
  const active = sequence
    ? sequence.started && sequence.active === index
    : !startOnView || inView;
  useEffect(() => {
    if (!active || sequence?.paused) return;
    if (reduced || length >= children.length) {
      setLength(children.length);
      sequence?.complete(index);
      return;
    }
    const timer = setTimeout(
      () => setLength((value) => value + 1),
      length === 0 ? delay + duration : duration,
    );
    return () => clearTimeout(timer);
  }, [active, sequence?.paused, length, children, delay, duration, reduced]);
  return (
    <span ref={ref} className={className}>
      {children.slice(0, length)}
    </span>
  );
}
export function AnimatedSpan({
  children,
  delay = 0,
  className,
  ...props
}: HTMLMotionProps<"div"> & { delay?: number }) {
  const sequence = useContext(SequenceContext),
    index = useContext(IndexContext);
  const started = !sequence || (sequence.started && sequence.active >= index);
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: started ? 1 : 0 }}
      transition={{ delay: delay / 1000, duration: 0.25 }}
      onAnimationComplete={() => {
        if (started && !sequence?.paused) sequence?.complete(index);
      }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}
export default Terminal;
