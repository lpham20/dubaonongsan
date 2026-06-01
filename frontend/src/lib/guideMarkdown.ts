export function guideHeadingId(value: string) {
  return Array.from(value.toLocaleLowerCase("vi-VN"))
    .map((character) => {
      if (/\s/u.test(character)) return "-";
      if (character === "-") return character;
      return /[\p{L}\p{N}\p{M}]/u.test(character) ? character : "";
    })
    .join("")
    .replace(/^-+|-+$/g, "");
}
