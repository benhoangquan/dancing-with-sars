# Dancing with the SARs

Static scrollytelling site (`web/`, Next.js static export) and offline Python pipeline (`pipeline/`, package `sarstory`, CLI `sar`).
Data contract: `schema/chapter.schema.json` (canonical) and `docs/data_contract.md`. Plan of record: `docs/decisions.md`.

## Commands
- `cd pipeline && uv sync && uv run ruff check . && uv run pytest` runs Python checks and the repo rules.
- `cd pipeline && uv run sar fixture --all && uv run sar validate` writes and validates the illustrative chapter data.
- `cd pipeline && uv run sar discover --all` searches the public NISAR catalog (no login) and writes `pipeline/reports/`.
- `cd pipeline && uv run sar fetch <slug>` then `uv run sar build <slug>` (add `--reuse-optical` to skip the network) make real layers. Fetch needs an Earthdata Login in `~/.netrc`.
- `cd web && npm run verify` runs gen:types, type diff check, manifest validation, typecheck, lint, unit tests and the static build.
- `cd web && npm run build && npm run smoke -- --trace off` runs the Playwright smoke tests against `out/`. Run `npx playwright install chromium` once. Screenshots land in `web/e2e/__screens__/` (ignored): look at them after a visual change.
- Add `?debug` to the URL to expose the two maps as `window.__sar`.

## Contract rules
- `schema/chapter.schema.json` is the source. `web/src/types/chapter.ts` is generated: never edit it by hand.
- Interface freeze: additive schema changes only, each logged in `docs/decisions.md`.
- `generated` in a manifest is owned by `sar build` and `sar fixture`. Authored fields are everything else.
- Numbers in story text come from `{stat:key}` tokens or sourced metrics, never typed by hand.
- Every layer carries a provenance status: `real`, `fallback` or `illustrative`. The UI shows it.

## Repo rules (tested in `pipeline/tests/test_repo_rules.py`)
- No source file over 500 lines. CLAUDE.md stays at 40 lines or fewer.
- Each file in `web/public/data` is 25 MB or less and the folder totals 150 MB or less.
- No `.netrc`, `.env` or credentials in the repo. Earthdata login is done by the user in their own terminal.
- Docs and UI text state what a thing is and does. No quality adjectives.

## Git
- Commits: one line, lowercase, past tense, 60 characters or fewer, no prefix, no trailer.
- Commit locally at the end of each milestone. Never push, create the GitHub repo or deploy without asking the user.
