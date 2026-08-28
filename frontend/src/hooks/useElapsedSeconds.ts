import { useEffect, useState } from "react";

/** Ticks once a second while `active` is true, resetting to 0 whenever it
 * flips from false to true. Used to show "还在跑，不是卡住了" during
 * long-running mutations (collector runs, event analysis) that can
 * legitimately take minutes once an LLM call is on the critical path.
 *
 * oxlint's react(set-state-in-effect) flags the reset below -- it's a
 * legitimate case though (re-initializing a stopwatch when `active` flips
 * true is standard for this kind of hook), and every alternative tried
 * (deriving from a ref, computing Date.now() during render) trips other
 * react() purity/refs rules instead. Accepting this one warning. */
export function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!active) return;
    setSeconds(0);
    const start = Date.now();
    const timer = setInterval(() => setSeconds(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [active]);

  return seconds;
}
