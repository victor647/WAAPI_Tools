# WAAPI 模块补充说明

## 底层 WAAPI 调用摘要

本文件是对 `libraries/wwise/WAAPI.py` 实现细节的速记，便于排查“实际调了哪条 waapi”。

| 区域 | 典型 `client.call` |
|------|---------------------|
| 连接 | `WaapiClient(url='ws://127.0.0.1:8080/waapi')` |
| 信息 | `ak.wwise.core.getInfo`, `getProjectInfo` |
| 对象读写 | `ak.wwise.core.object.get` / `set` / `create` / `move` / `copy` / `delete` / `setName` / `setProperty` / `setReference` / `setNotes` / `pasteProperties` |
| UI | `ak.wwise.ui.getSelectedObjects`, `ak.wwise.ui.commands.execute`, `ak.wwise.ui.bringToForeground` |
| Switch | `ak.wwise.core.switchContainer.getAssignments` / `addAssignment` / `removeAssignment` |
| 音频 | `ak.wwise.core.audio.import` |
| SoundBank | `ak.wwise.core.soundbank.getInclusions` / `setInclusions` |
| Transport | `ak.wwise.core.transport.create` / `executeAction` / `destroy` |
| 撤销 | `ak.wwise.core.undo.beginGroup` / `endGroup` |
| 源码管理 | `ak.wwise.core.sourceControl.add` |

## 返回值注意

- 多数查询在失败时返回空 `WwiseObject`、`[]` 或 `None`，并写日志。
- `get_object_from_path` 与部分路径 API 在成功分支可能返回原始 dict 列表元素，与 `find_object_by_path` 包装方式不完全一致；以当前源码为准。

## RETURN_FIELDS

默认对象查询返回字段：`id`, `name`, `type`, `path`（模块常量 `RETURN_FIELDS`）。
