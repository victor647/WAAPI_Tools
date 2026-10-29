from PySide6.QtCore import QEvent, QRect, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QTableWidgetItem,
)

import globals.global_variables as gv
from libraries.base_dialog import BaseDialog
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import compression_utils


# 分析结果表固定第一列为「选中」，复选框居中绘制并支持整格点击切换
SELECTION_COL = 0


class AnalysisCheckDelegate(QStyledItemDelegate):

    def createEditor(self, parent, option, index):
        return None

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            state = index.data(Qt.ItemDataRole.CheckStateRole)
            checked = (
                state == Qt.CheckState.Checked
                or state == Qt.CheckState.Checked.value
            )
            model.setData(
                index,
                Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked,
                Qt.ItemDataRole.CheckStateRole,
            )
            return True
        return super().editorEvent(event, model, option, index)

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.features &= ~QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
        opt.text = ''
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        state = index.data(Qt.ItemDataRole.CheckStateRole)
        checked = (
            state == Qt.CheckState.Checked
            or state == Qt.CheckState.Checked.value
        )
        button = QStyleOptionButton()
        button.state = QStyle.StateFlag.State_Enabled
        button.state |= QStyle.StateFlag.State_On if checked else QStyle.StateFlag.State_Off
        if opt.state & QStyle.StateFlag.State_MouseOver:
            button.state |= QStyle.StateFlag.State_MouseOver
        size = style.pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, button, opt.widget)
        button.rect = QRect(0, 0, size, size)
        button.rect.moveCenter(opt.rect.center())
        style.drawPrimitive(
            QStyle.PrimitiveElement.PE_IndicatorItemViewItemCheck,
            button, painter, opt.widget,
        )


# 分析窗口结果表统一控制器：表头自动加「选中」列，行数据从第 1 列开始
class AnalysisTable:

    def __init__(self, table, selection_width: int = 36):
        self.table = table
        self.selection_width = selection_width
        self.table.setItemDelegateForColumn(
            SELECTION_COL, AnalysisCheckDelegate(self.table)
        )
        self.table.verticalHeader().setVisible(False)

    @staticmethod
    def selection_item(checked: bool = True) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def setup(self, headers: list[str]):
        self.table.setColumnCount(len(headers) + 1)
        self.table.setHorizontalHeaderLabels(['选中', *headers])
        self.table.setColumnWidth(SELECTION_COL, self.selection_width)

    def ensure_rows(self, count: int, checked: bool = True):
        self.table.setRowCount(count)
        for row in range(count):
            if self.table.item(row, SELECTION_COL) is None:
                self.table.setItem(row, SELECTION_COL, self.selection_item(checked))

    def prepare_row(self, row: int, checked: bool = True):
        while self.table.rowCount() <= row:
            self.table.insertRow(self.table.rowCount())
        if self.table.item(row, SELECTION_COL) is None:
            self.table.setItem(row, SELECTION_COL, self.selection_item(checked))

    def is_checked(self, row: int) -> bool:
        item = self.table.item(row, SELECTION_COL)
        if item is None:
            return False
        state = item.checkState()
        return state == Qt.CheckState.Checked

    def selected_rows(self, visible_only: bool = False) -> list[int]:
        rows = []
        for row in range(self.table.rowCount()):
            if not self.is_checked(row):
                continue
            if visible_only and self.table.isRowHidden(row):
                continue
            rows.append(row)
        return rows

    def select_all(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, SELECTION_COL)
            if item is not None:
                item.setCheckState(state)
        self.table.blockSignals(False)

    def set_row_values(self, row: int, values: list, start_column: int = 1):
        self.prepare_row(row)
        for offset, value in enumerate(values):
            column = start_column + offset
            if isinstance(value, QTableWidgetItem):
                self.table.setItem(row, column, value)
            else:
                self.table.setItem(row, column, QTableWidgetItem(str(value)))


# 带分析步骤的窗口通用基类：
# - 只从主窗口「选中」列已勾选的对象取分析范围；
# - 未勾选行及其子树不参与分析；
# - 子类实现 analyze_objects / process_objects，并自行把「分析」「处理」按钮接到 run_analysis / run_process
class BaseAnalysisDialog(BaseDialog):

    analysis_tool_name = "分析"

    def setup_analysis_table(self, table, headers: list[str], selection_width: int = 36) -> AnalysisTable:
        controller = AnalysisTable(table, selection_width)
        controller.setup(headers)
        self.analysis_table = controller
        return controller

    # 主窗口当前勾选的可见对象；没有主窗口时退回全局对象列表
    @staticmethod
    def checked_analysis_objects() -> list:
        window = gv.main_window
        if window is None:
            return list(gv.active_objects)
        return list(window.get_checked_visible_objects())

    # 勾选对象（含按设置展开的子孙），并排除未勾选行对应的子树
    @staticmethod
    def collect_analysis_targets(target_types=None, expand: bool = None) -> list:
        window = gv.main_window
        if window is None:
            return list(gv.active_objects)
        return list(
            window.collect_tool_targets(
                target_types, expand, checked_only=True
            )
        )

    # 需要按根对象统计时使用：返回勾选根与「最近表格行是否勾选」的路径映射
    @staticmethod
    def analysis_scope() -> tuple:
        window = gv.main_window
        if window is None:
            return list(gv.active_objects), {}
        return window.get_checked_scope()

    @classmethod
    def no_checked_objects_message(cls) -> str:
        return (
            "主窗口表格里没有勾选任何对象（表格最左侧的「选中」列）。\n"
            "请先勾选要分析的对象。"
        )

    # 统一的「没有勾选对象」提示
    def warn_no_analysis_targets(self, title: str = None, detail: str = ""):
        message = self.no_checked_objects_message()
        if detail:
            message += f"\n\n{detail}"
        Logger().warning(message)
        QMessageBox.warning(self, title or self.analysis_tool_name, message)

    # 分析结果表里没有勾选任何行时的提示
    def warn_no_selected_rows(self, title: str = None, detail: str = ""):
        message = detail or '没有勾选需要处理的结果行，请先在结果表「选中」列勾选。'
        Logger().warning(message)
        QMessageBox.warning(self, title or self.analysis_tool_name, message)

    # 分析结束时统一记录并弹出结果提示；子类在分析完成回调中调用
    def show_analysis_result(self, summary: str, detail: str = "", title: str = None):
        Logger().info(summary)
        if not self.isVisible():
            return
        message = summary
        if detail:
            message += f"\n\n{detail}"
        QMessageBox.information(self, title or self.analysis_tool_name, message)

    # 供分析按钮直接调用：没有勾选对象时提示并返回 None
    def load_analysis_targets(
        self, target_types=None, expand: bool = None, detail: str = ""
    ) -> list | None:
        objects = self.collect_analysis_targets(target_types, expand)
        if not objects:
            self.warn_no_analysis_targets(detail=detail)
            return None
        return objects

    # 供按根对象分析的窗口使用
    def load_analysis_scope(self, detail: str = "") -> tuple | None:
        roots, row_checked_by_path = self.analysis_scope()
        if not roots:
            self.warn_no_analysis_targets(detail=detail)
            return None
        return roots, row_checked_by_path

    # 子类在「分析」按钮中实现
    def analyze_objects(self, objects: list):
        raise NotImplementedError

    # 子类在「处理」按钮中实现
    def process_objects(self):
        raise NotImplementedError

    def run_analysis(self, target_types=None, expand: bool = None, detail: str = ""):
        objects = self.load_analysis_targets(target_types, expand, detail)
        if objects is not None:
            self.analyze_objects(objects)

    def run_process(self):
        self.process_objects()

    # 判断某个后代对象是否落在未勾选行的子树里
    @staticmethod
    def is_excluded_by_scope(path: str, row_checked_by_path: dict) -> bool:
        return compression_utils.is_excluded_by_rows(path, row_checked_by_path)
