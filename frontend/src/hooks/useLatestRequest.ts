import { useCallback, useEffect, useRef } from "react";

/** Only the latest read may update the screen, including after unmount. */
export function useLatestRequest() {
  const sequence = useRef(0);
  useEffect(() => () => { sequence.current += 1; }, []);
  return useCallback(() => {
    const request = ++sequence.current;
    return () => request === sequence.current;
  }, []);
}
