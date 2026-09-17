from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTableView, QVBoxLayout, QWidget

from libraries.multi_thread import batch_processor
from libraries.table_view.table_facade import TableFacade
from libraries.utils.log_utils import Logger
from libraries.utils.wwise import soundbank_utils, waapi_utils
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
        self.resize(1100, 430)
        self.__objects = list(objects)
        # 每个根对象一个累加器；批处理按展开后的所有节点推进（进度条总数=节点数）
        self.__stats = [soundbank_utils.MediaSizeNodeStatistics() for _ in self.__objects]
        self.__nodes: list[WwiseObject] = []
        self.__node_root: list[int] = []
        self.__table_view = QTableView(self)
        self.__table = TableFacade(
            self.__table_view,
            headers=HEADERS,
            sorting_enabled=True,
            pinned_bottom_count=1,
        )
        self.__table_view.doubleClicked.connect(self.__on_table_double_clicked)
        self.__btnClose = QPushButton('关闭')
        self.__btnClose.clicked.connect(self.accept)
        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self.__btnClose)
        layout = QVBoxLayout(self)
        layout.addWidget(self.__table_view)
        layout.addLayout(button_row)
        self.__start_measuring()

    # 双击某行在 Wwise 中选中对应对象
    def __on_table_double_clicked(self, index):
        source_row = self.__table.get_source_row(index)
        if 0 <= source_row < len(self.__objects):
            waapi_utils.select_objects_in_wwise([self.__objects[source_row]])

    # 为每个对象创建一行并异步统计
    def __start_measuring(self):
        self.__table.clear()
        for obj in self.__objects:
            self.__table.append_row_values([obj.name, obj.type.name, '', '', '', '', '', '', '', ''])
        self.__table.on_table_filled()
        seen_ids: set[str] = set()
        for root_index, obj in enumerate(self.__objects):
            for node in [obj] + waapi_utils.get_child_objects(obj, True):
                if not node.id or node.id in seen_ids:
                    continue
                seen_ids.add(node.id)
                self.__nodes.append(node)
                self.__node_root.append(root_index)
        batch_processor.create_async(
            self.__nodes,
            lambda index, obj: self.__measure_node(index, obj),
            '统计媒体资源大小',
            'name',
            on_finished=self.__on_measuring_finished,
        )

    # 工作线程内累加单个节点到所属根对象
    def __measure_node(self, index: int, obj: WwiseObject):
        self.__stats[self.__node_root[index]].accumulate(obj)
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
        Logger().info(f'媒体资源统计完成，共 {len(self.__objects)} 个对象')
