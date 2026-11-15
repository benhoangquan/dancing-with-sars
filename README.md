# Dancing with the SARs

An interactive scrollytelling site for the 2026 NASA Space Apps Challenge. It turns NASA-ISRO NISAR L-band radar surface-change data into three short stories, each ending in a way to act.

| Chapter | Place | What the radar shows |
|---|---|---|
| Forest | Rondônia, Brazil | Cross-polarized (HV) backscatter drops where logging roads and clearings remove canopy |
| Fire | Okanagan, British Columbia | The August 2026 burn scars, seen through smoke, with canopy loss on steep terrain |
| Ground | San Joaquin Valley, California | Centimeter-scale land subsidence from repeat-pass interferometry |

Each chapter pairs a terrain flyover with a before/after radar swipe map, a plain-English legend, a small time-series readout and an action drawer with vetted conservation organizations.

## Layout

| Path | Contents |
|---|---|
| `schema/` | `chapter.schema.json`, the canonical data contract, and shared golden test vectors |
| `pipeline/` | Python (`uv`) offline processing: NISAR search and clipping, Cloud-Optimized GeoTIFF writing, manifests, flyover rendering |
| `web/` | Next.js static site: MapLibre GL JS, deck.gl, Tailwind CSS |
| `docs/` | Data contract notes, decision log, demo script |

## Data status

Each layer in a chapter has one of three statuses, shown in the site legend:

- `real`: NISAR data processed by this pipeline.
- `fallback`: another real mission (Sentinel-1 via OPERA products), labeled as such.
- `illustrative`: synthetic data that shows the intended pattern, labeled as such.

See [DATA_SOURCES.md](DATA_SOURCES.md) for products, collections and licenses.

## Run

```bash
cd pipeline && uv sync && uv run sar fixture --all && uv run sar validate
cd ../web && npm ci && npm run build
npx serve out
```

See [CLAUDE.md](CLAUDE.md) for the full command list.
