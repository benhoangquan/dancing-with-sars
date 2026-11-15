# AI use

AI tools used in this repository, what they produced, and how the output was checked.

| Tool | Used for | Output in the repository | Check |
|---|---|---|---|
| Claude Code (Anthropic) | Code, tests, schema, documentation drafts, chapter copy drafts | `pipeline/`, `web/`, `schema/`, `docs/` | `uv run pytest`, `npm run verify`, `npm run smoke`; numbers in story text come from pipeline output, not from the model; a person reviews each commit |

No AI tool receives credentials. Earthdata Login is completed by the user in their own terminal.

Models inside the product: none. The site is static and runs no model.
