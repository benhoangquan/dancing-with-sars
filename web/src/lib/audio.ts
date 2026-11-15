"use client";
// Spatial soundscape: two looped ambient recordings per place (before and after the change), crossfaded with
// chapter progress. Silent until the reader turns Sound on; the AudioContext is only created after that click.
import { useEffect, useRef } from "react";
import { assetUrl } from "./asset";
import { clock, useStory } from "./store";
import type { Chapter } from "@/types/chapter";

const MASTER = 0.6;
const RAMP_S = 0.25;

/** Equal-power crossfade: progress 0 is all "before", 1 is all "after". */
export function crossfade(progress: number): [number, number] {
  const p = Math.min(1, Math.max(0, progress));
  return [Math.cos((p * Math.PI) / 2), Math.sin((p * Math.PI) / 2)];
}

/** Progress through a chapter from the active beat and the progress inside it. */
export const chapterProgress = (beatIdx: number, p: number, beats: number) => Math.min(1, Math.max(0, (beatIdx + p) / Math.max(1, beats)));

interface Graph {
  ctx: AudioContext;
  before: GainNode;
  after: GainNode;
  sources: AudioBufferSourceNode[];
}

async function loop(ctx: AudioContext, url: string, gain: GainNode): Promise<AudioBufferSourceNode> {
  const data = await (await fetch(url)).arrayBuffer();
  const src = ctx.createBufferSource();
  src.buffer = await ctx.decodeAudioData(data);
  src.loop = true;
  src.connect(gain);
  src.start();
  return src;
}

/** Plays the chapter's soundscape while Sound is on; `gain` dims it (0.5 under a modal). */
export function useSoundscape(chapter: Chapter | null, gain: number) {
  const soundOn = useStory((s) => s.soundOn);
  const graph = useRef<Graph | null>(null);
  const gainRef = useRef(gain);
  useEffect(() => {
    gainRef.current = gain;
  }, [gain]);
  const sound = chapter?.soundscape;

  useEffect(() => {
    if (!soundOn || !sound || !chapter) return;
    let stopped = false;
    const ctx = new AudioContext();
    const before = ctx.createGain();
    const after = ctx.createGain();
    before.gain.value = after.gain.value = 0;
    before.connect(ctx.destination);
    after.connect(ctx.destination);
    const g: Graph = { ctx, before, after, sources: [] };
    graph.current = g;
    Promise.all([loop(ctx, assetUrl(sound.before.src), before), loop(ctx, assetUrl(sound.after.src), after)])
      .then((srcs) => {
        if (stopped) srcs.forEach((s) => s.stop());
        else g.sources = srcs;
      })
      .catch((e) => console.warn("soundscape failed to load", e));
    const apply = () => {
      const { beatIdx } = useStory.getState();
      const [a, b] = crossfade(chapterProgress(beatIdx, clock.getState().p, chapter.beats.length));
      const level = MASTER * gainRef.current;
      before.gain.setTargetAtTime(a * level, ctx.currentTime, RAMP_S);
      after.gain.setTargetAtTime(b * level, ctx.currentTime, RAMP_S);
    };
    apply();
    const timer = window.setInterval(apply, 200);
    return () => {
      stopped = true;
      window.clearInterval(timer);
      g.sources.forEach((s) => s.stop());
      void ctx.close();
      graph.current = null;
    };
  }, [soundOn, sound, chapter]);
}
