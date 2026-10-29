from windows.base_analysis_dialog import BaseAnalysisDialog
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QWidget

from libraries.multi_thread import batch_processor
from libraries.table_view.table_facade import TableFacade
from data import user_config
from libraries.utils.vcs import vcs_utils
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import (
    compression_utils, localization_utils, project_utils, soundbank_info_utils,
    soundbank_utils, waapi_utils,
)
from libraries.wwise_object import WwiseObject, WwiseObjectType
from ui.MediaSize_ui import Ui_MediaSize


HEADERS = ['名称', '类型', '流式源文件', '非流式源文件', '总源文件数',
           '原始wav', '平均压缩比', '合计wem', '内存wem', '流式wem']


# 把 KB 大小格式化为可读文本：不足 1MB 显示 KB，否则 MB/GB
def format_size(kilobytes: float) -> str:
    if kilobytes is None:
        return '-'
    bytes_value = kilobytes * 1024
    if bytes_value < 1024 * 1024:
        return f'{kilobytes:.2f} KB'
    if bytes_value < 1024 * 1024 * 1024:
        return f'{kilobytes / 1024:.2f} MB'
    return f'{kilobytes / (1024 * 1024):.2f} GB'


# 压缩比显示为 N:1（整数则省略小数，否则保留两位）
def format_ratio(numerator: float, denominator: float) -> str:
    if denominator <= 0:
        return '-'
    ratio = numerator / denominator
    if abs(ratio - round(ratio)) < 1e-9:
        return f'{round(ratio)}:1'
    return f'{ratio:.2f}:1'


# 媒体资源大小统计窗口：按对象逐项展示 wav/内存wem/流式wem 大小
# wem 只统计当前平台（可在窗口里切换平台并同步修改 Wwise 的当前平台）
class MediaSizeWindow(BaseAnalysisDialog, Ui_MediaSize):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.__objects: list[WwiseObject] = []
        # 每个根对象一个累加器；批处理按展开后的所有节点推进（进度条总数=节点数）
        self.__stats: list = []
        self.__nodes: list[WwiseObject] = []
        self.__node_root: list[int] = []
        self.__row_checked_by_path: dict = {}
        self.__source_properties_by_id: dict = None
        # 语言筛选（口径同主窗口「高级筛选 → 语言筛选」）：None 表示统计全部语言
        self.__only_language: str = None
        self.__current_platform: str = ''
        self.__soundbanks_info_path = ''
        self.__xml_index = None
        self.__xml_status_message = ''
        self.__xml_auto_selected = False
        self.__vcs_updated_xml = ''
        self.__language_filter_ready = False
        self.__table = TableFacade(
            self.tblMediaSize,
            headers=HEADERS,
            sorting_enabled=True,
            pinned_bottom_count=1,
        )
        self.setup_triggers()
        self.load_platforms()
        self.sync_language_filter_buttons()
        self.load_soundbanks_info_settings()
        self.lblSoundBanksInfoStatus.setText("请点击「分析」开始统计")
        self.__language_filter_ready = True

    # 绑定信号槽（控件来自 ui/MediaSize.ui）
    def setup_triggers(self):
        self.btnAnalyze.clicked.connect(self.__start_measuring)
        self.tblMediaSize.doubleClicked.connect(self.__on_table_double_clicked)
        self.cbbPlatform.currentIndexChanged.connect(self.on_platform_selected)
        self.btnChooseSoundBanksInfo.clicked.connect(self.choose_soundbanks_info)
        self.btnClearSoundBanksInfo.clicked.connect(self.clear_soundbanks_info)
        self.iptSoundBanksInfoPath.editingFinished.connect(self.on_soundbanks_info_edited)
        self.rbnLangAll.toggled.connect(self.on_language_filter_changed)
        self.rbnLangActive.toggled.connect(self.on_language_filter_changed)

    # 双击某行在 Wwise 中选中对应对象
    def __on_table_double_clicked(self, index):
        source_row = self.__table.get_source_row(index)
        if 0 <= source_row < len(self.__objects):
            waapi_utils.select_objects_in_wwise([self.__objects[source_row]])

    # 当前平台名（读工程信息里的 currentPlatformId）
    @staticmethod
    def get_current_platform_name() -> str:
        platform_id = waapi_utils.get_project_info('currentPlatformId')
        platform = waapi_utils.get_full_info_from_obj_id(platform_id) if platform_id else None
        return platform.name if platform else ''

    # 平台下拉：列出工程所有平台并选中当前平台
    def load_platforms(self):
        platforms = waapi_utils.get_project_info('platforms') or []
        names = [item.get('name') if isinstance(item, dict) else getattr(item, 'name', None)
                 for item in platforms]
        names = [name for name in names if name]
        self.__current_platform = self.get_current_platform_name()
        self.cbbPlatform.blockSignals(True)
        self.cbbPlatform.clear()
        self.cbbPlatform.addItems(names)
        index = self.cbbPlatform.findText(self.__current_platform)
        self.cbbPlatform.setCurrentIndex(index if index >= 0 else 0)
        self.cbbPlatform.blockSignals(False)

    # SoundBanksInfo.xml 设置：优先用户选择；否则按平台在 GeneratedSoundBanks 下自动查找
    def load_soundbanks_info_settings(self):
        settings = user_config.get_window_settings("media_size")
        saved_path = str(settings.get("soundbanks_info_path", "") or "")
        if saved_path and Path(saved_path).is_file():
            self.__soundbanks_info_path = saved_path
            self.__xml_auto_selected = False
        else:
            self.__soundbanks_info_path = self.discover_soundbanks_info()
            self.__xml_auto_selected = bool(self.__soundbanks_info_path)
        self.iptSoundBanksInfoPath.setText(self.__soundbanks_info_path)
        self.update_soundbanks_info_status()

    def save_soundbanks_info_settings(self):
        settings = dict(user_config.get_window_settings("media_size") or {})
        settings["soundbanks_info_path"] = self.__soundbanks_info_path
        user_config.set_window_settings("media_size", settings)

    def discover_soundbanks_info(self) -> str:
        project_dir = ""
        try:
            project_dir = project_utils.get_project_directory() or ""
        except Exception:
            Logger().debug("读取 Wwise 工程目录失败，跳过 SoundBanksInfo.xml 自动查找")
        platform = self.__current_platform
        candidates: list[Path] = []
        if project_dir:
            root = Path(project_dir)
            if platform:
                candidates.extend([
                    root / "GeneratedSoundBanks" / platform / "SoundbanksInfo.xml",
                    root / "GeneratedSoundBanks" / platform / "SoundBanksInfo.xml",
                ])
            candidates.extend([
                root / "SoundbanksInfo.xml",
                root / "SoundBanksInfo.xml",
            ])
        duplicate_settings = user_config.get_window_settings("media_duplicate")
        last_xml = str(duplicate_settings.get("last_file", "") or "")
        if last_xml:
            last_platform = soundbank_info_utils.read_soundbanks_info_platform(last_xml)
            if (not platform or not last_platform
                    or last_platform.casefold() == platform.casefold()):
                candidates.append(Path(last_xml))
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return ""

    def update_soundbanks_info_status(self, text: str = None):
        if text is not None:
            self.lblSoundBanksInfoStatus.setText(text)
        elif not self.__soundbanks_info_path:
            self.lblSoundBanksInfoStatus.setText("仅使用本地 wem")
        else:
            self.lblSoundBanksInfoStatus.setText("等待读取 XML")

    def choose_soundbanks_info(self):
        if batch_processor.is_busy():
            Logger().warning(batch_processor.busy_message('选择 SoundBanksInfo.xml'))
            return
        start_path = self.__soundbanks_info_path
        if start_path:
            start_dir = str(Path(start_path).parent)
        else:
            try:
                start_dir = project_utils.get_project_directory() or ""
            except Exception:
                start_dir = ""
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择 SoundBanksInfo.xml",
            start_dir,
            "SoundBanksInfo.xml (SoundbanksInfo.xml SoundBanksInfo.xml);;XML 文件 (*.xml);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self.__soundbanks_info_path = file_path
        self.__xml_auto_selected = False
        self.__vcs_updated_xml = ""
        self.iptSoundBanksInfoPath.setText(file_path)
        self.save_soundbanks_info_settings()
        self.update_soundbanks_info_status()
        self.mark_analysis_pending("SoundBanksInfo.xml 已更改，请点击「分析」刷新")

    def clear_soundbanks_info(self):
        if batch_processor.is_busy():
            Logger().warning(batch_processor.busy_message('清除 SoundBanksInfo.xml'))
            return
        self.__soundbanks_info_path = ""
        self.__xml_auto_selected = False
        self.__vcs_updated_xml = ""
        self.iptSoundBanksInfoPath.setText("")
        self.save_soundbanks_info_settings()
        self.update_soundbanks_info_status()
        self.mark_analysis_pending("SoundBanksInfo.xml 已清除，请点击「分析」刷新")

    def on_soundbanks_info_edited(self):
        if batch_processor.is_busy():
            Logger().warning(batch_processor.busy_message('修改 SoundBanksInfo.xml'))
            return
        file_path = self.iptSoundBanksInfoPath.text().strip()
        if file_path == self.__soundbanks_info_path:
            return
        self.__soundbanks_info_path = file_path
        self.__xml_auto_selected = False
        self.__vcs_updated_xml = ""
        self.save_soundbanks_info_settings()
        self.update_soundbanks_info_status()
        self.mark_analysis_pending("SoundBanksInfo.xml 已更改，请点击「分析」刷新")

    # 把下拉框选回指定平台（切换失败或正在跑批处理时回退显示）
    def select_platform_in_combo(self, platform_name: str):
        index = self.cbbPlatform.findText(platform_name)
        if index < 0:
            return
        self.cbbPlatform.blockSignals(True)
        self.cbbPlatform.setCurrentIndex(index)
        self.cbbPlatform.blockSignals(False)

    # 切换平台：同步修改 Wwise 的当前平台，然后按新平台重新统计
    def on_platform_selected(self, _index: int):
        platform_name = self.cbbPlatform.currentText()
        if not platform_name or platform_name == self.__current_platform:
            return
        if batch_processor.is_busy():
            Logger().warning(batch_processor.busy_message('切换平台'))
            self.select_platform_in_combo(self.__current_platform)
            return
        if not waapi_utils.switch_project_platform(platform_name):
            Logger().error(f'切换平台失败：{platform_name}')
            self.select_platform_in_combo(self.__current_platform)
            return
        self.__current_platform = platform_name
        if self.__xml_auto_selected:
            self.__soundbanks_info_path = self.discover_soundbanks_info()
            self.iptSoundBanksInfoPath.setText(self.__soundbanks_info_path)
            self.update_soundbanks_info_status()
        Logger().info(f'已切换 Wwise 当前平台为「{platform_name}」，请点击分析刷新统计')
        self.mark_analysis_pending("平台已切换，请点击「分析」刷新")

    # 与高级筛选窗口共用 advanced_filter.language_filter；两个窗口打开时都从同一配置恢复
    def sync_language_filter_buttons(self, active: bool = None):
        if active is None:
            active = user_config.get_advanced_filter_settings().get('language_filter') == 'active'
        widgets = (self.rbnLangAll, self.rbnLangActive)
        for widget in widgets:
            widget.blockSignals(True)
        self.rbnLangAll.setChecked(not active)
        self.rbnLangActive.setChecked(active)
        for widget in widgets:
            widget.blockSignals(False)

    def on_language_filter_changed(self, checked: bool):
        if not checked:
            return
        if batch_processor.is_busy():
            Logger().warning(batch_processor.busy_message('切换语言筛选'))
            self.sync_language_filter_buttons()
            return
        value = 'active' if self.rbnLangActive.isChecked() else 'all'
        user_config.save_advanced_filter_settings({'language_filter': value})
        self.mark_analysis_pending("语言筛选已更改，请点击「分析」刷新")

    # 高级筛选窗口可能已改过语言设置；激活本窗口时同步一次并刷新统计
    def changeEvent(self, event):
        if (event.type() == QEvent.Type.ActivationChange
                and self.isActiveWindow()
                and self.__language_filter_ready):
            self.sync_language_filter_from_config()
        super().changeEvent(event)

    def sync_language_filter_from_config(self):
        if batch_processor.is_busy():
            return
        active = user_config.get_advanced_filter_settings().get('language_filter') == 'active'
        if active == self.rbnLangActive.isChecked():
            return
        self.sync_language_filter_buttons(active)
        self.mark_analysis_pending("语言筛选已更改，请点击「分析」刷新")

    # 语言筛选口径与主窗口一致：高级筛选选「只显示当前语言」时只统计当前语言的源（SFX 始终保留）
    def resolve_language_filter(self):
        settings = user_config.get_advanced_filter_settings()
        active = settings.get('language_filter') == 'active'
        self.sync_language_filter_buttons(active)
        if not active:
            self.__only_language = None
            return
        active_language = localization_utils.get_current_language()
        self.__only_language = active_language or None

    # 参数变更后只提示，由用户点击「分析」手动刷新
    def mark_analysis_pending(self, message: str):
        self.lblSoundBanksInfoStatus.setText(message)
        self.btnAnalyze.setEnabled(True)

    # 为每个对象创建一行并异步统计
    def __start_measuring(self):
        if batch_processor.is_busy():
            message = batch_processor.busy_message('统计媒体资源大小')
            Logger().warning(message)
            self.lblSoundBanksInfoStatus.setText(message)
            return
        self.__soundbanks_info_path = self.iptSoundBanksInfoPath.text().strip()
        self.__xml_index = None
        self.__xml_status_message = ""
        if self.__soundbanks_info_path:
            self.update_soundbanks_info_status("正在读取 XML...")
        # 每次统计都取主窗口勾选对象，未勾选行的子树不参与
        checked_objects, self.__row_checked_by_path = self.analysis_scope()
        self.__objects = compression_utils.scan_roots(checked_objects)
        self.__stats = []
        self.__nodes = []
        self.__node_root = []
        self.__source_properties_by_id = None
        self.__table.clear()
        if not self.__objects:
            self.update_soundbanks_info_status()
            message = '主窗口没有勾选可用于「媒体资源大小统计」的对象'
            Logger().warning(message)
            self.lblSoundBanksInfoStatus.setText(message)
            return
        self.update_xml_from_vcs()
        self.resolve_language_filter()
        self.__stats = [soundbank_utils.MediaSizeNodeStatistics() for _ in self.__objects]
        for obj in self.__objects:
            self.__table.append_row_values([obj.name, obj.type.name, '', '', '', '', '', '', '', ''])
        self.__table.on_table_filled()
        seen_ids: set[str] = set()
        for root_index, obj in enumerate(self.__objects):
            for node in [obj] + waapi_utils.get_child_objects(obj, True):
                if not node.id or node.id in seen_ids:
                    continue
                if self.is_excluded_by_scope(node.path, self.__row_checked_by_path):
                    continue
                seen_ids.add(node.id)
                self.__nodes.append(node)
                self.__node_root.append(root_index)
        if not self.__nodes:
            self.update_soundbanks_info_status()
            self.lblSoundBanksInfoStatus.setText('没有可统计的节点')
            return
        self.btnAnalyze.setEnabled(False)
        started = batch_processor.create_async(
            self.__nodes,
            lambda index, obj: self.__measure_node(index, obj),
            '统计媒体资源大小',
            'name',
            on_finished=self.__on_measuring_finished,
            on_interrupted=self.__on_measuring_interrupted,
        )
        if not started:
            self.btnAnalyze.setEnabled(True)
            self.lblSoundBanksInfoStatus.setText(
                batch_processor.busy_message('统计媒体资源大小')
            )

    # 分析前从版本控制更新 SoundBanksInfo.xml；同一路径本次会话只尝试一次
    def update_xml_from_vcs(self):
        path = self.__soundbanks_info_path
        if not path or path == self.__vcs_updated_xml or not Path(path).is_file():
            return
        if not vcs_utils.is_available():
            Logger().info("版本控制不可用，跳过 SoundBanksInfo.xml 更新")
            return
        self.__vcs_updated_xml = path
        self.update_soundbanks_info_status("正在从版本控制更新 XML...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            updated, message = vcs_utils.update_path(path)
        except Exception as exc:
            updated, message = False, str(exc)
        finally:
            QApplication.restoreOverrideCursor()
        if updated:
            Logger().info(f"SoundBanksInfo.xml 版本控制更新完成：{path}")
        else:
            Logger().warning(
                f"SoundBanksInfo.xml 版本控制更新失败：{path} ({message or '未知原因'})"
            )
        self.update_soundbanks_info_status()

    def __prefetch_source_properties(self) -> dict:
        self.__xml_index = None
        self.__xml_status_message = ""
        if self.__soundbanks_info_path:
            project_dir = ""
            try:
                project_dir = project_utils.get_project_directory() or ""
            except Exception:
                Logger().debug("读取 Wwise 工程目录失败，SoundBanksInfo.xml 仅按 XML 相对路径解析")
            try:
                xml_index = soundbank_info_utils.SoundBankInfoSizeIndex(
                    self.__soundbanks_info_path,
                    project_root=project_dir,
                    platform=self.__current_platform,
                )
                if (xml_index.platform_name and self.__current_platform
                        and xml_index.platform_name.casefold() != self.__current_platform.casefold()):
                    self.__xml_status_message = (
                        f"XML 平台为 {xml_index.platform_name}，与当前平台不一致"
                    )
                    Logger().warning(self.__xml_status_message)
                else:
                    self.__xml_index = xml_index
                    self.__xml_status_message = (
                        f"XML 已加载：{xml_index.platform_name or self.__current_platform}"
                        f"（{xml_index.entry_count} 条媒体）"
                    )
            except Exception as exc:
                self.__xml_status_message = f"XML 加载失败：{exc}"
                Logger().error(self.__xml_status_message)

        sources = [
            node for node in self.__nodes
            if (node.wwise_dict or {}).get('type') == WwiseObjectType.AudioSource.value
        ]
        if not sources:
            return {}
        nodes_by_path = {node.path.rstrip("\\"): node for node in self.__nodes if node.path}
        parents_by_source_id = {}
        property_objects = {source.id: source for source in sources}
        for source in sources:
            parent_path, separator, _source_name = source.path.rpartition("\\")
            parent = nodes_by_path.get(parent_path) if separator else None
            if parent and parent.id != source.id:
                parents_by_source_id[source.id] = parent
                property_objects[parent.id] = parent
        properties_by_id = waapi_utils.get_objects_properties(
            list(property_objects.values()),
            # 语言属性一起取回，语言筛选时不必再逐个查
            ['originalFilePath', 'originalRelativeFilePath', 'originalWavFilePath',
             'convertedWemFilePath', 'IsStreamingEnabled',
             'audioSource:language'],
        )
        cached_properties = {}
        for source in sources:
            parent = parents_by_source_id.get(source.id)
            source_properties = properties_by_id.get(source.id)
            if parent is None or source_properties is None:
                continue
            cached_properties[source.id] = {
                **source_properties,
                soundbank_utils.PARENT_STREAMING_CACHE_KEY:
                    properties_by_id.get(parent.id, {}).get('IsStreamingEnabled', False),
            }
        return cached_properties

    # 工作线程内累加单个节点到所属根对象
    def __measure_node(self, index: int, obj: WwiseObject):
        if index == 0:
            self.__source_properties_by_id = self.__prefetch_source_properties()
        self.__stats[self.__node_root[index]].accumulate(
            obj, self.__source_properties_by_id, self.__only_language,
            xml_index=self.__xml_index)
        return True

    # 主线程写入结果并追加合计行
    def __on_measuring_finished(self):
        self.__table.clear()
        total_wav = 0.0
        total_mem = 0.0
        total_stream = 0.0
        total_stream_files = 0
        total_memory_files = 0
        total_files = 0
        for index, stats in enumerate(self.__stats):
            obj = self.__objects[index]
            result = stats.finish()
            wav_kb, mem_kb, stream_kb, used_files, stream_files, memory_files = result
            total_wav += wav_kb
            total_mem += mem_kb
            total_stream += stream_kb
            stream_count = len(stream_files)
            mem_count = len(memory_files)
            file_count = len(used_files)
            total_stream_files += stream_count
            total_memory_files += mem_count
            total_files += file_count
            total_wem_kb = mem_kb + stream_kb
            ratio_val = (wav_kb / total_wem_kb) if total_wem_kb > 0 else 0.0
            ratio_text = format_ratio(wav_kb, total_wem_kb)

            disp_values = [
                obj.name,
                obj.type.name,
                str(stream_count),
                str(mem_count),
                str(file_count),
                format_size(wav_kb),
                ratio_text,
                format_size(total_wem_kb),
                format_size(mem_kb),
                format_size(stream_kb),
            ]
            raw_values = [
                obj.name,
                obj.type.name,
                stream_count,
                mem_count,
                file_count,
                wav_kb,
                ratio_val,
                total_wem_kb,
                mem_kb,
                stream_kb,
            ]
            self.__table.append_row_values(disp_values, raw_values=raw_values)

        # 追加合计行（由 pinned_bottom_count=1 确保无论何种排序方式均置底）
        total_wem = total_mem + total_stream
        total_ratio_val = (total_wav / total_wem) if total_wem > 0 else 0.0
        total_ratio_text = format_ratio(total_wav, total_wem)
        total_disp = [
            '合计',
            '',
            str(total_stream_files),
            str(total_memory_files),
            str(total_files),
            format_size(total_wav),
            total_ratio_text,
            format_size(total_wem),
            format_size(total_mem),
            format_size(total_stream),
        ]
        total_raw = [
            '合计',
            '',
            total_stream_files,
            total_memory_files,
            total_files,
            total_wav,
            total_ratio_val,
            total_wem,
            total_mem,
            total_stream,
        ]
        self.__table.append_row_values(total_disp, raw_values=total_raw)
        self.__table.on_table_filled()
        if self.__xml_status_message:
            self.update_soundbanks_info_status(self.__xml_status_message)
        else:
            self.update_soundbanks_info_status()
        self.btnAnalyze.setEnabled(True)
        Logger().info(f'媒体资源统计完成，共 {len(self.__objects)} 个对象')

    def __on_measuring_interrupted(self):
        self.btnAnalyze.setEnabled(True)
        self.lblSoundBanksInfoStatus.setText('统计中断，请点击「分析」重试')
        Logger().warning('媒体资源大小统计中断')
