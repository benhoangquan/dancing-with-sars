"use client";

import { useEffect, useRef } from "react";
import { heroPose } from "@/lib/scenes";
import { heroClock, useStory } from "@/lib/store";

/**
 * Scene 1. A white canvas with the headline over the globe. Three feathered backdrop-blur bands under a white
 * gradient soften the top of the globe (a CSS stack, so Safari and Chromium render it the same). Scrolling lifts
 * and fades the headline while the globe zooms into orbit; when it settles the page hands over to the hotspot
 * globe.
 */
export function HeroBlurHeader({ places }: { places: number }) {
  const title = useRef<HTMLDivElement>(null);
  const section = useRef<HTMLElement>(null);

  useEffect(() => {
    const onScroll = () => {
      const el = section.current;
      if (!el) return;
      const span = el.offsetHeight - window.innerHeight;
      const p = span > 0 ? window.scrollY / span : 1;
      heroClock.setState({ p: Math.min(1, Math.max(0, p)) });
      const pose = heroPose(p);
      if (title.current) {
        title.current.style.transform = `translateY(${pose.headlineY}px)`;
        title.current.style.opacity = String(pose.headlineOpacity);
      }
      if (pose.settled && useStory.getState().scene === "HERO_GLOBE") {
        useStory.getState().setScene("HOTSPOT_GLOBE");
        window.scrollTo(0, 0);
      }
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <section ref={section} data-story-root className="hero relative h-[240svh]" aria-labelledby="hero-title">
      <div className="hero-blur pointer-events-none fixed inset-x-0 top-0 z-10 h-[22svh]" aria-hidden="true">
        <span className="hero-blur-band hero-blur-24" />
        <span className="hero-blur-band hero-blur-12" />
        <span className="hero-blur-band hero-blur-4" />
        <span className="hero-blur-wash" />
      </div>
      <div ref={title} className="pointer-events-none fixed inset-x-0 top-[9svh] z-20 px-6 text-center will-change-transform">
        <p className="text-[13px] font-semibold uppercase tracking-[0.12em] text-light-ink-dim">NASA Space Apps Challenge 2026</p>
        <h1 id="hero-title" className="display mx-auto mt-3 max-w-[14ch] text-[clamp(44px,8vw,96px)] font-semibold leading-[1.02] text-light-ink">
          Dancing with the SARs
        </h1>
        <p className="mx-auto mt-4 max-w-[38ch] text-[clamp(17px,2vw,21px)] leading-[1.4] text-light-ink-dim">
          NISAR’s L-band radar sees how the ground changes, through cloud and smoke. Scroll to orbit, then pick one of{" "}
          <span className="tabular">{places}</span> places.
        </p>
      </div>
      <p className="pointer-events-none fixed inset-x-0 bottom-8 z-20 text-center text-[13px] font-medium text-light-ink-dim">Scroll</p>
    </section>
  );
}
