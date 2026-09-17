from enum import Enum

import clipboard
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush
from PySide6.QtWidgets import QDialog, QMenu, QTableWidgetItem

from libraries.utils import audio_utils, path_utils, theme_utils
from libraries.utils.qt_utils import resize_table_and_window
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import audio_source_utils, mixing_utils, waapi_utils
from table.wwise_table_context_menu import add_common_object_actions, connect_double_click_select
from ui.LoudnessDetail_ui import Ui_LoudnessDetail

# 明细表的列
COL_NAME = 0
COL_TYPE = 1
COL_PATH = 2
COL_PROPERTY_START = 3
COL_SUBTOTAL = 7

# 对象类型上没有该属性时的占位文本
NOT_APPLICABLE = '\u2014'

OBJECT_CHAIN_LABEL = '对象'
BUS_CHAIN_LABEL = '总线'
NO_GAIN_TEXT = '（无音量调整）'
# 对象链路上不适用的属性（只有 Bus / AuxBus 才有）
BUS_VOLUME_NAME = 'BusVolume'


# 明细窗口要显示哪条链路
class DetailChain(Enum):
    Object = 'object'
    Bus = 'bus'


# 对象类型文本：祖先链里可能存在 WAAPI 未返回类型的节点，直接读字典避免枚举转换抛异常
def get_type_text(node) -> str:
    return str((node.wwise_dict or {}).get('type', '') or '')


# 只读单元格的标志
READ_ONLY_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
# 可编辑单元格的标志（音量属性可以双击改值并同步回 Wwise）
EDITABLE_FLAGS = READ_ONLY_FLAGS | Qt.ItemFlag.ItemIsEditable


# 增益用主题的 success 色、减益用 danger 色，其它保持默认文字颜色
def make_value_item(value, editable: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(value if isinstance(value, str) else f'{value:+.1f}')
    item.setFlags(EDITABLE_FLAGS if editable else READ_ONLY_FLAGS)
    if isinstance(value, (int, float)):
        color = theme_utils.get_gain_text_color(value)
        if color:
            item.setForeground(color)
    return item


# 按数值刷新文字与颜色（改值同步成功后回写单元格）
def update_value_item(item: QTableWidgetItem, value) -> None:
    item.setText(f'{value:+.1f}')
    item.setForeground(theme_utils.get_gain_text_color(value) or QBrush())


# 响度调整明细窗口：只列出指定链路上逐级每个属性的调整值
class LoudnessDetailWindow(QDialog, Ui_LoudnessDetail):

    def __init__(self, file_path: str, wwise_objects: list, loudness: float = None,
                 chain: DetailChain = DetailChain.Object, loudness_unit: str = 'dBFS'):
        super().__init__()
        self.setupUi(self)
        self.__file_path = file_path
        self.__loudness = loudness
        self.__loudness_unit = loudness_unit
        self.__chain = chain
        # 被改过属性的对象：关闭窗口后由响度调整窗口据此重算相关行
        self.__modified_objects: dict = {}
        self.__objects: dict = {}
        self.__row_objects: dict = {}
        self.__node_values: dict = {}
        self.__node_rows: dict = {}
        # 每个引用对象一条链路记录：{'object', 'nodes', 'subtotal_row'}
        self.__chains: list = []
        self.__updating = False
        self.__chain_label = OBJECT_CHAIN_LABEL if chain == DetailChain.Object else BUS_CHAIN_LABEL
        self.setWindowTitle(f'{self.__chain_label}音量调整明细')
        display_path = path_utils.get_display_path(audio_source_utils.to_originals_relative_path(file_path))
        self.lblTitle.setText(f'音频文件：{display_path}')
        self.lblReferences.setText(self.__format_references(wwise_objects))
        multiple = len(wwise_objects) > 1
        for wwise_object in wwise_objects:
            object_details, bus_details = mixing_utils.get_gain_details(wwise_object)
            details = object_details if chain == DetailChain.Object else bus_details
            # 多个对象引用同一文件时，用小计行标出这一段属于哪个对象
            subtotal_label = f'小计（{wwise_object.name}）' if multiple else '小计'
            self.__fill_chain(wwise_object, subtotal_label, details)
        resize_table_and_window(self.tblDetails, self)
        self.__sync_chain_columns()
        self.__update_summary()
        self.setup_triggers()

    # 对象链路上不会出现 BusVolume（只有 Bus / AuxBus 才有），对象明细里隐藏该列
    def __sync_chain_columns(self):
        if BUS_VOLUME_NAME not in mixing_utils.GAIN_PROPERTY_NAMES:
            return
        column = COL_PROPERTY_START + mixing_utils.GAIN_PROPERTY_NAMES.index(BUS_VOLUME_NAME)
        self.tblDetails.setColumnHidden(column, self.__chain == DetailChain.Object)

    def setup_triggers(self):
        self.tblDetails.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tblDetails.customContextMenuRequested.connect(self.show_context_menu)
        self.tblDetails.itemChanged.connect(self.on_item_changed)
        # 双击在 Wwise 中选中（含 Wwise 对象的表格的默认行为）
        connect_double_click_select(self.tblDetails, self.__row_object_list)

    # 某一行的 Wwise 对象（供双击在 Wwise 中选中使用）
    def __row_object_list(self, row: int) -> list:
        node = self.__row_objects.get(row)
        return [node] if node else []

    # 表格右键菜单：路径列可复制对象路径，行上提供通用对象动作（在Wwise中选中）
    def show_context_menu(self, position):
        item = self.tblDetails.itemAt(position)
        if item is None:
            return
        node = self.__row_objects.get(item.row())
        if node is None:
            return
        menu = QMenu(self)
        if item.column() == COL_PATH:
            menu.addAction('复制', lambda: self.copy_object_path(node))
        # 通用对象动作（在Wwise中选中、AudioSource 预览）
        add_common_object_actions(menu, node, self)
        if not menu.actions():
            return
        menu.exec(self.tblDetails.viewport().mapToGlobal(position))

    # 复制对象的完整路径（表格里显示的是缩写形式）
    @staticmethod
    def copy_object_path(node):
        clipboard.copy(node.path)
        Logger().info(f'已复制到剪贴板：{node.path}')

    # 改过属性的对象列表（按 id 去重）
    def modified_objects(self) -> list:
        return list(self.__modified_objects.values())

    # 双击修改音量属性后同步写回 Wwise
    def on_item_changed(self, item: QTableWidgetItem):
        if self.__updating:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload:
            return
        object_id, property_name = payload
        node = self.__objects.get(object_id)
        if node is None:
            return
        try:
            value = float(item.text())
        except (TypeError, ValueError):
            self.__restore_cell(item, node, property_name)
            Logger().warning(f'音量值必须是数字：{item.text()}')
            return
        if not waapi_utils.set_object_property(node, property_name, value):
            self.__restore_cell(item, node, property_name)
            Logger().error(f'写入 Wwise 失败：{node.name} 的 {property_name}')
            return
        self.__modified_objects[node.id] = node
        self.__node_values.setdefault(node.id, {})[property_name] = value
        self.__updating = True
        update_value_item(item, value)
        self.__updating = False
        self.__refresh_subtotals(node.id)
        Logger().info(f'已同步到 Wwise：{node.name} 的 {property_name} = {value:+.1f}')

    # 写入失败或数值非法时把单元格还原成当前值
    def __restore_cell(self, item: QTableWidgetItem, node, property_name: str):
        value = mixing_utils.get_node_gain_values(node).get(property_name)
        self.__updating = True
        if value is None:
            item.setText(NOT_APPLICABLE)
            item.setForeground(QBrush())
        else:
            update_value_item(item, value)
        self.__node_values.setdefault(node.id, {})[property_name] = value
        self.__updating = False

    # 属性改动后重算该层级行的小计、所属链路的小计行与底部汇总
    def __refresh_subtotals(self, changed_id: str):
        values = self.__node_values.get(changed_id, {})
        self.__updating = True
        for row in self.__node_rows.get(changed_id, []):
            # 同一对象可能出现在多条链路上，所有行的属性值与行小计一起刷新
            for offset, name in enumerate(mixing_utils.GAIN_PROPERTY_NAMES):
                item = self.tblDetails.item(row, COL_PROPERTY_START + offset)
                value = values.get(name)
                if item is None or value is None:
                    continue
                update_value_item(item, value)
            item = self.tblDetails.item(row, COL_SUBTOTAL)
            if item is not None:
                update_value_item(item, sum(values.values()))
        for chain in self.__chains:
            if changed_id not in {node.id for node in chain['nodes']}:
                continue
            # 小计行上每个属性列也是该链路的合计
            chain_values = [self.__node_values.get(node.id, {}) for node in chain['nodes']]
            for offset, name in enumerate(mixing_utils.GAIN_PROPERTY_NAMES):
                self.__update_total_cell(
                    self.tblDetails.item(chain['subtotal_row'], COL_PROPERTY_START + offset),
                    self.__total_of(chain_values, name),
                )
            subtotal_item = self.tblDetails.item(chain['subtotal_row'], COL_SUBTOTAL)
            if subtotal_item is not None:
                update_value_item(subtotal_item, self.__chain_offset(chain))
                subtotal_item.setText(f'{subtotal_item.text()} dB')
        self.__updating = False
        resize_table_and_window(self.tblDetails, self)
        self.__update_summary()

    # 一组层级里某个属性的合计；这些层级都没有该属性时返回 None
    @staticmethod
    def __total_of(values_list: list, name: str):
        present = [values.get(name) for values in values_list if values.get(name) is not None]
        return sum(present) if present else None

    # 写入合计单元格（没有该属性时显示不适用占位）
    @staticmethod
    def __update_total_cell(item: QTableWidgetItem, total):
        if item is None:
            return
        if total is None:
            item.setText(NOT_APPLICABLE)
            item.setForeground(QBrush())
        else:
            update_value_item(item, total)

    # 某条链路的小计
    def __chain_offset(self, chain: dict) -> float:
        return sum(sum(self.__node_values.get(node.id, {}).values()) for node in chain['nodes'])

    # 引用该文件的 Wwise 对象路径，显示在表格上方（表格里不再占行）
    @staticmethod
    def __format_references(wwise_objects: list) -> str:
        lines = [path_utils.get_display_path(obj.path) for obj in wwise_objects]
        return f'引用对象（{len(wwise_objects)}）：\n' + '\n'.join(lines)

    # 把一条链路的明细逐级写入表格，并在末尾补一行小计；
    # WorkUnit / Folder 这类没有音量属性的层级直接过滤掉
    def __fill_chain(self, wwise_object, subtotal_label: str, details: list):
        rows = [(node, values) for node, values in details if values]
        for node, values in rows:
            self.__objects[node.id] = node
            self.__node_values[node.id] = dict(values)
            row = self.tblDetails.rowCount()
            self.__row_objects[row] = node
            self.__node_rows.setdefault(node.id, []).append(row)
            self.tblDetails.insertRow(row)
            self.__set_text_cell(row, COL_NAME, node.name)
            self.__set_text_cell(row, COL_TYPE, get_type_text(node))
            self.__set_text_cell(row, COL_PATH, path_utils.get_display_path(node.path))
            for offset, name in enumerate(mixing_utils.GAIN_PROPERTY_NAMES):
                value = values.get(name)
                item = make_value_item(NOT_APPLICABLE if value is None else value, editable=value is not None)
                if value is not None:
                    # 双击改值后按这个标识回写 Wwise
                    item.setData(Qt.ItemDataRole.UserRole, (node.id, name))
                    item.setToolTip(f'{node.name} 的 {name}，双击可修改并同步到 Wwise')
                self.tblDetails.setItem(row, COL_PROPERTY_START + offset, item)
            self.tblDetails.setItem(row, COL_SUBTOTAL, make_value_item(sum(values.values())))
        row = self.tblDetails.rowCount()
        self.tblDetails.insertRow(row)
        # 该链路没有可调整的音量属性时给一行占位，避免空表
        self.__set_text_cell(row, COL_NAME, subtotal_label if rows else NO_GAIN_TEXT)
        # 小计行上每个属性列给出该链路的合计
        chain_values = [values for _node, values in rows]
        for offset, name in enumerate(mixing_utils.GAIN_PROPERTY_NAMES):
            total = self.__total_of(chain_values, name)
            self.tblDetails.setItem(
                row, COL_PROPERTY_START + offset,
                make_value_item(NOT_APPLICABLE if total is None else total),
            )
        subtotal = make_value_item(mixing_utils.sum_gain_details(rows))
        subtotal.setText(f'{subtotal.text()} dB')
        self.tblDetails.setItem(row, COL_SUBTOTAL, subtotal)
        # 记录链路：属性被改动后据此重算小计与底部汇总
        self.__chains.append({
            'object': wwise_object,
            'nodes': [node for node, _values in rows],
            'subtotal_row': row,
        })

    # 写入只读文本单元格
    def __set_text_cell(self, row: int, column: int, text: str):
        item = QTableWidgetItem(text)
        item.setFlags(READ_ONLY_FLAGS)
        self.tblDetails.setItem(row, column, item)

    # 底部汇总：样本响度 + 每个引用对象在该链路上的偏移（属性改动后会重新计算）
    def __update_summary(self):
        parts = []
        if self.__loudness is None:
            parts.append('样本响度 未分析')
        elif self.__loudness <= audio_utils.MIN_LOUDNESS_DB:
            parts.append('样本响度 无信号')
        else:
            parts.append(f'样本响度 {self.__loudness:.1f} {self.__loudness_unit}')
        for chain in self.__chains:
            parts.append(f'{chain["object"].name}：{self.__chain_label} {self.__chain_offset(chain):+.1f} dB')
        self.lblSummary.setText('\n'.join(parts))
        Logger().debug(
            f'响度调整明细（{self.__chain_label}）：{self.__file_path} 共 {len(self.__chains)} 个引用对象'
        )
