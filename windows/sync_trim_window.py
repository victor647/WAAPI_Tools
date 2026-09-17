import clipboard
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMenu, QTableWidgetItem

from libraries.multi_thread import batch_processor
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, waapi_utils
from libraries.wwise_object import WwiseObject, WwiseObjectType
from table.wwise_table_context_menu import add_common_object_actions
from table.wwise_table_row_data import WwiseTableRowData
from ui.SyncTrim_ui import Ui_SyncTrim

# 表格列
COL_SOURCE_PATH = 0
COL_USAGE = 1
COL_OBJECT_PATH = 2
COL_TRIM_START = 3


# 查看并同步一批 AudioSource 的裁剪信息（TrimBegin/TrimEnd/Fade/Loop）
class SyncTrimWindow(QDialog, Ui_SyncTrim):

    def __init__(self, sources: list[WwiseObject]):
        super().__init__()
        self.setupUi(self)
        # 传进来的可能是容器 / Sound 等任意对象，打开后会先展开成所有 AudioSource
        self.__input_sources = list(sources)
        self.__sources: list = []
        self.__usage: dict = {}
        self.__path_by_id: dict = {}
        self.__input_paths: list = []
        self.__input_by_path: dict = {}
        self.__found_by_path: dict = {}
        self.setup_triggers()
        self.tblTrimInfo.setColumnCount(9)
        self.tblTrimInfo.setHorizontalHeaderLabels(
            ['源文件路径', '使用次数', 'AudioSource路径', 'TrimBegin', 'TrimEnd', 'FadeIn', 'FadeOut',
             'LoopBegin', 'LoopEnd']
        )
        self.refresh_sources()

    def setup_triggers(self):
        self.tblTrimInfo.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblTrimInfo.customContextMenuRequested.connect(self.show_context_menu)
        self.tblTrimInfo.itemDoubleClicked.connect(self.show_object_in_wwise)

    # 打开 / 刷新：先把输入对象展开成 AudioSource，再按源文件去重、逐个文件查找工程内所有引用，
    # 最后读取裁剪信息
    def refresh_sources(self):
        self.lblHint.setText('正在查找源文件…')
        self.__input_paths = []
        batch_processor.create_async(
            self.__input_sources,
            self.resolve_source_path,
            '读取源文件',
            'name',
            on_finished=self.on_source_paths_resolved,
        )

    # 工作线程：把对象展开成 AudioSource 并读取其源文件相对路径
    def resolve_source_path(self, index: int, obj: WwiseObject):
        for source in self.collect_audio_sources(obj):
            relative_path = waapi_utils.get_object_property(source, 'originalRelativeFilePath') or ''
            self.__input_paths.append((source, relative_path))
        return True

    # AudioSource 直接用；容器 / Sound 等展开成全部后代 AudioSource
    @staticmethod
    def collect_audio_sources(obj: WwiseObject) -> list:
        if obj.type == WwiseObjectType.AudioSource:
            return [obj]
        return [
            child
            for child in waapi_utils.get_child_objects(obj, True)
            if child.type == WwiseObjectType.AudioSource
        ]

    # 主线程：按源文件去重后，逐个文件查找工程内所有引用它的 AudioSource
    def on_source_paths_resolved(self):
        self.__input_by_path = {}
        for source, relative_path in self.__input_paths:
            if relative_path:
                self.__input_by_path.setdefault(relative_path, []).append(source)
        if not self.__input_by_path:
            self.lblHint.setText('没有解析出源文件')
            Logger().warning('没有解析出任何源文件')
            return
        self.__found_by_path = {}
        batch_processor.create_async(
            list(self.__input_by_path),
            self.find_references_by_path,
            '查找引用对象',
            on_finished=self.on_references_collected,
        )

    # 工作线程：按 originalRelativeFilePath 反查工程内所有使用该文件的 AudioSource
    def find_references_by_path(self, index: int, relative_path: str):
        self.__found_by_path[relative_path] = waapi_utils.find_audio_sources_by_original_path(relative_path)
        return True

    # 主线程：合并同源文件的对象（按文件分组、组内编号即使用次数）并刷新表格
    def on_references_collected(self):
        ordered: list = []
        seen_ids: set = set()
        self.__usage = {}
        self.__path_by_id = {}
        for relative_path, input_sources in self.__input_by_path.items():
            group = list(input_sources)
            group_ids = {obj.id for obj in group}
            for obj in self.__found_by_path.get(relative_path, []):
                if obj.id not in group_ids:
                    group_ids.add(obj.id)
                    group.append(obj)
            usage_index = 0
            for obj in group:
                if obj.id in seen_ids:
                    continue
                seen_ids.add(obj.id)
                usage_index += 1
                self.__usage[obj.id] = usage_index
                self.__path_by_id[obj.id] = relative_path
                ordered.append(obj)
        self.__sources = ordered
        Logger().info(
            f'共 {len(self.__sources)} 个 AudioSource 使用 {len(self.__input_by_path)} 个源文件'
        )
        self.reload_trim_info()

    # 重建表格并异步读取每个对象的裁剪信息
    def reload_trim_info(self):
        self.lblHint.setText(
            f'AudioSource 裁剪信息（共 {len(self.__sources)} 个，{len(self.__input_by_path)} 个源文件）'
        )
        self.tblTrimInfo.setRowCount(len(self.__sources))
        for index, source in enumerate(self.__sources):
            self.tblTrimInfo.setItem(index, COL_SOURCE_PATH, QTableWidgetItem(
                WwiseTableRowData.get_path_text(self.__path_by_id.get(source.id, ''))
            ))
            self.tblTrimInfo.setItem(index, COL_USAGE, QTableWidgetItem(
                str(self.__usage.get(source.id, ''))
            ))
            self.tblTrimInfo.setItem(index, COL_OBJECT_PATH, QTableWidgetItem(
                WwiseTableRowData.get_path_text(source.path)
            ))
        batch_processor.create_async(
            self.__sources,
            self.fill_source_info,
            '读取裁剪信息',
            on_finished=self.on_info_filled,
        )

    # 异步读取单个对象的裁剪信息
    def fill_source_info(self, index: int, source: WwiseObject):
        info = audio_source_utils.get_source_edit_info(source)
        if info is None:
            return
        for column, value in enumerate(info, start=COL_TRIM_START):
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
        resize_table_and_window(self.tblTrimInfo, self)

    # 行右键菜单：复制单元格、通用对象动作、按本行同步裁剪、重新查找引用对象
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
        refresh_action = menu.addAction('重新查找引用对象')
        chosen = menu.exec(self.tblTrimInfo.viewport().mapToGlobal(position))
        if chosen == sync_action:
            self.sync_from_row(row)
        elif chosen == refresh_action:
            # 工程里可能新增了引用该文件的 AudioSource，重新走一遍查找
            self.refresh_sources()

    # 以指定行为基准，把所有使用同一 originalRelativeFilePath 的 AudioSource 裁剪信息改为该行数值
    def sync_from_row(self, row: int):
        if not 0 <= row < len(self.__sources):
            return
        source = self.__sources[row]
        relative_path = self.__path_by_id.get(source.id) \
            or waapi_utils.get_object_property(source, 'originalRelativeFilePath')
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

    # 同步完成后提示并刷新表格（源文件与引用关系没变，只重读裁剪信息）
    def on_sync_finished(self, source_name: str, relative_path: str, count: int):
        Logger().info(f'已将 {count} 个使用 [{relative_path}] 的 AudioSource 同步为 [{source_name}] 的裁剪设置')
        self.reload_trim_info()

    # 双击跳转到Wwise中的对象
    def show_object_in_wwise(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.__sources):
            waapi_utils.select_objects_in_wwise([self.__sources[row]])
