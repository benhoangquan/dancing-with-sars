/** Opening screen. The stage behind it shows the first chapter's first beat. */
export function Hero() {
  return (
    <section data-section="hero" data-chapter={0} data-beat={0} aria-labelledby="hero-title" className="flex min-h-svh items-end px-4 pb-24 lg:px-16">
      <div className="max-w-4xl">
        <p className="text-[13px] font-medium uppercase tracking-[0.1em] text-ink-dim">NASA Space Apps Challenge 2026</p>
        <h1 id="hero-title" className="display mt-4 text-[clamp(3rem,9vw,7.5rem)] font-semibold leading-[0.98] text-balance">
          Dancing with the SARs
        </h1>
        <p className="mt-6 max-w-2xl text-[21px] leading-snug text-ink-dim text-pretty">
          NISAR&rsquo;s L-band radar measures how the surface of the Earth changes, through cloud and smoke. Three places, three stories, and a way to act on each.
        </p>
        <p className="mt-10 flex items-center gap-3 text-[13px] text-ink-faint">
          <span aria-hidden className="inline-block h-9 w-px bg-white/30" />
          Scroll to begin
        </p>
      </div>
    </section>
  );
}
