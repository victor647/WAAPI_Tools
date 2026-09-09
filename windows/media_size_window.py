from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from libraries.multi_thread import batch_processor
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import soundbank_utils
from libraries.wwise_object import WwiseObject


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
class MediaSizeWindow(QDialog):

    def __init__(self, objects: list[WwiseObject], parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle('媒体资源大小')
        self.resize(820, 560)
        self.__objects = list(objects)
        self.__results = [None] * len(self.__objects)
        self.__table = QTableWidget(0, len(HEADERS))
        self.__table.setHorizontalHeaderLabels(HEADERS)
        self.__table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.__table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.__btnClose = QPushButton('关闭')
        self.__btnClose.clicked.connect(self.accept)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.__btnClose)
        layout = QVBoxLayout(self)
        layout.addWidget(self.__table)
        layout.addLayout(button_row)
        self.__start_measuring()

    # 为每个对象创建一行并异步统计
    def __start_measuring(self):
        self.__table.setRowCount(len(self.__objects))
        for index, obj in enumerate(self.__objects):
            self.__table.setItem(index, 0, QTableWidgetItem(obj.name))
            self.__table.setItem(index, 1, QTableWidgetItem(obj.type.name))
        batch_processor.create_async(
            self.__objects,
            lambda index, obj: self.__measure_object(index, obj),
            '统计媒体资源大小',
            'name',
            on_finished=self.__on_measuring_finished,
        )

    # 工作线程内统计单个对象
    def __measure_object(self, index: int, obj: WwiseObject):
        self.__results[index] = soundbank_utils.get_object_media_size(obj)
        return True

    # 主线程写入结果并追加合计行
    def __on_measuring_finished(self):
        total_wav = 0.0
        total_mem = 0.0
        total_stream = 0.0
        total_stream_files = 0
        total_memory_files = 0
        total_files = 0
        for index, result in enumerate(self.__results):
            if result is None:
                continue
            wav_kb, mem_kb, stream_kb, used_files, stream_files, memory_files = result
            total_wav += wav_kb
            total_mem += mem_kb
            total_stream += stream_kb
            total_stream_files += len(stream_files)
            total_memory_files += len(memory_files)
            total_files += len(used_files)
            total_wem_kb = mem_kb + stream_kb
            self.__table.setItem(index, 2, QTableWidgetItem(str(len(stream_files))))
            self.__table.setItem(index, 3, QTableWidgetItem(str(len(memory_files))))
            self.__table.setItem(index, 4, QTableWidgetItem(str(len(used_files))))
            self.__table.setItem(index, 5, QTableWidgetItem(format_size(wav_kb)))
            ratio_text = format_ratio(wav_kb, total_wem_kb)
            self.__table.setItem(index, 6, QTableWidgetItem(ratio_text))
            self.__table.setItem(index, 7, QTableWidgetItem(format_size(total_wem_kb)))
            self.__table.setItem(index, 8, QTableWidgetItem(format_size(mem_kb)))
            self.__table.setItem(index, 9, QTableWidgetItem(format_size(stream_kb)))
        total_row = self.__table.rowCount()
        self.__table.insertRow(total_row)
        self.__table.setItem(total_row, 0, QTableWidgetItem('合计'))
        self.__table.setItem(total_row, 2, QTableWidgetItem(str(total_stream_files)))
        self.__table.setItem(total_row, 3, QTableWidgetItem(str(total_memory_files)))
        self.__table.setItem(total_row, 4, QTableWidgetItem(str(total_files)))
        self.__table.setItem(total_row, 5, QTableWidgetItem(format_size(total_wav)))
        total_wem = total_mem + total_stream
        total_ratio = format_ratio(total_wav, total_wem)
        self.__table.setItem(total_row, 6, QTableWidgetItem(total_ratio))
        self.__table.setItem(total_row, 7, QTableWidgetItem(format_size(total_wem)))
        self.__table.setItem(total_row, 8, QTableWidgetItem(format_size(total_mem)))
        self.__table.setItem(total_row, 9, QTableWidgetItem(format_size(total_stream)))
        self.__table.resizeColumnsToContents()
        Logger().info(f'媒体资源统计完成，共 {len(self.__objects)} 个对象')
