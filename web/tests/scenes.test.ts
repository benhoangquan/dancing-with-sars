import { describe, expect, it } from "vitest";
import { actOf, heroPose, initialScene, overlays, parsePlace, placeHash, shouldClosePopover } from "@/lib/scenes";

const slugs = ["rondonia", "demak", "okanagan"];

describe("route", () => {
  it("reads a known place from the hash", () => {
    expect(parsePlace("#place=demak", slugs)).toBe("demak");
    expect(parsePlace("#x=1&place=okanagan", slugs)).toBe("okanagan");
  });
  it("ignores unknown or malformed places", () => {
    expect(parsePlace("#place=atlantis", slugs)).toBeNull();
    expect(parsePlace("", slugs)).toBeNull();
    expect(parsePlace("#placed=demak", slugs)).toBeNull();
  });
  it("round-trips and picks the starting scene", () => {
    expect(parsePlace(placeHash("rondonia"), slugs)).toBe("rondonia");
    expect(placeHash(null)).toBe("");
    expect(initialScene("rondonia")).toBe("PLACE_CHAPTER");
    expect(initialScene(null)).toBe("HERO_GLOBE");
  });
});

describe("acts", () => {
  it("map five beats to I, II, II, II, III", () => expect([0, 1, 2, 3, 4].map((i) => actOf(i, 5))).toEqual([1, 2, 2, 2, 3]));
});

describe("hero", () => {
  it("lifts and fades the headline as the globe settles", () => {
    expect(heroPose(0)).toMatchObject({ headlineY: -0, headlineOpacity: 1, settled: false });
    const end = heroPose(1);
    expect(end.headlineY).toBeCloseTo(-28);
    expect(end.headlineOpacity).toBeCloseTo(0);
    expect(end.settled).toBe(true);
    expect(heroPose(2)).toEqual(end);
  });
});

describe("overlay matrix", () => {
  const base = { scene: "PLACE_CHAPTER", act: 2, dragging: false, popover: null, modal: null } as const;
  it("dims the beat card while dragging or reading a popover", () => {
    expect(overlays(base).cardOpacity).toBe(1);
    expect(overlays({ ...base, dragging: true }).cardOpacity).toBe(0.25);
    expect(overlays({ ...base, popover: "pin" }).cardOpacity).toBe(0.25);
  });
  it("shows the legend and landmarks in Act II only", () => {
    expect(overlays(base).legend).toBe(true);
    expect(overlays({ ...base, act: 1 }).legend).toBe(false);
    expect(overlays({ ...base, act: 3 }).landmarks).toBe(false);
    expect(overlays({ ...base, modal: "action" }).legend).toBe(false);
  });
  it("sets the globe button per scene", () => {
    expect(overlays({ ...base, scene: "HERO_GLOBE" }).backToGlobe).toBe("hidden");
    expect(overlays({ ...base, scene: "HOTSPOT_GLOBE" }).backToGlobe).toBe("disabled");
    expect(overlays(base).backToGlobe).toBe("enabled");
  });
  it("locks scroll on the hotspot globe and under a modal, and halves audio under a modal", () => {
    expect(overlays({ ...base, scene: "HOTSPOT_GLOBE" }).scrollLocked).toBe(true);
    expect(overlays({ ...base, modal: "discovery" })).toMatchObject({ scrollLocked: true, audioGain: 0.5 });
    expect(overlays(base)).toMatchObject({ scrollLocked: false, audioGain: 1 });
  });
  it("closes a popover after more than 40 px of scroll", () => {
    expect(shouldClosePopover(100, 140)).toBe(false);
    expect(shouldClosePopover(100, 141)).toBe(true);
    expect(shouldClosePopover(100, 59)).toBe(true);
  });
});
