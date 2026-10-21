# Handover — freecad-mcp (2026-10-21)

## State

- **assfix run completed** (`docs/assess-reports/2026-10-21.md`). Score 39/100,
  2 HIGH open, 11 MEDIUM, 1 LOW. The pre-fix score saturated at 0 (the current
  checklist applies more rows than the 2026-09-01 run did).
- **MCPB** `dist/freecad-mcp-v0.6.0.mcpb` 163.4 KB, manifest validates, import
  isolation + AST + clean-unpack launch checks pass. Audit reports `clean`.
- **Demo chain verified live** against the running backend:
  cube 8000 mm3 / 684 B, car 102,976 mm3 / 8.1 MB / 4 wheels, depot
  create/list/download/rename/upload/delete all 200.
- **Guided Demo page** `/demo` added and browser-walked with Playwright
  (cube -> save -> car -> save -> rename -> delete). Screenshot in
  `cua-reports/guided-demo-2026-10-21.png` (gitignored).
- **Tool count truth: 59.** `glama.json` and `mcpb/manifest.json` now mirror the
  59 actual `@mcp.tool` names (the manifest previously listed 85, mostly REST
  route names that are not MCP tools).

## Last concrete actions (commits, oldest first)

`de4697fe` MCPB manifest `${PWD}` -> `${__dirname}`, stdio entry, fleet pack shim
`1f9c6ffb` NSIS client registration (canonical `mcp-clients.nsh`)
`2932f075` drop S110/S112 ignores, remove fabricated CFD results, add pyright
`0a02ff05` tests for the real forces parser + refusal path
`655c036e` same-origin API base with Tauri gate, dashboard hero + onboarding cue
`36698d87`/`d25d8828` README/glama/llms/just/.mcpbignore
`b81c3b96`/`8b68b426` docs stack + assessment + timestamp
`3d728265` `create_shape` writes a real STL; depot create verifies the copy; all
          59 tools document return shape/examples
`2bc5649c` Parts Studio cube demo uses the real response and download route
`fabde964` assessment updated (39/100)
`fc7ba65f` guided demo page (browser-walked)

## Next step

1. **Pyright pass** (the only code-quality HIGH left): 73 errors from optional
   imports (torch/PIL/FreeCAD/PySide), `ctx.sample()` result typing, `list.get`,
   `FastMCP._tool_manager`, and a `css_class` kwarg. Do not silence the gate by
   widening rules. `uv run pyright src/`.
2. **Rebuild the `freecad-expert` skill** (41 lines, sole domain skill):
   `SUGGESTED: skillbuild freecad-mcp`. Needs a repo-wide harvest; do not
   hand-patch it.
3. MEDIUM backlog: missing Inbox/Tools/Skills pages, sparse `data-testid` on 15
   pages, no `/api/llm/{providers,models,onboarding}`, no chat streaming, no
   `output_schema`, npm instead of bun lockfile, author-machine fallback paths,
   GPU detection not wired into the store.

## Deliberately not done

- No NSIS rebuild this session (only the MCPB bundle was repacked). If you build
  the installer, read `TAURI_PRODUCTION_PITFALLS.md` Phase 1 A-J first and expect
  to hold ~45-60 min.
- No browser walk of the other 17 pages; only `/demo` was exercised.
- No attempt to make `pyright` green by config exclusions.
- `docs/mcp-tools.md` was not regenerated. There is no working generator
  (`freecad_mcp.utils.llms_txt` does not exist); `llms-full.txt` is maintained
  manually.
