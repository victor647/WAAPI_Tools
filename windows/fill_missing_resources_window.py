from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidgetItem

import globals.global_variables as gv
from libraries.multi_thread import batch_processor
from libraries.table_view.table_context_menu import (
    CellCapability,
    CellPayload,
    ColumnSpec,
    TableContextMenu,
)
from libraries.table_view.table_path_item import create_path_item
from data import user_config
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, localization_utils, waapi_utils
from libraries.wwise_object import WwiseObjectType
from ui.FillMissingResources_ui import Ui_FillMissingResources
from windows.base_analysis_dialog import BaseAnalysisDialog


WINDOW_SETTINGS_KEY = 'fill_missing_resources'
MODE_SILENCE = 'silence'
MODE_SINE = 'sine'

COL_NAME = 1
COL_PATH = 2
COL_MISSING = 3
COL_EXISTING = 4
LANGUAGE_COLUMN_MIN_WIDTH = 40
LANGUAGE_COLUMN_PADDING = 8


def group_audio_sources_by_parent(sounds: list) -> tuple[dict, dict]:
    children = waapi_utils.get_children_of_objects(sounds, return_fields=['parent'])
    sources_by_parent = {}
    for child in children:
        if child.type != WwiseObjectType.AudioSource:
            continue
        parent = (child.wwise_dict or {}).get('parent') or {}
        parent_id = parent.get('id') if isinstance(parent, dict) else ''
        if parent_id:
            sources_by_parent.setdefault(parent_id, []).append(child)
    all_sources = [source for sources in sources_by_parent.values() for source in sources]
    languages_by_source = (
        localization_utils.get_sound_languages(all_sources) if all_sources else {}
    )
    return sources_by_parent, languages_by_source


# 分析并批量填补 Sound 缺失的语言资源：窗口内选择静音或正弦波
class FillMissingResourcesWindow(BaseAnalysisDialog, Ui_FillMissingResources):

    analysis_tool_name = '填补缺失资源'

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.__rows = []
        self.__results = []
        self.__project_languages = []
        self.__processed_counts = []
        self.__loading_settings = False
        self.__saved_selected_languages = None
        self.__updating_languages = False
        self.analysis_table = self.setup_analysis_table(
            self.tblMissing, ['Sound 名称', 'Sound 路径', '缺失语言', '已有语言']
        )
        self.__configure_table()
        self.__context_menu = TableContextMenu(
            self.tblMissing, self.build_context_columns(), self.context_payload, parent=self
        )
        self.__context_menu.install()
        self.load_settings()
        self.__populate_initial_languages()
        self.setup_triggers()
        self.cbxSelectAll.setChecked(True)
        self.__update_frequency_enabled()

    def setup_triggers(self):
        self.btnAnalyze.clicked.connect(self.analyze)
        self.btnProcess.clicked.connect(self.process_selected)
        self.cbxSelectAll.toggled.connect(self.analysis_table.select_all)
        self.cbbFillMode.currentIndexChanged.connect(self.on_mode_changed)
        self.spbFillDuration.valueChanged.connect(self.save_settings)
        self.spbSineFrequency.valueChanged.connect(self.save_settings)
        self.tblLanguages.itemChanged.connect(self.on_language_item_changed)
        self.tblMissing.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    def __configure_table(self):
        header = self.tblMissing.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tblMissing.setColumnWidth(0, 36)
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Interactive)
        self.tblMissing.setColumnWidth(COL_NAME, 240)
        header.setSectionResizeMode(COL_PATH, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_MISSING, QHeaderView.ResizeMode.Fixed)
        self.tblMissing.setColumnWidth(COL_MISSING, 200)
        header.setSectionResizeMode(COL_EXISTING, QHeaderView.ResizeMode.Fixed)
        self.tblMissing.setColumnWidth(COL_EXISTING, 180)
        self.tblMissing.setSortingEnabled(False)

    def build_context_columns(self) -> dict[int, ColumnSpec]:
        return {
            COL_NAME: ColumnSpec(
                CellCapability.TEXT | CellCapability.WWISE_OBJECT,
                default_action='select',
            ),
            COL_PATH: ColumnSpec(
                CellCapability.TEXT | CellCapability.WWISE_OBJECT | CellCapability.WWISE_OBJECT_PATH,
                default_action='select',
            ),
            COL_MISSING: ColumnSpec(CellCapability.TEXT),
            COL_EXISTING: ColumnSpec(CellCapability.TEXT),
        }

    def context_payload(self, row: int, column: int) -> CellPayload:
        data = self.row_data_at(row)
        item = self.tblMissing.item(row, column)
        text = item.text() if item is not None else ''
        if data is None:
            return CellPayload(text=text)
        sound = data['sound']
        return CellPayload(
            text=text,
            wwise_object=sound,
            wwise_objects=[sound],
            wwise_path=sound.path if column == COL_PATH else '',
        )

    def row_data_at(self, row: int):
        item = self.tblMissing.item(row, 0)
        key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if not key:
            return None
        return next((data for data in self.__rows if data['sound'].id == key), None)

    def current_mode(self) -> str:
        return MODE_SINE if self.cbbFillMode.currentIndex() == 1 else MODE_SILENCE

    def load_settings(self):
        self.__loading_settings = True
        settings = user_config.get_window_settings(WINDOW_SETTINGS_KEY)
        self.cbbFillMode.setCurrentIndex(1 if settings.get('mode') == MODE_SINE else 0)
        try:
            duration = float(settings.get('duration', 2.0))
        except (TypeError, ValueError):
            duration = 2.0
        try:
            frequency = int(settings.get('frequency', 1000))
        except (TypeError, ValueError):
            frequency = 1000
        saved_languages = settings.get('languages')
        self.__saved_selected_languages = (
            [str(language) for language in saved_languages]
            if isinstance(saved_languages, list) else None
        )
        self.spbFillDuration.setValue(duration)
        self.spbSineFrequency.setValue(frequency)
        self.__loading_settings = False

    def save_settings(self, *_args):
        if self.__loading_settings:
            return
        languages = (
            self.selected_languages()
            if self.tblLanguages.columnCount()
            else self.__saved_selected_languages
        )
        user_config.set_window_settings(WINDOW_SETTINGS_KEY, {
            'mode': self.current_mode(),
            'duration': self.spbFillDuration.value(),
            'frequency': self.spbSineFrequency.value(),
            'languages': languages,
        })

    def __populate_initial_languages(self):
        try:
            languages = localization_utils.get_all_language_names()
        except Exception:
            languages = []
        if languages:
            self.__populate_language_table(languages)

    def __populate_language_table(self, languages: list[str], selected=None):
        if selected is None:
            if self.tblLanguages.columnCount() > 0:
                selected = set(self.selected_languages())
            elif self.__saved_selected_languages is not None:
                selected = set(self.__saved_selected_languages)
            else:
                selected = set(languages)
        selected &= set(languages)
        self.__updating_languages = True
        self.tblLanguages.clear()
        self.tblLanguages.setColumnCount(len(languages))
        self.tblLanguages.setRowCount(1 if languages else 0)
        self.tblLanguages.setHorizontalHeaderLabels(languages)
        for column, language in enumerate(languages):
            item = QTableWidgetItem()
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if language in selected else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, language)
            self.tblLanguages.setItem(0, column, item)
        if languages:
            header = self.tblLanguages.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            self.tblLanguages.resizeColumnsToContents()
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            total_width = 6
            for column in range(len(languages)):
                width = max(
                    self.tblLanguages.columnWidth(column) + LANGUAGE_COLUMN_PADDING,
                    LANGUAGE_COLUMN_MIN_WIDTH,
                )
                self.tblLanguages.setColumnWidth(column, width)
                total_width += width
            self.tblLanguages.setFixedWidth(total_width)
            self.tblLanguages.setRowHeight(0, 26)
        else:
            self.tblLanguages.setFixedWidth(0)
        self.__updating_languages = False
        self.__saved_selected_languages = [
            language for language in languages if language in selected
        ]
        self.save_settings()

    def selected_languages(self) -> list[str]:
        languages = []
        for column in range(self.tblLanguages.columnCount()):
            item = self.tblLanguages.item(0, column)
            if item is None or item.checkState() != Qt.CheckState.Checked:
                continue
            language = item.data(Qt.ItemDataRole.UserRole) or item.text()
            if language:
                languages.append(language)
        return languages

    def on_language_item_changed(self, _item):
        if self.__updating_languages:
            return
        self.__saved_selected_languages = self.selected_languages()
        self.save_settings()

    def on_mode_changed(self, _index: int):
        self.__update_frequency_enabled()
        self.save_settings()

    def __update_frequency_enabled(self):
        self.spbSineFrequency.setEnabled(self.current_mode() == MODE_SINE)

    def analyze(self):
        if batch_processor.is_busy():
            Logger().warning('已有任务正在运行，请稍后再分析')
            return
        window = gv.main_window
        if window is None:
            sounds = list(gv.active_objects)
        else:
            sounds = window.collect_tool_targets(
                WwiseObjectType.Sound, ignore_language_filter=True
            )
        if not sounds:
            message = '主窗口中没有可用于「填补缺失资源」的 Sound'
            Logger().warning(message)
            QMessageBox.warning(self, self.analysis_tool_name, message)
            return
        languages = localization_utils.get_all_language_names()
        if not languages:
            Logger().warning('工程没有可用语言，无法分析缺失资源')
            return
        self.__project_languages = languages
        self.__populate_language_table(languages)
        self.__results = [None] * len(sounds)
        self.__rows = []
        self.tblMissing.setRowCount(0)
        items = list(enumerate(sounds))
        batch_size = user_config.get_tool_page_size()
        batches = [
            items[index:index + batch_size]
            for index in range(0, len(items), batch_size)
        ]
        started = batch_processor.create_async(
            batches, self.analyze_sound_batch, '分析缺失语言',
            on_finished=self.on_analysis_finished,
            progress_text_func=lambda index, batch: (
                f'第 {index + 1}/{len(batches)} 批（{len(batch)} 个对象）'
            ),
        )
        if not started:
            Logger().warning('无法启动缺失语言分析任务')

    def analyze_sound_batch(self, _index: int, batch: list[tuple[int, object]]):
        sounds = [sound for _, sound in batch]
        try:
            sources_by_parent, languages_by_source = group_audio_sources_by_parent(sounds)
            for global_index, sound in batch:
                sources = sources_by_parent.get(sound.id, [])
                languages_by_id = {
                    source.id: languages_by_source.get(
                        source.id, localization_utils.SFX_LANGUAGE_NAME
                    )
                    for source in sources
                }
                # 只看 Sound 级语言非 SFX 的对象；纯音效/无源对象不参与缺失语言分析
                first_language = next(
                    iter(languages_by_id.values()), localization_utils.SFX_LANGUAGE_NAME
                )
                if first_language == localization_utils.SFX_LANGUAGE_NAME:
                    self.__results[global_index] = None
                    continue
                all_existing = {language for language in languages_by_id.values() if language}
                project_existing = [
                    language for language in self.__project_languages if language in all_existing
                ]
                other_existing = sorted(all_existing - set(self.__project_languages))
                missing = [
                    language for language in self.__project_languages
                    if language not in all_existing
                ]
                self.__results[global_index] = {
                    'sound': sound,
                    'existing': project_existing + other_existing,
                    'missing': missing,
                }
        except Exception:
            Logger().exception('批量分析缺失语言失败')
            for global_index, _ in batch:
                self.__results[global_index] = None
        return True

    def on_analysis_finished(self):
        self.__rows = [result for result in self.__results if result and result['missing']]
        self.analysis_table.ensure_rows(
            len(self.__rows), checked=self.cbxSelectAll.isChecked()
        )
        for row, data in enumerate(self.__rows):
            check_item = self.tblMissing.item(row, 0)
            if check_item is not None:
                check_item.setData(Qt.ItemDataRole.UserRole, data['sound'].id)
            name_item = QTableWidgetItem(data['sound'].name)
            name_item.setToolTip(data['sound'].path)
            path_item = create_path_item(data['sound'].path)
            missing_text = '、'.join(data['missing'])
            existing_text = '、'.join(data['existing']) or '无'
            missing_item = QTableWidgetItem(missing_text)
            missing_item.setToolTip(missing_text)
            existing_item = QTableWidgetItem(existing_text)
            existing_item.setToolTip(existing_text)
            self.tblMissing.setItem(row, COL_NAME, name_item)
            self.tblMissing.setItem(row, COL_PATH, path_item)
            self.tblMissing.setItem(row, COL_MISSING, missing_item)
            self.tblMissing.setItem(row, COL_EXISTING, existing_item)
        self.__context_menu.set_columns(self.build_context_columns())
        analyzed = sum(1 for result in self.__results if result is not None)
        found = len(self.__rows)
        if analyzed == 0:
            summary = '分析完成：没有找到 Sound 级语言非 SFX 的对象。'
        elif found:
            summary = (
                f'分析完成：共分析 {analyzed} 个本地化 Sound，'
                f'发现 {found} 个存在缺失语言。\n'
                '请在表格中勾选后点击「处理选中」。'
            )
        else:
            summary = f'分析完成：共分析 {analyzed} 个本地化 Sound，没有发现缺失语言。'
        self.show_analysis_result(summary)

    def process_selected(self):
        if batch_processor.is_busy():
            Logger().warning('已有任务正在运行，请稍后再处理')
            return
        if not self.__rows:
            Logger().warning('请先分析缺失语言')
            return
        selected_rows = self.analysis_table.selected_rows(visible_only=True)
        if not selected_rows:
            self.warn_no_selected_rows()
            return
        sounds = []
        for row in selected_rows:
            data = self.row_data_at(row)
            if data is not None:
                sounds.append(data['sound'])
        if not sounds:
            return
        mode = self.current_mode()
        duration = self.spbFillDuration.value()
        frequency = self.spbSineFrequency.value()
        languages = self.selected_languages()
        if not languages:
            message = '请至少勾选一个要填补的语言。'
            Logger().warning(message)
            QMessageBox.warning(self, self.analysis_tool_name, message)
            return
        batch_size = user_config.get_tool_page_size()
        batches = [
            sounds[index:index + batch_size]
            for index in range(0, len(sounds), batch_size)
        ]
        self.__processed_counts = [0] * len(batches)
        started = batch_processor.create_async(
            batches,
            lambda index, batch: self.process_sound_batch(
                index, batch, mode, duration, frequency, languages
            ),
            '填补缺失资源',
            on_finished=self.on_process_finished,
            progress_text_func=lambda index, batch: (
                f'第 {index + 1}/{len(batches)} 批（{len(batch)} 个对象）'
            ),
            undo_group='填补缺失资源',
        )
        if not started:
            Logger().warning('无法启动填补缺失资源任务')

    def process_sound_batch(self, index: int, sounds: list, mode: str, duration: float,
                            frequency: int, languages: list[str]):
        try:
            sources_by_parent, languages_by_source = group_audio_sources_by_parent(sounds)
            assignments = []
            for sound in sounds:
                sources = sources_by_parent.get(sound.id, [])
                existing = {
                    languages_by_source.get(
                        source.id, localization_utils.SFX_LANGUAGE_NAME
                    )
                    for source in sources
                }
                if not any(
                    language != localization_utils.SFX_LANGUAGE_NAME for language in existing
                ):
                    continue
                missing = [language for language in languages if language not in existing]
                if missing:
                    assignments.append((sound, missing))
            if not assignments:
                return True
            # 语言 SourcePlugin 只能挂在 Voice 上；这些对象已有非 SFX 源，统一补齐 IsVoice
            if not waapi_utils.set_objects_property_values(
                [(sound, True) for sound, _ in assignments], 'IsVoice'
            ):
                Logger().warning('批量设置 IsVoice=True 失败，继续尝试添加语言源')
            if mode == MODE_SINE:
                ok = audio_source_utils.add_sine_batch(assignments, duration, frequency)
            else:
                ok = audio_source_utils.add_silence_batch(assignments, duration)
            if ok:
                self.__processed_counts[index] = sum(
                    len(missing) for _, missing in assignments
                )
        except Exception:
            Logger().exception('批量填补缺失资源失败')
        return True

    def on_process_finished(self):
        Logger().info(
            f'填补完成：共新增 {sum(self.__processed_counts)} 个占位源；'
            '如需刷新结果，请重新点击「分析」'
        )
