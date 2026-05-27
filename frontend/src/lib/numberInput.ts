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

export function decimalInputValue(value: string, options: { allowNegative?: boolean } = {}) {
  const compact = value.replace(/\s/g, "").replace(options.allowNegative ? /[^\d.,-]/g : /[^\d.,]/g, "");
  const negative = Boolean(options.allowNegative && compact.startsWith("-"));
  const unsigned = compact.replace(/-/g, "");
  const separatorIndex = unsigned.search(/[.,]/);

  if (separatorIndex < 0) {
    return `${negative ? "-" : ""}${unsigned.replace(/[.,]/g, "")}`;
  }

  const before = unsigned.slice(0, separatorIndex).replace(/[.,]/g, "");
  const separator = unsigned[separatorIndex];
  const after = unsigned.slice(separatorIndex + 1).replace(/[.,]/g, "");
  return `${negative ? "-" : ""}${before}${separator}${after}`;
}

export function parseDecimalInput(value: string): number | null {
  const normalized = value.trim().replace(/\s/g, "").replace(",", ".");
  if (!normalized || normalized === "." || normalized === "-" || normalized === "-.") return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}
