# AGENTS.md

## Repository Workflow

- This repository is Git-managed. Use Git commands for status and diffs; do not use Perforce commands here unless the user explicitly asks for a Perforce operation.
- Keep IDE/editor metadata out of version control. `.idea/` and `.cursor/` are intentionally ignored.
- Keep changes scoped to the user's request. Do not do broad cleanup or unrelated refactors while touching nearby files.
- Prefer existing project utilities, managers, and naming patterns over introducing new abstractions.

## Python Style

- Use straightforward, typed Python with clear function boundaries and explicit inputs/outputs.
- Prefer `pathlib` for new filesystem code unless the surrounding module already uses `os.path` or strings consistently.
- Use standard library functionality first, then existing project dependencies, before adding packages.
- Keep I/O, parsing, transformation, and reporting separated enough that core logic can be tested without files or network.
- Raise or handle specific exceptions at meaningful boundaries. Avoid broad `except` blocks unless they add context before re-raising or intentionally continue batch processing.
- Avoid hidden global state in utility code. Pass dependencies, paths, clients, and configuration explicitly unless an existing project singleton or runtime container is already the local pattern.
- Put explanatory comments above the code they describe. Keep comments sparse and focused on intent, edge cases, or compatibility constraints.
- Do not use module, class, or function docstrings as routine inline documentation. FastMCP tool descriptions belong in `@mcp.tool(description="...")`.
- Keep `def` signatures on one line when they fit within the project's current line length. When wrapping is needed, prefer balanced lines over one-argument-per-line wrapping.
- Use `Optional[T]` for nullable type annotations in files that already follow that style; avoid switching a file wholesale to `T | None` as an incidental change.
- For FastMCP-facing schemas, prefer plain `dict` where richer generic annotations have caused host schema parsing issues.
- Use `if value:` instead of `if value is not None:` only when falsey values do not have distinct meaning. Preserve explicit `is None` / `is not None` checks when `0`, `False`, `""`, or `[]` are valid values.
- Keep adjacent top-level functions separated by the spacing already used in the file. Do not reformat whole files just to normalize blank lines.

## WAAPI_Tools Architecture

- `libraries/waapi_client.py` is the low-level JSON/dict WAAPI client layer. Its inputs and outputs should remain dicts or primitive values.
- `libraries/utils/wwise/waapi_utils.py` is the Wwise object facade. It converts `WwiseObject` and `WwiseObjectType` to the dict/string values expected by `WAAPIClient`, then wraps dict results back into `WwiseObject`.
- Business code under `libraries/utils/wwise/*_utils.py`, `windows/`, `data/`, and table/UI flows should prefer `from libraries.utils.wwise import waapi_utils` and pass `WwiseObject` / `WwiseObjectType` values.
- Avoid calling `WAAPIClient` directly from business logic when an equivalent `waapi_utils` facade function exists.
- `waapi_mcp/` is allowed to call `WAAPIClient` directly for GUID/dict thin wrappers, or to call existing `libraries/utils/wwise/*_utils.py` functions when exposing higher-level operations.
- `libraries/` code is reused by other tools. Change it conservatively; if a change affects shared behavior, call out the impact and add focused verification.

## Wwise and Batch Operations

- For repeated or user-visible Wwise operations over many objects, use `libraries/multi_thread/batch_processor.py` or the existing batch helper pattern instead of running long WAAPI loops directly in UI handlers.
- Keep table/UI code and batch Wwise execution separated. UI code should gather inputs and wire callbacks; utility code should perform the operation.
- 批量处理细节规则见 `.agents/rules/batch-processing.md`：必须用 BatchProcessor 异步执行（带进度条），工作线程不碰 UI，结果在主线程回调里更新，禁止主界面卡死等待。
- When adding Wwise object operations, use project-provided constants, `WwiseObjectType`, generated IDs, and existing config helpers instead of duplicating string lookup logic.
- Preserve existing Wwise version checks through `libraries/utils/wwise/project_utils.py` when behavior differs across Wwise versions.

## UI 窗口开发

- 新增或修改 `windows/*_window.py` 时，界面布局必须先写在 `ui/<Name>.ui` 里，再用 pyuic 生成 `ui/<Name>_ui.py`（`pyside6-uic ui/<Name>.ui -o ui/<Name>_ui.py`），窗口类继承 `Ui_*` 并调用 `setupUi`；不要在窗口逻辑代码中手工添加控件/布局/菜单。调整已有窗口的布局同样只改 `.ui` 并重新生成，不要直接在逻辑代码里改 UI。
- 所有按钮 / action / 控件的信号绑定统一放在 `setup_triggers` 方法中（由 `__init__` 调用），不要在 `__init__` 或其它方法里散落绑定代码。
- 所有允许用户在界面设置的选项都必须持久化到 `user_config`，以窗口为节点（`window_settings.<window_key>`），开窗读取、关窗/变化时保存；详见 workflow 文件。
- 详细流程与约定见 `.agents/rules/ui-window-workflow.md`。
- `.ui` 控件 objectName 使用类型缩写前缀（`act`/`btn`/`cbb`/`cbx`/`lbl`/`rbn`/`ipt`/`pte`/`txe`/`spb`/`tbl`/`grp`/`mnu` 等，完整表见 workflow 文件），如 `btnSave`、`cbxTurboMode`。

## Logging

- Use `Logger()` from `libraries.utils.log_utils`.
- Use `Logger().info(...)` for user-visible operations, `Logger().debug(...)` for internal detail, and `Logger().error(...)` or existing exception logging for failures.

## Verification

- When tests exist for the touched area, run the focused tests. For broad Python changes, prefer `python -m pytest` if the environment has test dependencies installed.
- When no automated test fits, run the smallest import, syntax, or command-level check that validates the changed path, and report what was and was not verified.

## Codex Guidance Layout

- Durable repository instructions belong in this `AGENTS.md`; Codex reads it automatically at the start of each run or new session.
- Reusable task workflows belong under `.agents/skills/<skill-name>/SKILL.md`; Codex can invoke them explicitly or when the task matches the skill description.
- Additional repository rules live under `.agents/rules/*.md`（如 UI 窗口开发流程）；Codex 应在涉及相关代码时遵循其中约定。
- Do not use `.codex/rules/*.mdc` for coding style. Codex `rules/` files are command approval policy files, not Cursor-style code instruction files.
