import { StatusBadge } from "@/components/ui/StatusBadge";
import type { Chapter } from "@/types/chapter";

/** Closing section: how the data was made and what each layer is, so nothing on screen is unexplained. */
export function Outro({ chapters }: { chapters: Chapter[] }) {
  const last = chapters.length - 1;
  return (
    <section data-section="outro" data-chapter={last} data-beat={chapters[last].beats.length - 1} aria-labelledby="outro-title" className="flex min-h-svh items-center px-4 py-24 lg:px-16">
      <div className="glass-data pointer-events-auto w-full max-w-3xl p-8 lg:p-10">
        <h2 id="outro-title" className="display text-[32px] font-semibold leading-tight">How this was made</h2>
        <p className="mt-4 text-[17px] leading-snug text-ink-dim">
          NISAR is a NASA and ISRO radar satellite. Its L-band signal passes through cloud, smoke and canopy, so it measures structure and ground motion in any weather. A pipeline clips the data to each study area, writes Cloud-Optimized GeoTIFFs, and this site reads them directly in the browser. Every layer below shows how real it is.
        </p>
        <ul className="mt-8 space-y-6">
          {chapters.map((c) => (
            <li key={c.slug}>
              <h3 className="text-[15px] font-semibold" style={{ color: c.accent }}>{c.kicker}</h3>
              <ul className="mt-2 space-y-2">
                {c.generated.layers.map((l) => {
                  const src = c.generated.sources.find((s) => l.sourceIds.includes(s.id));
                  return (
                    <li key={l.id} className="tabular flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
                      <span className="font-medium">{l.label}</span>
                      <span className="text-ink-dim">
                        {src ? `${src.mission} · ${src.product}` : "Unknown source"} · {l.date}
                      </span>
                      <StatusBadge status={l.status} />
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
        <p className="mt-8 text-[12px] leading-snug text-ink-faint">
          NISAR data: NASA and ISRO, distributed by the ASF DAAC. Optical imagery: Harmonized Landsat Sentinel-2. Terrain: Mapzen and AWS Open Data. Illustrative layers are synthetic patterns that show what the radar would reveal; they are not measurements.
        </p>
      </div>
    </section>
  );
}
