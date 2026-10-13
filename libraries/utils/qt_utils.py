from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QMessageBox,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

# 路径类表格列的默认固定宽度
PATH_COLUMN_DEFAULT_WIDTH = 300


# 判定表头文本是否属于路径列（如路径、对象路径、源文件路径、原工程路径等）
def is_path_column(header_text: str) -> bool:
    if not header_text:
        return False
    text = header_text.lower()
    return "路径" in text or "path" in text


# 弹出消息框
def show_message_box(title: str, text: str):
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.exec()


# 根据表格全部列内容的总宽度，自动拉伸调整所在窗口的宽度，避免出现水平滚动条
def auto_adjust_window_width(
    table: QAbstractItemView,
    parent_window: QWidget = None,
    padding: int = 20,
    extra_padding: int = 12,
    resize_columns: bool = True,
    resize_window: bool = True,
) -> None:
    if not table:
        return
    window = parent_window or table.window()
    if not window:
        return

    header = table.horizontalHeader()
    if not header or header.count() == 0:
        return

    model = table.model()
    if not model:
        return

    metrics = table.fontMetrics()
    row_count = model.rowCount()
    col_count = header.count()

    columns_width = 0
    for col in range(col_count):
        if not table.isColumnHidden(col):
            header_val = model.headerData(col, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            header_text = str(header_val) if header_val is not None else ""

            if is_path_column(header_text):
                # 隐藏根目录开启时路径精简，保持 300px 紧凑宽度；未开启隐藏根目录时前缀带有较长根目录，合理展开避免只能看到最左侧
                from libraries.utils import user_config
                if user_config.get_tool_path_hide_root():
                    max_col_width = PATH_COLUMN_DEFAULT_WIDTH
                else:
                    content_w = metrics.horizontalAdvance(header_text) + padding
                    for row in range(row_count):
                        if table.isRowHidden(row):
                            continue
                        index = model.index(row, col)
                        display_val = model.data(index, Qt.ItemDataRole.DisplayRole)
                        display_text = str(display_val) if display_val is not None else ""
                        w = metrics.horizontalAdvance(display_text) + padding
                        if w > content_w:
                            content_w = w
                    max_col_width = max(PATH_COLUMN_DEFAULT_WIDTH, min(content_w, 480))
            else:
                max_col_width = metrics.horizontalAdvance(header_text) + padding

                # 严格使用 DisplayRole 获取展示文本，确保非路径列按实际展示长度测量
                for row in range(row_count):
                    if table.isRowHidden(row):
                        continue
                    index = model.index(row, col)
                    display_val = model.data(index, Qt.ItemDataRole.DisplayRole)
                    display_text = str(display_val) if display_val is not None else ""

                    w = metrics.horizontalAdvance(display_text) + padding
                    if model.data(index, Qt.ItemDataRole.CheckStateRole) is not None:
                        w += 22
                    if w > max_col_width:
                        max_col_width = w

            if resize_columns:
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
                header.resizeSection(col, max_col_width)
            columns_width += max_col_width

    if columns_width <= 0:
        return
    if not resize_window:
        return

    # 预留垂直滚动条宽度、行头宽度、框架边距
    style = table.style() or window.style()
    v_bar_width = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) if style else 16
    v_header = table.verticalHeader()
    v_header_w = v_header.width() if (v_header and v_header.isVisible()) else 0
    frame_w = table.frameWidth() * 2 if hasattr(table, "frameWidth") else 4

    needed_viewport_width = columns_width + v_header_w + v_bar_width + frame_w + extra_padding

    current_viewport_width = table.viewport().width() if table.viewport() else table.width()
    diff = needed_viewport_width - current_viewport_width
    if diff <= 0:
        return

    # 获取当前屏幕可用工作区几何，防止窗口被撑得超出屏幕
    screen = window.screen() or QGuiApplication.primaryScreen()
    avail_geom = screen.availableGeometry() if screen else None
    max_allowed_width = int(avail_geom.width() * 0.95) if avail_geom else 1920

    new_width = min(window.width() + diff, max_allowed_width)
    if new_width > window.width():
        window.resize(new_width, window.height())
        # 若右侧超出屏幕工作区，适度向左平移
        if avail_geom and (window.x() + new_width > avail_geom.right()):
            new_x = max(avail_geom.left(), avail_geom.right() - new_width - 10)
            window.move(new_x, window.y())


# 统一调整表格列宽（严格基于 DisplayRole）并自适应窗口宽度
def resize_table_and_window(table: QAbstractItemView, parent_window: QWidget = None) -> None:
    if not table:
        return
    auto_adjust_window_width(table, parent_window, resize_columns=True)
