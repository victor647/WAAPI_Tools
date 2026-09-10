import clipboard
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMenu, QTableWidgetItem

from libraries.multi_thread import batch_processor
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, waapi_utils
from libraries.wwise_object import WwiseObject
from table.wwise_table_context_menu import add_common_object_actions
from table.wwise_table_row_data import WwiseTableRowData
from ui.SyncTrim_ui import Ui_SyncTrim


# 查看并同步一批 AudioSource 的裁剪信息（TrimBegin/TrimEnd/Fade/Loop）
class SyncTrimWindow(QDialog, Ui_SyncTrim):

    def __init__(self, sources: list[WwiseObject]):
        super().__init__()
        self.setupUi(self)
        self.__sources = list(sources)
        self.setup_triggers()
        self.tblTrimInfo.setColumnCount(8)
        self.tblTrimInfo.setHorizontalHeaderLabels(
            ['源文件路径', 'AudioSource路径', 'TrimBegin', 'TrimEnd', 'FadeIn', 'FadeOut', 'LoopBegin', 'LoopEnd']
        )
        self.lblHint.setText(f'AudioSource 裁剪信息（共 {len(self.__sources)} 个）')
        self.refresh_sources()

    def setup_triggers(self):
        self.tblTrimInfo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblTrimInfo.customContextMenuRequested.connect(self.show_context_menu)
        self.tblTrimInfo.itemDoubleClicked.connect(self.show_object_in_wwise)

    # 重建表格并异步读取每个对象的源文件路径与裁剪信息
    def refresh_sources(self):
        self.tblTrimInfo.setRowCount(len(self.__sources))
        for index, source in enumerate(self.__sources):
            self.tblTrimInfo.setItem(index, 1, QTableWidgetItem(WwiseTableRowData.get_path_text(source.path)))
        batch_processor.create_async(
            self.__sources,
            lambda index, source: self.fill_source_info(index, source),
            '读取裁剪信息',
            on_finished=self.on_info_filled,
        )

    # 异步读取单个对象的源文件路径与裁剪信息
    def fill_source_info(self, index: int, source: WwiseObject):
        relative_path = waapi_utils.get_object_property(source, 'originalRelativeFilePath') or ''
        self.tblTrimInfo.setItem(index, 0, QTableWidgetItem(WwiseTableRowData.get_path_text(relative_path)))
        info = audio_source_utils.get_source_edit_info(source)
        if info is None:
            return
        for column, value in enumerate(info, start=2):
            self.tblTrimInfo.setItem(index, column, QTableWidgetItem(self._format_trim_value(value)))

    # 0 或 -0.001 等价的数值视为“无”
    @staticmethod
    def _format_trim_value(value):
        if value is None:
            return '无'
        if isinstance(value, (int, float)) and (value == 0 or abs(value + 0.001) < 1e-6):
            return '无'
        # 参数只保留 3 位小数
        if isinstance(value, float):
            text = f'{value:.3f}'.rstrip('0').rstrip('.')
            return text if text not in ('', '-') else '0'
        return str(value)

    # 读取完成后自适应列宽
    def on_info_filled(self):
        self.tblTrimInfo.resizeColumnsToContents()

    # 行右键菜单：把该行裁剪设置同步给所有同源文件对象
    def show_context_menu(self, position):
        index = self.tblTrimInfo.indexAt(position)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu(self)
        cell = self.tblTrimInfo.item(row, index.column())
        if cell is not None and cell.text():
            menu.addAction('复制', lambda: clipboard.copy(cell.text()))
        if 0 <= row < len(self.__sources):
            add_common_object_actions(menu, self.__sources[row], self)
        sync_action = menu.addAction('使用此版本')
        if menu.exec(self.tblTrimInfo.viewport().mapToGlobal(position)) == sync_action:
            self.sync_from_row(row)

    # 以指定行为基准，把所有使用同一 originalRelativeFilePath 的 AudioSource 裁剪信息改为该行数值
    def sync_from_row(self, row: int):
        if not 0 <= row < len(self.__sources):
            return
        source = self.__sources[row]
        relative_path = waapi_utils.get_object_property(source, 'originalRelativeFilePath')
        info = audio_source_utils.get_source_edit_info(source)
        if not relative_path or not info:
            Logger().warning(f'无法读取 [{source.name}] 的源文件路径或裁剪信息')
            return
        targets = waapi_utils.find_audio_sources_by_original_path(relative_path)
        if not targets:
            Logger().warning(f'未找到使用源文件 [{relative_path}] 的其他对象')
            return

        def apply_sync(index: int, target: WwiseObject):
            audio_source_utils.set_source_edit_info(target, *info)

        batch_processor.create_async(
            targets,
            apply_sync,
            '同步裁剪',
            on_finished=lambda: self.on_sync_finished(source.name, relative_path, len(targets)),
        )

    # 同步完成后提示并刷新表格
    def on_sync_finished(self, source_name: str, relative_path: str, count: int):
        Logger().info(f'已将 {count} 个使用 [{relative_path}] 的 AudioSource 同步为 [{source_name}] 的裁剪设置')
        self.refresh_sources()

    # 双击跳转到Wwise中的对象
    def show_object_in_wwise(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.__sources):
            waapi_utils.select_objects_in_wwise([self.__sources[row]])
