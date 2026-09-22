export type SortValue = string | number | null;
export type SortDirection = "ascending" | "descending";

// Missing values stay last; ties retain the source order in both directions.
export function sortRowIndices(
  values: SortValue[],
  direction: SortDirection,
): number[] {
  return values
    .map((_, i) => i)
    .sort((a, b) => {
      const av = values[a],
        bv = values[b];
      if (av === null && bv === null) return a - b;
      if (av === null) return 1;
      if (bv === null) return -1;
      const compared =
        typeof av === "number" && typeof bv === "number"
          ? av - bv
          : String(av).localeCompare(String(bv), "en", {
              numeric: true,
              sensitivity: "base",
            });
      return (direction === "ascending" ? compared : -compared) || a - b;
    });
}

export function displayedSortValue(text: string): SortValue {
  const value = text.trim();
  if (!value || value === "Unavailable") return null;
  // Timing cells sort by the leading median, not their min/max interval.
  if (/^[+-]?[\d,]+(?:\.\d+)?%?(?: \[[^\]]+\])?$/.test(value)) {
    return Number.parseFloat(value.replaceAll(",", ""));
  }
  return value;
}
