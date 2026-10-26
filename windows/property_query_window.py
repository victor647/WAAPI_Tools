from windows.base_analysis_dialog import BaseAnalysisDialog
import json
import webbrowser

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem

from libraries.multi_thread import batch_processor
from libraries.table_view.table_path_item import create_path_item
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import waapi_utils
from libraries.wwise_object import WwiseObject
from libraries.table_view.table_context_menu import install_row_object_context
from ui.PropertyQuery_ui import Ui_PropertyQuery

# Wwise 对象属性说明文档（官方 wobjects 索引页）
PROPERTY_DOC_URL = 'https://www.audiokinetic.com/zh/library/2025.1.10_9233/?source=SDK&id=wobjects_index.html'

# 对象信息列：名称 / 类型 / 路径
COL_NAME = 0
COL_PATH = 2

# 常用属性快捷项（与查询输入框共用同一份属性名列表）
COMMON_PROPERTY_NAMES = [
    'Volume',
    'MakeUpGain',
    'Pitch',
    'Lowpass',
    'Highpass',
    'InitialDelay',
    'IsLoopingEnabled',
    'IsStreamingEnabled',
    'Priority',
    '3DSpatialization',
    'Attenuation',
    'OutputBus',
    'Conversion',
    'EnableDiffraction',
    'UseGameAuxSends',
]


# 属性查询窗口：对传入对象列表批量读取指定属性，把结果输出为表格
class PropertyQueryWindow(BaseAnalysisDialog, Ui_PropertyQuery):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        # 只取主窗口「选中」列已勾选的对象
        self.__objects: list[WwiseObject] = self.collect_analysis_targets()
        self.__property_names: list[str] = []
        self.__results = []
        self.__row_types: list[str] = []
        self.__type_missing_props: dict[str, set] = {}
        self.__missing_combos: list[tuple] = []
        self._setup_common_property_combo()
        self.setup_triggers()
        self.__pressed_common_state = None
        self.lblObjectCount.setText(f'表格内共 {len(self.__objects)} 个对象')
        # 打开窗口就先把对象列表铺进表格，属性列留空，点「查询」后再补值
        self._render_object_rows()
        resize_table_and_window(self.tblPropertyResults, self)
        self.tblPropertyResults.setSortingEnabled(True)

    def setup_triggers(self):
        self.btnQuery.clicked.connect(self.start_query)
        self.btnPropertyHelp.clicked.connect(self.open_property_doc)
        self.btnClose.clicked.connect(self.accept)
        self.iptPropertyNames.returnPressed.connect(self.start_query)
        self.iptPropertyNames.textChanged.connect(self._sync_common_checkboxes_from_input)
        common_view = self.cbbCommonProperties.view()
        common_view.pressed.connect(self._remember_common_pressed_state)
        common_view.clicked.connect(self._on_common_property_clicked)
        self.tblPropertyResults.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        install_row_object_context(
            self.tblPropertyResults,
            self.objects_at_row,
            path_columns=(COL_PATH,),
            default_action="select",
        )

    # 往可复选下拉框里填充常用属性名
    def _setup_common_property_combo(self):
        model = QStandardItemModel(self.cbbCommonProperties)
        for name in COMMON_PROPERTY_NAMES:
            item = QStandardItem(name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            model.appendRow(item)
        self.cbbCommonProperties.setModel(model)
        self.cbbCommonProperties.setCurrentIndex(-1)

    # 记录按下瞬间的复选状态，用于判断 Qt 是否已自动切换（仅点击复选框指示器时才会）
    def _remember_common_pressed_state(self, index):
        item = self.cbbCommonProperties.model().itemFromIndex(index)
        self.__pressed_common_state = item.checkState() if item is not None else None

    # 点击任意位置（含文字）都切换勾选并同步到输入框；下拉保持弹出便于连续多选
    def _on_common_property_clicked(self, index):
        item = self.cbbCommonProperties.model().itemFromIndex(index)
        if item is not None and self.__pressed_common_state == item.checkState():
            # Qt 没有自动切换（点击在文字上），这里手动切换
            new_state = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new_state)
        self.__pressed_common_state = None
        self._sync_input_from_common()
        # 重新弹出下拉，便于连续勾选多个属性
        QTimer.singleShot(0, self.cbbCommonProperties.showPopup)

    # 读取全部常用属性的勾选状态，重排输入框内容（未勾选即移除）
    def _sync_input_from_common(self):
        model = self.cbbCommonProperties.model()
        checked_names = set()
        for row in range(model.rowCount()):
            if model.item(row).checkState() == Qt.CheckState.Checked:
                checked_names.add(model.item(row).text())
        tokens = [token.strip() for token in self.iptPropertyNames.text().split(';') if token.strip()]
        # 保留用户手输的其它属性与仍勾选的常用属性，新勾选的按下拉顺序追加到末尾
        kept = [token for token in tokens if token in checked_names or token not in COMMON_PROPERTY_NAMES]
        appended = [name for name in COMMON_PROPERTY_NAMES if name in checked_names and name not in kept]
        self.iptPropertyNames.setText(';'.join(kept + appended))

    # 输入框内容变化时同步常用属性的勾选状态
    def _sync_common_checkboxes_from_input(self):
        tokens = set(token.strip() for token in self.iptPropertyNames.text().split(';') if token.strip())
        model = self.cbbCommonProperties.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            state = Qt.CheckState.Checked if item.text() in tokens else Qt.CheckState.Unchecked
            item.setCheckState(state)

    # 解析输入框中的属性名列表（用英文分号分隔）
    def parse_property_names(self) -> list[str]:
        raw_text = self.iptPropertyNames.text()
        names = [part.strip() for part in raw_text.split(';')]
        return [name for name in names if name]

    # 打开官方属性说明文档
    def open_property_doc(self):
        webbrowser.open(PROPERTY_DOC_URL)

    # 按当前属性名列表重建表格：名称/类型/路径三列填对象信息，属性列留空
    def _render_object_rows(self):
        self.tblPropertyResults.clear()
        self.tblPropertyResults.setColumnCount(3 + len(self.__property_names))
        self.tblPropertyResults.setHorizontalHeaderLabels(['名称', '类型', '路径'] + self.__property_names)
        self.tblPropertyResults.setRowCount(len(self.__objects))
        for index, obj in enumerate(self.__objects):
            name_item = QTableWidgetItem(obj.name)
            # 排序后行序会变化，用对象 id 保证双击仍能定位到正确对象
            name_item.setData(Qt.ItemDataRole.UserRole, obj.id)
            self.tblPropertyResults.setItem(index, COL_NAME, name_item)
            self.tblPropertyResults.setItem(index, 1, QTableWidgetItem(obj.type.name))
            self.tblPropertyResults.setItem(index, COL_PATH, create_path_item(obj.path))

    # 按输入属性名对全部对象发起查询
    def start_query(self):
        self.__property_names = self.parse_property_names()
        if not self.__property_names:
            Logger().warning('请输入要查询的属性名，多个用分号分隔')
            return
        if not self.__objects:
            Logger().warning('没有可查询的对象')
            return
        self.__results = [None] * len(self.__objects)
        self.__row_types = [''] * len(self.__objects)
        self.__type_missing_props = {}
        self.__missing_combos = []
        self.tblPropertyResults.setSortingEnabled(False)
        self._render_object_rows()
        self.__prefetched_pages: set = set()
        self.__values_by_id: dict = {}
        # 仍按对象逐个驱动批处理（进度条跟着对象数量走），属性在 worker 里按「查询分页大小」惰性分批取回
        batch_processor.create_async(
            self.__objects,
            self.read_object_properties,
            '读取属性',
            'name',
            on_finished=self.on_query_finished,
        )

    # 工作线程内读取单个对象的属性；所在分页还没取过时先把整页取回（同类型合并成一次查询）
    def read_object_properties(self, index: int, obj: WwiseObject):
        self.__prefetch_page(index)
        values = self.__values_by_id.get(obj.id, {})
        self.__results[index] = values
        return True

    # 预取 index 所在分页的属性：只在分页首次被访问时发起一次 WAAPI 查询
    def __prefetch_page(self, index: int):
        start, end = waapi_utils.page_bounds(self.__objects, index)
        if start in self.__prefetched_pages:
            return
        self.__prefetched_pages.add(start)
        page = self.__objects[start:end]
        # 先按对象类型分组：已确认该类型不含的属性不再重复查询
        entries_by_type: dict[str, list] = {}
        for offset, obj in enumerate(page):
            row_index = start + offset
            obj_type = obj.type.name
            self.__row_types[row_index] = obj_type
            entries_by_type.setdefault(obj_type, []).append((row_index, obj))
        for obj_type, entries in entries_by_type.items():
            missing_props = self.__type_missing_props.get(obj_type, set())
            candidates = [name for name in self.__property_names if name not in missing_props]
            if not candidates:
                for row_index, _obj in entries:
                    self.__results[row_index] = {}
                continue
            values_by_id = waapi_utils.get_objects_properties([obj for _row, obj in entries], candidates)
            # 查询后仍缺失的属性记为“该类型不含有”，后续同类型对象跳过
            for row_index, obj in entries:
                values = values_by_id.get(obj.id, {})
                self.__values_by_id[obj.id] = values
                self.__results[row_index] = values
                for name in candidates:
                    if name in values:
                        continue
                    self.__type_missing_props.setdefault(obj_type, set()).add(name)
                    if (obj_type, name) not in self.__missing_combos:
                        self.__missing_combos.append((obj_type, name))

    # 查询完成后在主线程把结果写入表格
    def on_query_finished(self):
        for index, values in enumerate(self.__results):
            if values is None:
                continue
            obj_type = self.__row_types[index]
            missing_props = self.__type_missing_props.get(obj_type, set())
            for column, property_name in enumerate(self.__property_names, start=3):
                if property_name in values:
                    value_text = self._format_value(values[property_name])
                elif property_name in missing_props:
                    # 该类型不包含此属性
                    value_text = '-'
                else:
                    value_text = ''
                self.tblPropertyResults.setItem(index, column, QTableWidgetItem(value_text))
        resize_table_and_window(self.tblPropertyResults, self)
        # 数据写完后才开启表头排序，避免填充过程中行被反复重排
        self.tblPropertyResults.setSortingEnabled(True)
        self._notify_missing_properties()
        Logger().query(f'属性查询完成，共查询 {len(self.__objects)} 个对象 × {len(self.__property_names)} 个属性')

    # 查询完成后弹出提示：哪些对象类型不含有哪些属性
    def _notify_missing_properties(self):
        if not self.__missing_combos:
            return
        lines = [f'{obj_type} 类型不含有 {name} 属性' for obj_type, name in self.__missing_combos]
        QMessageBox.warning(self, '属性查询', '\n'.join(lines))

    # 属性值格式化为可读文本（布尔/列表/字典等转字符串）
    @staticmethod
    def _format_value(value):
        if value is None:
            return ''
        if isinstance(value, bool):
            return 'True' if value else 'False'
        if isinstance(value, dict):
            # WAAPI 引用类属性返回对象时显示其 name（没有 name 时退回 id）
            if value.get('name'):
                return str(value['name'])
            if value.get('id'):
                return str(value['id'])
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, list):
            # 对象列表（如多个引用）逐项取 name 显示
            names = [item['name'] for item in value if isinstance(item, dict) and item.get('name')]
            if names and len(names) == len(value):
                return '、'.join(str(name) for name in names)
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    # 行对象：名称列 UserRole 中存对象 id，排序后也能正确解析
    def objects_at_row(self, row: int) -> list:
        name_item = self.tblPropertyResults.item(row, COL_NAME)
        obj_id = name_item.data(Qt.ItemDataRole.UserRole) if name_item else None
        if obj_id is None:
            return []
        target = next((obj for obj in self.__objects if obj.id == obj_id), None)
        return [target] if target is not None else []
