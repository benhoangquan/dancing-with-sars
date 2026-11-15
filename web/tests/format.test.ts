import { describe, expect, it } from "vitest";
import { formatCoordinate, formatNumber, formatStat, unitSuffix } from "@/lib/format";
import { fillTokens, splitTokens } from "@/lib/tokens";
import type { Stat } from "@/types/chapter";

const stat = (value: number, unit: Stat["unit"], decimals: number): Stat => ({
  value,
  unit,
  decimals,
  label: "x",
  method: "x",
});

describe("format", () => {
  it("uses thousands separators and a true minus sign", () => {
    expect(formatNumber(7648)).toBe("7,648");
    expect(formatNumber(-12, 1)).toBe("−12.0");
    expect(formatNumber(1234567.891, 2)).toBe("1,234,567.89");
  });
  it("appends unit suffixes, none for counts and ratios", () => {
    expect(formatStat(stat(7648, "ha", 0))).toBe("7,648 ha");
    expect(formatStat(stat(5.5, "dB", 1))).toBe("5.5 dB");
    expect(formatStat(stat(55, "%", 0))).toBe("55%");
    expect(formatStat(stat(3.4, "cm/month", 1))).toBe("3.4 cm/month");
    expect(formatStat(stat(38.5, "m/day", 1))).toBe("38.5 m/day");
    expect(formatStat(stat(10, "count", 0))).toBe("10");
    expect(unitSuffix("ratio")).toBe("");
  });
  it("formats coordinates latitude first with hemispheres", () => {
    expect(formatCoordinate(-63.35, -9.98)).toBe("9.98° S, 63.35° W");
    expect(formatCoordinate(110.5, 6.9)).toBe("6.90° N, 110.50° E");
  });
});

describe("tokens", () => {
  const stats = { cleared_ha: stat(7648, "ha", 0), hv_drop_db: stat(5.5, "dB", 1) };
  it("fills tokens with formatted stats", () => {
    expect(fillTokens("Lost {stat:cleared_ha}; HV fell {stat:hv_drop_db}.", { stats })).toBe(
      "Lost 7,648 ha; HV fell 5.5 dB.",
    );
  });
  it("splits text so each stat can render in its own span", () => {
    expect(splitTokens("a {stat:cleared_ha} b", { stats })).toEqual([
      { kind: "text", text: "a " },
      { kind: "stat", key: "cleared_ha", text: "7,648 ha" },
      { kind: "text", text: " b" },
    ]);
  });
  it("leaves text without tokens alone and throws on an unknown stat", () => {
    expect(fillTokens("plain", { stats })).toBe("plain");
    expect(() => fillTokens("{stat:nope}", { stats })).toThrow(/no stat/);
  });
});

describe("facts and scale anchors", () => {
  const stats = { cleared_ha: stat(374, "ha", 0), hv_drop_db: stat(6.0, "dB", 1) };
  const fact = { id: "sinking", value: 13, unit: "cm/yr" as const, decimals: 0, label: "x", source: { name: "s", url: "https://x.test", accessed: "2026-11-15" } };
  it("resolve facts and attach the everyday comparison", () => {
    const parts = splitTokens("Sank {fact:sinking} and lost {stat:cleared_ha}.", {
      stats,
      facts: [fact],
      anchors: { sinking: "per-decade", cleared_ha: "central-park" },
    });
    expect(parts[1]).toMatchObject({ kind: "fact", text: "13 cm/yr", anchor: "1.3 m per decade" });
    expect(parts[3]).toMatchObject({ kind: "stat", key: "cleared_ha" });
    expect((parts[3] as { anchor: string }).anchor).toMatch(/Central Park/);
  });
  it("throw on unknown facts", () => expect(() => fillTokens("{fact:nope}", { stats })).toThrow(/no fact/));
});
