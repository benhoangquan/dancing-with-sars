// Prebuild check: every manifest in public/chapters validates, its assets match, size budgets hold.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { MAX_FILE_BYTES, MAX_TOTAL_BYTES, validateChapter } from "./lib/validate.mjs";

const publicDir = new URL("../public/", import.meta.url);
const chaptersDir = new URL("chapters/", publicDir);
const files = readdirSync(chaptersDir).filter((f) => f.endsWith(".json")).sort();
if (!files.length) {
  console.error("validate-chapters: no manifests in public/chapters");
  process.exit(1);
}

let failed = 0;
const orders = new Map();
for (const file of files) {
  const slug = file.replace(/\.json$/, "");
  const obj = JSON.parse(readFileSync(new URL(file, chaptersDir), "utf8"));
  const { errors, warnings } = validateChapter(obj, publicDir);
  if (obj.slug !== slug) errors.push(`slug '${obj.slug}' does not match the file name`);
  if (orders.has(obj.order)) errors.push(`order ${obj.order} is also used by ${orders.get(obj.order)}`);
  orders.set(obj.order, slug);
  for (const w of warnings) console.warn(`warn  ${slug}: ${w}`);
  if (errors.length) {
    failed += errors.length;
    console.error(`FAIL  ${slug}`);
    for (const e of errors) console.error(`      ${e}`);
  } else {
    const g = obj.generated;
    const kinds = [...new Set(g.layers.map((l) => l.status))].sort().join("/");
    console.log(`ok    ${slug}  ${g.layers.length} layers, ${g.series.length} series, status ${kinds}`);
  }
}

// Size budgets for everything served from public/data.
const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((d) =>
    d.isDirectory() ? walk(new URL(`${d.name}/`, dir)) : [{ name: d.name, size: statSync(new URL(d.name, dir)).size }],
  );
let total = 0;
try {
  for (const f of walk(new URL("data/", publicDir))) {
    total += f.size;
    if (f.size > MAX_FILE_BYTES) {
      failed++;
      console.error(`FAIL  data/${f.name} is ${(f.size / 1e6).toFixed(1)} MB, over the ${MAX_FILE_BYTES / 1e6} MB file budget`);
    }
  }
} catch {
  /* no data directory yet */
}
if (total > MAX_TOTAL_BYTES) {
  failed++;
  console.error(`FAIL  public/data totals ${(total / 1e6).toFixed(1)} MB, over the ${MAX_TOTAL_BYTES / 1e6} MB budget`);
}
console.log(`data  ${(total / 1e6).toFixed(1)} MB of ${MAX_TOTAL_BYTES / 1e6} MB budget`);
process.exit(failed ? 1 : 0);
