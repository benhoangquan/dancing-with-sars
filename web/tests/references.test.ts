import { describe, expect, it } from "vitest";
import { anchorText } from "@/lib/references";

describe("scale anchors", () => {
  it("compare hectares with Central Park (341 ha)", () => {
    expect(anchorText("central-park", 374, "ha")).toBe("about 1.1 × Central Park");
    expect(anchorText("central-park", 2534, "ha")).toBe("about 7.4 × Central Park");
    expect(anchorText("central-park", 170, "ha")).toBe("about 50% of Central Park");
  });
  it("convert km² before comparing", () => expect(anchorText("manhattan", 58.69, "km2")).toBe("about 1.0 × Manhattan"));
  it("count football pitches", () => expect(anchorText("football-pitch", 7.14, "ha")).toBe("about 10 football pitches"));
  it("turn a dB drop into echo strength", () => {
    expect(anchorText("echo-power", 6.0, "dB")).toBe("the echo fell to about 1/4 of its strength");
    expect(anchorText("echo-power", 0.8, "dB")).toBe("an echo about 17% weaker");
  });
  it("scale a rate to a decade", () => {
    expect(anchorText("per-decade", 13, "cm/yr")).toBe("1.3 m per decade");
    expect(anchorText("per-decade", 8, "cm/yr")).toBe("80 cm per decade");
  });
});
