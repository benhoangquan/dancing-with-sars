# Dancing with the SARs

An interactive scrollytelling site for the 2026 NASA Space Apps Challenge. It turns NASA-ISRO NISAR L-band radar data into four short stories, each ending in a way to act.

The reader starts on a white canvas with the Earth (NASA Blue Marble), scrolls into orbit, and picks a red pin on the hotspot globe. Each place has three acts: a 20-second terrain flyover, a radar stage with a before/after swipe, landmarks, roads and buildings, and an action sheet with vetted organizations and a "your city scale" comparison. Grey pins mark places NISAR data was checked for but gave no change we could defend.

| Chapter | Place | What the radar shows | Status |
|---|---|---|---|
| Forest | Rondônia, Brazil | HV backscatter falls where new clearings open (374 ha, 6.0 dB) | measured with NISAR |
| Water | Demak, Indonesia | Water dark, walls bright: villages standing in tidal water | NISAR imagery; subsidence and land-loss figures cited from Deltares (2021) |
| Fire | Okanagan, British Columbia | Inside the Quilpituk Creek fire perimeter, HV fell 0.8 dB relative to the forest around it | measured with NISAR, perimeter from BC Wildfire Service |
| Fire | Crosswhite fire, Oregon | Inside the 143,690 ha perimeter, HV fell 1.0 dB relative to the land around it; 850 mapped buildings within 2 km | measured with NISAR, perimeter from NIFC WFIGS |

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
- `fallback`: other real data, labeled as such (a mapped fire perimeter, or a square of a cited area).
- `illustrative`: synthetic data that shows the intended pattern, labeled as such.

See [DATA_SOURCES.md](DATA_SOURCES.md) for products, collections and licenses.

## Run

```bash
cd pipeline && uv sync && uv run sar validate
cd ../web && npm ci && npm run build
npx serve out          # then open http://localhost:3000, or http://localhost:3000/#place=demak
```

The data under `web/public/` is committed, so the site builds without credentials. Rebuilding it needs an Earthdata Login (see CLAUDE.md).

See [CLAUDE.md](CLAUDE.md) for the full command list.
