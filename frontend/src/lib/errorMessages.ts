const TECHNICAL_ERROR_PATTERN = /api|json|unexpected token|doctype|failed to fetch|networkerror|syntaxerror|html|stack|trace|chunkload/i;

export function safeErrorMessage(error: unknown, fallback: string) {
  const raw = error instanceof Error ? error.message : typeof error === "string" ? error : "";
  const clean = raw.trim();
  if (!clean) return fallback;
  if (TECHNICAL_ERROR_PATTERN.test(clean)) return fallback;
  return clean.length > 150 ? fallback : clean;
}

export function messageFromError(error: unknown, fallback: string) {
  return safeErrorMessage(error, fallback);
}
