---
name: waapi-tools-conventions
description: >-
  索引：本仓库代码规范已迁移至 Cursor Rules（.cursor/rules/*.mdc）。
  编辑本仓库时 Agent 会由 Rules 注入约定；本 skill 仅作入口说明。
  Wwise API 任务映射仍见 .cursor/skills/wwise-waapi/SKILL.md
---

# WAAPI_Tools 规范入口

- **通用 Python 风格**（注释、`def` 折行、函数空行、紧凑度）：`.cursor/rules/python-style.mdc`（匹配 `**/*.py`）
- **本仓库架构**（`libraries`、Wwise/WAAPI 分层、批处理、Logger）：`.cursor/rules/waapi-tools-architecture.mdc`（始终应用）

规范正文以 **Rules 文件为准**；若对话与本 skill 冲突，以 Rules 与用户对当前任务的说明为准。
