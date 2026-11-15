// Reports the HTTP status of every external URL in the chapter manifests (organizations, call-to-action
// links, metric sources, data sources). Exit code 1 if any URL fails. Network required.
import { readdirSync, readFileSync } from "node:fs";

const dir = new URL("../public/chapters/", import.meta.url);
const urls = new Map();
const add = (url, where) => urls.set(url, [...(urls.get(url) ?? []), where]);
for (const f of readdirSync(dir).filter((x) => x.endsWith(".json"))) {
  const c = JSON.parse(readFileSync(new URL(f, dir), "utf8"));
  for (const o of c.action.organizations) {
    add(o.url, `${c.slug}: ${o.name} site`);
    add(o.cta.url, `${c.slug}: ${o.name} call to action`);
  }
  for (const m of c.action.metrics) add(m.source.url, `${c.slug}: metric source`);
  for (const s of c.generated.sources) add(s.url, `${c.slug}: data source ${s.id}`);
}

const headers = { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) dancing-with-sars-link-check" };
async function status(url) {
  for (const method of ["HEAD", "GET"]) {
    try {
      const res = await fetch(url, { method, headers, redirect: "follow", signal: AbortSignal.timeout(25000) });
      if (res.status < 400 || method === "GET") return res.status;
    } catch (e) {
      if (method === "GET") return `error: ${e.cause?.code ?? e.message}`;
    }
  }
}

let bad = 0;
for (const [url, where] of urls) {
  const s = await status(url);
  const ok = typeof s === "number" && s < 400;
  if (!ok) bad++;
  console.log(`${ok ? "ok  " : "FAIL"}  ${s}  ${url}  (${where[0]}${where.length > 1 ? ` +${where.length - 1}` : ""})`);
}
console.log(`${urls.size - bad}/${urls.size} URLs reachable`);
process.exit(bad ? 1 : 0);
