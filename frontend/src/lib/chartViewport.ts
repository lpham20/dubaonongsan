import { useEffect, useState } from "react";

export type ChartRange = {
  startIndex: number;
  endIndex: number;
};

export const CHART_DEFAULT_VISIBLE_POINTS = {
  coarse: 48,
  fine: 120
} as const;

export const CHART_MIN_VISIBLE_POINTS = {
  coarse: 10,
  fine: 14
} as const;

export const CHART_CAN_ZOOM_POINT_COUNT = 14;
export const CHART_ZOOM_IN_FACTOR = 0.58;
export const CHART_ZOOM_OUT_FACTOR = 1.72;
export const CHART_PAN_FRACTION = 0.45;

export function useCoarseChartPointer(): boolean {
  const getInitialValue = () =>
    typeof window === "undefined" ? true : window.matchMedia("(pointer: coarse), (max-width: 1180px)").matches;
  const [isCoarse, setIsCoarse] = useState(getInitialValue);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(pointer: coarse), (max-width: 1180px)");
    const update = () => setIsCoarse(mediaQuery.matches);
    update();
    if (typeof mediaQuery.addEventListener === "function") {
      mediaQuery.addEventListener("change", update);
      return () => mediaQuery.removeEventListener("change", update);
    }
    mediaQuery.addListener(update);
    return () => mediaQuery.removeListener(update);
  }, []);

  return isCoarse;
}

export function clampChartRange(range: ChartRange, fullEndIndex: number) {
  const endLimit = Math.max(0, fullEndIndex);
  const startIndex = Math.min(Math.max(0, range.startIndex), endLimit);
  const endIndex = Math.min(Math.max(startIndex, range.endIndex), endLimit);
  return { startIndex, endIndex };
}

function defaultChartRange(totalPoints: number, isCoarsePointer: boolean) {
  const fullEndIndex = Math.max(totalPoints - 1, 0);
  const defaultVisiblePoints = isCoarsePointer ? CHART_DEFAULT_VISIBLE_POINTS.coarse : CHART_DEFAULT_VISIBLE_POINTS.fine;
  return { startIndex: Math.max(0, fullEndIndex - defaultVisiblePoints + 1), endIndex: fullEndIndex };
}

export function useChartViewport(totalPoints: number, isCoarsePointer: boolean) {
  const [zoomRange, setZoomRange] = useState<ChartRange | null>(null);
  const fullEndIndex = Math.max(totalPoints - 1, 0);
  const defaultZoomRange = defaultChartRange(totalPoints, isCoarsePointer);
  const activeZoomRange = clampChartRange(zoomRange ?? defaultZoomRange, fullEndIndex);
  const canZoom = totalPoints > CHART_CAN_ZOOM_POINT_COUNT;
  const showBrush = canZoom && !isCoarsePointer;
  const activeWindowLength = activeZoomRange.endIndex - activeZoomRange.startIndex + 1;
  const maxWindowStart = Math.max(0, totalPoints - activeWindowLength);
  const panWindowStep = Math.max(1, Math.round(activeWindowLength * CHART_PAN_FRACTION));

  useEffect(() => {
    setZoomRange(null);
  }, [isCoarsePointer, totalPoints]);

  function updateZoom(nextRange: ChartRange) {
    const clamped = clampChartRange(nextRange, fullEndIndex);
    setZoomRange((current) => {
      const previous = clampChartRange(current ?? defaultZoomRange, fullEndIndex);
      if (previous.startIndex === clamped.startIndex && previous.endIndex === clamped.endIndex) {
        return current;
      }
      return clamped;
    });
  }

  function zoomBy(factor: number) {
    if (!canZoom) return;
    const minVisiblePoints = isCoarsePointer ? CHART_MIN_VISIBLE_POINTS.coarse : CHART_MIN_VISIBLE_POINTS.fine;
    const nextLength = Math.min(totalPoints, Math.max(minVisiblePoints, Math.round(activeWindowLength * factor)));
    if (nextLength >= totalPoints) {
      updateZoom({ startIndex: 0, endIndex: fullEndIndex });
      return;
    }
    const center = (activeZoomRange.startIndex + activeZoomRange.endIndex) / 2;
    const startIndex = Math.round(center - nextLength / 2);
    updateZoom({ startIndex, endIndex: startIndex + nextLength - 1 });
  }

  function panBy(steps: number) {
    if (!canZoom) return;
    updateZoom({ startIndex: activeZoomRange.startIndex + steps, endIndex: activeZoomRange.endIndex + steps });
  }

  function setWindowStart(startIndex: number) {
    if (!canZoom) return;
    updateZoom({ startIndex, endIndex: startIndex + activeWindowLength - 1 });
  }

  function resetZoom() {
    setZoomRange({ startIndex: 0, endIndex: fullEndIndex });
  }

  return {
    activeZoomRange,
    activeWindowLength,
    canZoom,
    maxWindowStart,
    panBy,
    panWindowStep,
    resetZoom,
    setWindowStart,
    showBrush,
    updateZoom,
    zoomBy
  };
}
