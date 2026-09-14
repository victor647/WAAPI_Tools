from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QStylePainter, QWidget


# 可复选下拉框：点任意一项切换勾选（含文字区域），下拉保持展开便于连续多选；
# 控件文本显示当前勾选汇总，未勾选任何项时显示 all_text
class MultiSelectCombo(QComboBox):

    selectionChanged = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.__all_text = ''
        self.__pressed_state = None
        self.setModel(QStandardItemModel(self))
        self.view().pressed.connect(self.__remember_pressed_state)
        self.view().clicked.connect(self.__toggle_option)

    # 设置可选项；checked 为需要预先勾选的项，all_text 为未勾选任何项时的显示文本
    def set_options(self, options: list[str], checked: list[str] = None, all_text: str = '') -> None:
        self.__all_text = all_text
        checked_set = set(checked or [])
        model = self.model()
        model.clear()
        for name in options:
            item = QStandardItem(name)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if name in checked_set else Qt.CheckState.Unchecked)
            model.appendRow(item)
        self.setCurrentIndex(-1)
        self.update()

    # 当前勾选的项（按选项原顺序）
    def checked_options(self) -> list[str]:
        model = self.model()
        return [model.item(row).text() for row in range(model.rowCount())
                if model.item(row).checkState() == Qt.CheckState.Checked]

    # 按名称设置勾选项；名称不在选项里时忽略
    def set_checked_options(self, names) -> None:
        wanted = set(names or [])
        model = self.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            state = Qt.CheckState.Checked if item.text() in wanted else Qt.CheckState.Unchecked
            item.setCheckState(state)
        self.update()

    def clear_checked(self) -> None:
        self.set_checked_options([])

    # 下拉框自身不用 currentIndex 显示文本，这里改画勾选汇总
    def paintEvent(self, event) -> None:
        painter = QStylePainter(self)
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        option.currentText = self._display_text()
        painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
        painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, option)

    def _display_text(self) -> str:
        checked = self.checked_options()
        return '、'.join(checked) if checked else self.__all_text

    # 记录按下瞬间的勾选状态，用于判断 Qt 是否已自动切换（仅点击复选框指示器时才会）
    def __remember_pressed_state(self, index) -> None:
        item = self.model().itemFromIndex(index)
        self.__pressed_state = item.checkState() if item is not None else None

    # 点击任意位置都切换勾选，并重新弹出下拉
    def __toggle_option(self, index) -> None:
        item = self.model().itemFromIndex(index)
        if item is None:
            return
        if self.__pressed_state == item.checkState():
            # Qt 没有自动切换（点击在文字上），这里手动切换
            new_state = Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked
            item.setCheckState(new_state)
        self.__pressed_state = None
        self.update()
        self.selectionChanged.emit()
        QTimer.singleShot(0, self.showPopup)
