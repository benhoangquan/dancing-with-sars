// Number, unit and coordinate formatting. Every number on screen goes through here so it renders
// with a true minus sign and thousands separators (pair with the `tabular` utility class).
import type { Stat, Unit } from "@/types/chapter";

const MINUS = "−";

export function formatNumber(value: number, decimals = 0): string {
  const text = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
  return text.replace("-", MINUS);
}

const SUFFIX: Record<Unit, string> = {
  dB: " dB",
  cm: " cm",
  ha: " ha",
  m: " m",
  ratio: "",
  "%": "%",
  count: "",
  "cm/month": " cm/month",
  "m/day": " m/day",
  "cm/yr": " cm/yr",
  km2: " km²",
  km: " km",
};

export const unitSuffix = (unit: Unit) => SUFFIX[unit];

/** A stat as text, for example "7,648 ha" or "−12.0 cm". */
export const formatStat = (s: Pick<Stat, "value" | "unit" | "decimals">) =>
  `${formatNumber(s.value, s.decimals)}${unitSuffix(s.unit)}`;

/** "9.98° S, 63.35° W" (latitude first). */
export function formatCoordinate(lon: number, lat: number): string {
  const ns = lat < 0 ? "S" : "N";
  const ew = lon < 0 ? "W" : "E";
  return `${Math.abs(lat).toFixed(2)}° ${ns}, ${Math.abs(lon).toFixed(2)}° ${ew}`;
}
