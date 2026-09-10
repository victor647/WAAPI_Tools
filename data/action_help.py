# 菜单/工具栏 action 的使用说明：主窗口启动时写入 QAction.toolTip/statusTip。
# key 为 MainWindow.ui 中 action 的 objectName；说明面向“鼠标悬停时快速了解用途”，
# 涉及对象范围、前提条件与危险操作提示。对象范围若无特别说明，指“表格当前可见对象”。

ACTION_HELP = {
    # 文件
    "actReconnectWwise": "重新检测/连接 Wwise；未连接时请先在 Wwise 中打开工程并开启 WAAPI。",
    "actExportObjectList": "把表格当前对象导出为文件：单列导出 TXT，多列导出 CSV。",
    "actImportObjectList": "从 CSV 导入对象列表：文件需包含“路径”列，按路径在工程中解析后填入表格。",
    # 编辑
    "actUndo": "撤销上一步 Wwise 中的操作。",
    "actRedo": "重做被撤销的 Wwise 操作。",
    "actDeleteObjects": "删除表格当前对象（危险：删除后无法通过本工具恢复）。",
    # 通用-命名
    "actRenameToShort": "把对象名改成去掉父级重复前缀后的最简名称。",
    "actRenameToFull": "把对象名改成带父级链与缩写约定的完整命名。",
    "actRemovePrefix": "去掉对象名开头的“XXX_”前缀段。",
    "actRemoveSuffix": "去掉对象名末尾的“_XXX”后缀段。",
    "actUseAcronym": "把名称前缀替换为工程约定的类型缩写。",
    "actChangeToTitleCase": "把对象名改为首字母大写（Title Case）。",
    "actChangeToLowerCase": "把对象名改为全小写。",
    "actChangeToUpperCase": "把对象名改为全大写。",
    "actAutoSetColor": "按工程约定的分类颜色表给对象设置颜色；被 Event 播放或被 SoundBank 包含的对象会同时处理（含深色标记）。",
    "actAutoAddNotes": "按 Event / SoundBank 引用关系自动写备注（Played by Event [...]、Included by SoundBank [...]）；只新增/覆盖，不删除已有备注。",
    # 通用-创建父级/结构
    "actCreateActorMixer": "在对象上方插入一层 ActorMixer 父级并移入。",
    "actCreateBlendContainer": "在对象上方插入一层 Blend Container 父级并移入。",
    "actCreateRandomSequenceContainer": "在对象上方插入一层 Random/Sequence 容器父级并移入。",
    "actCreateSwitchContainer": "在对象上方插入一层 Switch Container 父级并移入。",
    "actCreateVirtualFolder": "在对象上方插入一层 Virtual Folder 父级并移入。",
    "actCreateWorkUnit": "在对象上方插入一层 Work Unit 父级并移入。",
    "actSplitUnderScore": "按名称第一个下划线拆成子文件夹并移入对象、去掉该前缀。",
    "actMoveToSelection": "把表格对象移动到 Wwise 当前选中对象之下。",
    "actCopyFromSelection": "把 Wwise 当前选中的对象复制到表格对象之下。",
    "actReplaceByTemplate": "打开“模板批量替换”窗口。",
    "actRenameByDataTable": "打开“读表批量重命名”窗口（按表格数据批量改对象）。",
    # 源文件
    "actApplyEditsToOriginal": "把 Source Editor 中的裁剪/淡变写回磁盘 wav（会直接改动源文件）。",
    "actResetSourceEdits": "重置对象的裁剪/淡变等 Source 编辑参数。",
    "actTrimAudioSilence": "打开“裁剪头尾静音”窗口，需要对应源文件存在。",
    "actAutoImport": "按 Originals 约定路径自动为对象导入 wav 文件。",
    "actRenameOriginalToWwise": "把磁盘 wav 文件名改成与 Wwise 对象一致（磁盘改名）。",
    "actTidyOriginalFolders": "自动归类整理 Originals 下的子文件夹并更新引用。",
    "actDeleteUnusedAKDFiles": "删除工程中无对应 wav 的 .akd 文件（全工程扫描，危险）。",
    # 本地化
    "actLocalizeLanguages": "为语音对象批量导入其它语言槽位的样本（按已有语言路径复制）。",
    "actFillSilenceForRefLanguage": "为参考语言缺失的语音补静音。",
    "actFillSilenceForAllLanguages": "为全部未导入语言补静音。",
    "actFilterByLanguage": "表格只保留当前编辑语言对应的语音对象。",
    # 混音
    "actDownMixFader": "把当前层的音量/音高/滤波器参数向下逐层传递并清零当前层。",
    "actVolumeToGain": "把音量值并入增益并清零音量（Bus 类对象无增益，不处理）。",
    "actEnableEffectRender": "开启表格对象的“效果器预渲染”。",
    "actDisableEffectRender": "关闭表格对象的“效果器预渲染”。",
    "actEnableEffectBypass": "开启表格对象的效果器旁通。",
    "actDisableEffectBypass": "关闭表格对象的效果器旁通。",
    # Container
    "actBreakContainer": "打散容器结构：子对象上移一层并删除容器（危险）。",
    "actAssignSwitchMappings": "按子对象名与 Switch 值自动分配 Switch 容器的映射。",
    "actRemoveSwitchMappings": "清空 Switch 容器当前的映射分配。",
    "actReplaceParent": "把对象上移一层并尽量修复 Switch 映射。",
    "actAssignToGenericPath": "为父 Switch 容器中未分配的子对象补上通用路径映射。",
    "actSplitTo1P3P": "按角色拆分为 SwitchContainer（生成 1P 与 3P 分支）。",
    "actSplitTo1P2P3P": "按角色拆分（生成 1P/2P/3P 三分支）。",
    "actSplitTo1P2P": "按角色拆分（生成 1P/2P 两分支）。",
    "actRenameRandomChildren": "重命名 Random/Sequence 容器下的子对象（编号规则）。",
    "actGroupAsRandom": "把同级对象自动归组为 Random/Sequence 容器。",
    # Event
    "actCreatePlayEvent": "为对象创建或更新引用它的 Play Event（实现“可播放”）。",
    "actRenameEventByTarget": "单目标事件按播放对象推导并重命名事件。",
    "actHasEventReference": "表格只保留被 Event 引用的对象。",
    "actHasNoEventReference": "表格只保留未被 Event 引用的对象。",
    "actExportAllEvents": "导出全部事件的播放列表（事件→目标对象清单）。",
    # SoundBank
    "actCreateSoundBank": "为每个表格对象创建/复用同名 SoundBank 并加入包含。",
    "actAddToSelectedBank": "把表格对象的媒体加入 Wwise 当前选中的 SoundBank。",
    "actBankAssignmentMatrix": "打开“Bank 分配矩阵”窗口批量规划 Bank 归属。",
    "actIncludeMediaOnly": "把 Bank 包含内容设为仅媒体。",
    "actIncludeEventsAndStructures": "把 Bank 包含内容设为事件与结构。",
    "actIncludeAll": "把 Bank 包含内容设为事件/结构/媒体全部。",
    "actClearInclusions": "清空 Bank 的全部包含项。",
    "actGenerateEventBankMap": "生成事件与 Bank 的对应关系表。",
    # 统计
    "actCalculateMediaSize": "打开“媒体资源大小”统计窗口：对表格当前对象逐个统计 wav/内存 wem/流式 wem、源文件数与压缩比，并显示合计。",
    "actPropertyQuery": "打开属性查询窗口：对表格当前可见对象批量读取指定属性（多个属性用分号分隔），结果以表格展示。",
    # GameSync
    "actCopyRtpcFromSelection": "把 Wwise 当前选中对象的 RTPC 复制（替换）到表格对象。",
    # 导入
    "actImportWorkUnit": "从其它 Wwise 工程导入 Work Unit（打开导入窗口）。",
    "actImportFMODEvent": "从 FMOD 工程导入 Event。",
    "actImportFMODPreset": "从 FMOD 工程导入 Preset。",
    # 其他
    "actHelpDoc": "打开帮助文档（链接在 user_config.json 的 Documentation 中维护）。",
    "actProjectValidation": "打开“工程规范检查”窗口：按规则批量校验工程/列表/选中对象，逐条列出问题并支持一键修复。",
}
