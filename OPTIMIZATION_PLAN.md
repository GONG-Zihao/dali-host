# LiFud DALI Host — Optimization Plan (for GPT‑5‑Codex)

This plan turns the current “usable prototype” into a robust, maintainable, and scalable DALI host. It is written for an automated coding agent to execute incrementally and safely.

Important: Do not modify the bilingual translation files under `i18n/` (keep `i18n/strings.zh.json`, `i18n/strings.en.json`, and `i18n/direct.map.json` intact). All new UI text should rely on existing translation helpers without changing existing dictionaries.

## Scope & Invariants

- Invariants
  - Do not change files: `i18n/strings.zh.json`, `i18n/strings.en.json`, `i18n/direct.map.json`.
  - Preserve existing public behaviors of panels unless explicitly refactored in this plan.
  - Avoid adding heavy, unused dependencies. Keep network actions optional and off by default.
- Environment assumptions
  - Python 3.10–3.12.
  - Network may be restricted. Avoid steps requiring package install or external calls during CI checks.
  - Filesystem is writable inside the workspace.

## Current Snapshot (Key Points)

- Strong: End‑to‑end “Control → Benchmark → Analysis → Scheduler → Config I/O”.
- Gaps vs. top‑tier: No real device scanning/reading; limited transports; repeated UI for address selection; no headless/automation endpoints; oversized dependency list; some demo/placeholder panels.
- Notable mismatch: Code imports `qdarktheme` (optional) while `requirements.txt` lists `qdarkstyle` only.

## Workstreams Overview

- WS1 Dependency Hygiene (shrink, align, split base/extras)
- WS2 UI Factorization (AddressTargetWidget; deduplicate address selectors)
- WS3 Device Readback + Inventory (MVP scan + groups/scenes query + UI)
- WS4 Transport Reliability (stubs for serial/HID; reconnect policy for TCP)
- WS5 Headless Mode & Scheduling (CLI runner; optional local API scaffold)
- WS6 Tests (frames/stats/schedule/DT8 conversions)
- WS7 Cleanup & Pruning (experimental panels; doc/README sync)

Each workstream is specified as actionable tasks with acceptance criteria and revert guidance.

---

## WS1 — Dependency Hygiene

Goal: Reduce footprint, align theme lib, and separate “base” vs. “extras”.

Task WS1‑A: Split requirements and align theme
- Changes
  - Add `requirements.base.txt` with only: `pyside6`, `numpy`, `matplotlib`, `pyyaml`, `pytest` (optional), `ruff` and `black` (dev only).
  - Add `requirements.extras.txt` with optional libs grouped by feature (comment each): `pyserial`, `hidapi`, `zeroconf`, `aiohttp`, `websockets`, `pandas`, `qdarktheme` (if keeping), etc.
  - Update `requirements.txt` to include only base (or keep as pointer with comments) and remove `qdarkstyle`. If using `qdarktheme`, add it to extras or base and keep code unchanged; else remove `qdarktheme` import in `app/extensions/boot.py` and rely on Fusion palette only.
- Files to edit
  - `requirements.txt`
  - Add: `requirements.base.txt`, `requirements.extras.txt`
  - `README.md` (installation section to mention base/extras)
- Acceptance
  - `pip install -r requirements.base.txt` succeeds in a fresh venv.
  - App runs with `python -m app.main --light --lang=zh` without missing theme libs.
- Revert
  - Restore original `requirements.txt` from VCS if theme mismatch causes issues.

Task WS1‑B: Comment unused heavy deps
- Action
  - In `requirements.extras.txt`, list unused heavy packages under commented sections with rationale (keep for future features), e.g., `pandas`, `scipy`, `sklearn`, `sqlalchemy`, `duckdb`, `fastapi`, `uvicorn`, `apscheduler`, `openpyxl`, `xlrd`.
- Acceptance
  - Lint and tests do not import any removed packages.

---

## WS2 — UI Factorization: AddressTargetWidget

Goal: Remove repeated address selection UI across panels and unify behavior.

Task WS2‑A: Implement `AddressTargetWidget`
- Create `app/gui/widgets/address_target.py`:
  - Public API
    - Properties: `mode()` -> `"broadcast"|"short"|"group"`, `addr_value()` -> `int|None`, `unaddressed()` -> `bool`.
    - Signals: `changed` (emitted on any field change).
    - Methods: `set_mode(mode, value=None, unaddr=False)`.
  - UI: radio buttons for broadcast/short/group; short(0–63) and group(0–15) spin boxes; “only unaddressed” checkbox.
  - No i18n dictionary changes; use `tr()` helpers for labels.
- Files to add/edit
  - Add `app/gui/widgets/address_target.py`.
- Acceptance
  - Self‑contained widget can be created in isolation; returns consistent values.

Task WS2‑B: Refactor panels to use AddressTargetWidget
- Panels to update
  - `app/gui/panels/panel_dimming.py`
  - `app/gui/panels/panel_rw.py`
  - `app/gui/panels/panel_groups.py`
  - `app/gui/panels/panel_scenes.py`
  - `app/gui/panels/panel_dt8_tc.py`
  - `app/gui/panels/panel_dt8_color.py`
  - `app/gui/panels/panel_sender.py`
- Actions
  - Replace each duplicated address block with a single `AddressTargetWidget` instance.
  - Replace private helpers like `_read_addr_mode()` with calls to the widget.
  - Ensure `BasePanel.register_send_widgets` still gates “send” actions only.
- Acceptance
  - All panels compile and run; address values unchanged in normal usage.
  - No regression in status messages or i18n display.

---

## WS3 — Device Readback & Inventory (MVP)

Goal: Provide a basic “readback → visualize → export” loop for groups/scenes and device presence.

Task WS3‑A: Extend config for query opcodes
- Edit `配置/dali.yaml` (do not change i18n files):
  - Under `ops`, add configurable defaults (commonly used in DALI gear):
    - `query_status: 144` (0x90)
    - `query_groups_0_7: 192` (0xC0)
    - `query_groups_8_15: 193` (0xC1)
    - `query_scene_level_base: 176` (0xB0)
- Acceptance
  - `get_app_config()` loads these keys with defaults if missing.

Task WS3‑B: Controller read APIs
- Edit `app/core/controller.py`:
  - Add methods
    - `query_status(short: int, timeout=0.3) -> bytes|None`
    - `query_groups(short: int, timeout=0.3) -> dict` returning `{0..15: 0/1}` by merging two bitmasks.
    - `query_scene_levels(short: int, timeout=0.3) -> dict` returning `{0..15: 0..254 or None}` via `query_scene_level_base + n`.
    - `scan_devices(range_=range(64)) -> list[int]` using `query_status` non‑None as presence.
- Constraints
  - Use existing `send_command()`; do not block the UI thread; these are synchronous calls invoked from UI via buttons.
- Acceptance
  - With `MockTransport`, return deterministic bytes (XOR behavior already in mock) and provide sensible fallbacks.

Task WS3‑C: Inventory panel
- Add `app/gui/panels/panel_inventory.py`:
  - UI: list/table of short addresses; columns for presence, groups bitmask, selected scenes’ levels; buttons: “Scan”, “Read Groups”, “Read Scenes”, “Export JSON…”.
  - Use `AddressTargetWidget` only if needed for broadcast actions (optional). For readback, iterate shorts.
  - Export format compatible with `app/core/io/state_io.py` structures (so it can feed Config I/O panel later).
- Integrate into main window
  - In `app/gui/main_window.py`, add a new tab “设备清单/Inventory”.
- Acceptance
  - “Scan” populates present devices (mock returns plausible results); export writes a JSON file to `数据/`.

---

## WS4 — Transport Reliability

Goal: Prepare for real deployments with pluggable transports and better TCP resilience.

Task WS4‑A: Serial/HID stubs
- Files to add
  - `app/core/transport/serial_port.py` (class `SerialGateway(Transport)` with NotImplemented for now)
  - `app/core/transport/hid_gateway.py` (class `HidGateway(Transport)` with NotImplemented)
- Edit `app/core/controller.py`
  - Recognize `gateway.type` values `serial` and `hid`; instantiate corresponding classes.
- Acceptance
  - App starts with `type=serial`/`hid` and shows a clear error on connect (NotImplemented), without crashing the UI.

Task WS4‑B: TCP reconnect policy (optional, minimal)
- Edit `app/core/transport/tcp_gateway.py`
  - Add simple reconnect on `BrokenPipeError` during `send()`; mark disconnected and propagate.
  - Optional heartbeat timer is deferred.
- Acceptance
  - No behavior change in mock; better logs for TCP failures.

---

## WS5 — Headless Mode & Scheduling

Goal: Allow automation without GUI.

Task WS5‑A: Headless runner
- Add `app/headless.py`:
  - CLI: `python -m app.headless --lang=zh --load-tasks 数据/schedule/tasks.json --run`.
  - Loads `ScheduleManager` with Controller and runs Qt event loop in headless mode (no QMainWindow); exits on SIGINT.
- Acceptance
  - Can run scheduler tasks without opening UI; respects “skip if not connected”.

Task WS5‑B: (Optional) Minimal local API stub
- Add `app/api/local.py` (optional): HTTP server stub behind a flag; deferred until network/extras are enabled.

---

## WS6 — Tests

Goal: Guard core logic with lightweight tests.

Task WS6‑A: Unit tests
- Add files under `tests/`:
  - `tests/test_frames.py` — `addr_short/group/broadcast`, `make_forward_frame`.
  - `tests/test_stats.py` — percentiles and ECDF.
  - `tests/test_schedule.py` — daily/weekly/interval next run computation.
  - `tests/test_dt8.py` — Tc K↔Mirek conversion boundaries.
- Acceptance
  - `pytest -q` passes with only base deps installed.

---

## WS7 — Cleanup & Pruning

Goal: Remove or isolate demos to avoid confusing users.

Task WS7‑A: Mark experimental panels
- Move the following to `app/experimental/` and remove from main UI tabs:
  - `app/panels/panel_addr_alloc.py`
  - `app/panels/panel_timecontrol.py`
  - `app/panels/panel_gateway_scan.py` (keep accessible via Tools menu only if functionally connected later)
- Acceptance
  - MainWindow tabs focus on production panels; no import errors.

Task WS7‑B: Minor tidy
- Remove duplicate/unused methods (e.g., `_delete` vs `_del` in `panel_sender.py` → keep one and fix callers).
- Normalize directory access: keep Chinese `数据/` and `配置/`, but add alias helpers in `app/core/config.py` (optional) for `data/` and `config/` if present.

---

## Implementation Order (Phased)

1) WS1 Dependency Hygiene (unlock stable dev env)
2) WS2 AddressTargetWidget + panel refactors (reduce duplication)
3) WS3 Inventory readback + panel (user‑visible value)
4) WS4 Transport stubs/reliability (infrastructure readiness)
5) WS5 Headless runner (automation)
6) WS6 Tests (confidence)
7) WS7 Cleanup (polish)

Each phase should compile and run before proceeding. Commit after each task with clear messages.

---

## Agent Execution Checklist (Per Task)

For each task above, follow this template:

1) Read related files (limit 250 lines per view). Identify insertion points.
2) Apply patch:
   - Add new files with minimal, focused implementation.
   - Update existing files surgically; avoid unrelated changes.
   - Never edit i18n translation JSON files.
3) Run quick validations:
   - Imports resolve (no missing modules).
   - App starts (for UI tasks) or relevant unit tests pass (for logic tasks).
4) Document in commit message: `[WSx‑Y] <short summary>`.

---

## Validation Guide

- Smoke run (UI): `python -m app.main --light --lang=zh` → window shows tabs; send actions disabled until connected (mock ok).
- Inventory (after WS3): use Scan; export JSON to `数据/` and re‑import via Config I/O if desired.
- Headless (after WS5): `python -m app.headless --lang=zh --run` (ensure tasks saved in `数据/schedule/tasks.json`).
- Tests (after WS6): `pytest -q`.

---

## Notes & Risks

- DALI opcode variations: query commands (`0xB0..BF`, `0xC0..C1`, `0x90`) vary across gear types. Keep opcodes configurable under `配置/dali.yaml`. The controller must not hardcode values.
- Network‑restricted environments: avoid adding servers unless gated behind flags and extras.
- Theme libs: Prefer stable Fusion palette; treat third‑party themes as optional.

---

## Appendix — File Map (New/Modified)

- New
  - `app/gui/widgets/address_target.py`
  - `app/gui/panels/panel_inventory.py`
  - `app/core/transport/serial_port.py`
  - `app/core/transport/hid_gateway.py`
  - `app/headless.py`
  - `tests/test_frames.py`
  - `tests/test_stats.py`
  - `tests/test_schedule.py`
  - `tests/test_dt8.py`
  - `requirements.base.txt`, `requirements.extras.txt`
- Modified
  - `requirements.txt`, `README.md`
  - `配置/dali.yaml` (add query ops with defaults)
  - `app/core/config.py` (defaults for new ops)
  - `app/core/controller.py` (query methods + transport selection)
  - `app/gui/main_window.py` (add Inventory tab)
  - Panels listed in WS2‑B (replace address UI)
  - `app/core/transport/tcp_gateway.py` (optional reconnect logs)
- Moved (WS7‑A)
  - `app/panels/*.py` → `app/experimental/*.py` (selected demos)

This plan is intentionally granular to enable efficient, automated execution by a coding agent while minimizing risk and preserving existing functionality.

