# AI use

AI tools used in this repository, what they produced, and how the output was checked.

| Tool | Used for | Output in the repository | Check |
|---|---|---|---|
| Claude Code (Anthropic) | Code, tests, schema, documentation drafts, chapter copy drafts | `pipeline/`, `web/`, `schema/`, `docs/` | `uv run pytest`, `npm run verify`, `npm run smoke`; numbers in story text come from pipeline output, not from the model; a person reviews each commit |

No AI tool receives credentials. Earthdata Login is completed by the user in their own terminal.

Models inside the product: none. The site is static and runs no model.

2026-11-15 (v1 re-plan): the same tool wrote the globe, place and action components, the perimeter analysis, terrain, overlay, landmark, city and audio steps, and the story copy for Demak and Okanagan. Every figure in that copy is either a pipeline stat or a fact with a linked source; organization links and reference values were checked by HTTP and page reads on 2026-11-15.
