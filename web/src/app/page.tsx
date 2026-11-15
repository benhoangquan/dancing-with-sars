import { loadChapters } from "@/lib/chapters";

// Milestone 1 placeholder: lists the chapters. Milestone 2 replaces it with the scrollytelling stage.
export default function Home() {
  const chapters = loadChapters();
  return (
    <main className="mx-auto max-w-3xl px-6 py-24">
      <h1 className="display text-5xl font-semibold">Dancing with the SARs</h1>
      <p className="mt-4 text-ink-dim">
        NISAR L-band radar shows surface change from space. Three chapters, each ending in a way to act.
      </p>
      <ol className="mt-16 space-y-10">
        {chapters.map((c) => (
          <li key={c.slug} className="glass p-8" style={{ borderColor: `${c.accent}55` }}>
            <p className="text-sm uppercase tracking-widest" style={{ color: c.accent }}>
              {c.kicker}
            </p>
            <h2 className="display mt-2 text-3xl font-semibold">{c.title}</h2>
            <p className="mt-3 text-ink-dim">{c.dek}</p>
          </li>
        ))}
      </ol>
    </main>
  );
}
