// Reads chapter manifests at build time (server components only). The site is a static export, so
// this runs once during `next build`.
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import type { Chapter } from "@/types/chapter";

const CHAPTERS_DIR = path.join(process.cwd(), "public", "chapters");

export function loadChapters(dir: string = CHAPTERS_DIR): Chapter[] {
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(readFileSync(path.join(dir, f), "utf8")) as Chapter)
    .sort((a, b) => a.order - b.order);
}
