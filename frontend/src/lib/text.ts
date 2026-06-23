/** Normalize Vietnamese text to NFC so serif fonts render precomposed marks correctly. */
export function toNFC(value: string | null | undefined): string {
  return (value ?? "").normalize("NFC");
}
