import { describe, expect, it } from "vitest";
import { colorFragment, cogSourceUrl, imageCorners, insertBefore, layerRank } from "@/lib/mapLayers";
import type { Layer } from "@/types/chapter";

const layer = (over: Partial<Layer>): Layer => ({
  id: "x",
  kind: "optical",
  label: "x",
  date: "2026-06-17",
  cog: "data/demo/x.tif",
  render: { type: "rgba" },
  preview: "data/demo/x.png",
  bounds: [-64, -10.5, -62.5, -9.1],
  sourceIds: ["s"],
  status: "illustrative",
  bytes: 1,
  sha256: "0".repeat(64),
  ...over,
});

describe("layer order", () => {
  it("stacks imagery under radar under coherence under displacement under change", () => {
    const kinds = ["optical", "sar-composite", "coherence", "displacement", "change"] as const;
    const ranks = kinds.map(layerRank);
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b));
    expect(new Set(ranks).size).toBe(5);
    expect(layerRank("sar-db")).toBe(layerRank("sar-composite"));
    expect(layerRank("speed")).toBe(layerRank("displacement"));
  });
  it("inserts under the first layer of a higher rank, else under the hillshade", () => {
    const existing = [
      { id: "lyr-sar", rank: 1 },
      { id: "lyr-change", rank: 4 },
    ];
    expect(insertBefore(existing, 0, "hillshade")).toBe("lyr-sar");
    expect(insertBefore(existing, 2, "hillshade")).toBe("lyr-change");
    expect(insertBefore(existing, 4, "hillshade")).toBe("hillshade");
    expect(insertBefore([], 3, "hillshade")).toBe("hillshade");
  });
});

describe("COG source URL", () => {
  const abs = (p: string) => `https://site.test/base/${p}`;
  it("has no fragment for RGBA layers", () => {
    expect(colorFragment({ type: "rgba" })).toBe("");
    expect(cogSourceUrl(layer({}), abs)).toBe("cog://https://site.test/base/data/demo/x.tif");
  });
  it("adds a continuous #color ramp for ramp layers", () => {
    const render: Layer["render"] = { type: "ramp", scheme: "BrewerRdBu11", domain: [-15, 15], unit: "cm" };
    expect(colorFragment(render)).toBe("#color:BrewerRdBu11,-15,15,c");
    expect(cogSourceUrl(layer({ render }), abs)).toBe("cog://https://site.test/base/data/demo/x.tif#color:BrewerRdBu11,-15,15,c");
  });
});

describe("image fallback corners", () => {
  it("orders corners top-left, top-right, bottom-right, bottom-left", () => {
    expect(imageCorners([-64, -10.5, -62.5, -9.1])).toEqual([
      [-64, -9.1],
      [-62.5, -9.1],
      [-62.5, -10.5],
      [-64, -10.5],
    ]);
  });
});
