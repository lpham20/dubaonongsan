import { useEffect, type DependencyList } from "react";

type UseFetchOnceOptions<T> = {
  deps: DependencyList;
  load: (signal: AbortSignal) => Promise<T>;
  onData: (data: T) => void;
  onError?: (error: unknown) => void;
  onFinally?: () => void;
  onReset?: () => void;
  timeoutMs?: number;
};

export function useFetchOnce<T>({
  deps,
  load,
  onData,
  onError,
  onFinally,
  onReset,
  timeoutMs = 20_000
}: UseFetchOnceOptions<T>) {
  useEffect(() => {
    const controller = new AbortController();
    let timedOut = false;
    const timeoutId = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);

    onReset?.();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) onData(data);
      })
      .catch((error) => {
        if (controller.signal.aborted && !timedOut) return;
        onError?.(error);
      })
      .finally(() => {
        window.clearTimeout(timeoutId);
        if (!controller.signal.aborted || timedOut) onFinally?.();
      });

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, deps);
}
