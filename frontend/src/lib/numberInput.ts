export function finiteNumber(value: number | string, fallback = 0) {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export function minNumber(value: number | string, min: number, fallback = min) {
  return Math.max(min, finiteNumber(value, fallback));
}

export function numberInputValue(value: string, min: number, fallback = min) {
  return minNumber(value, min, fallback);
}
