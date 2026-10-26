import json
import csv
import xml.etree.ElementTree as ElementTree
from pathlib import Path

from libraries.utils.log_utils import Logger


# 延迟导入 Qt 文件对话框：MCP / AI 等无界面场景 import io_utils 时无需加载 PySide6
def _get_qfiledialog():
    from PySide6.QtWidgets import QFileDialog

    return QFileDialog

# 从json文件导入
def import_from_json():
    file_path = _get_qfiledialog().getOpenFileName(filter='JSON(*.json)')
    if file_path[0] == '':
        return None
    file = open(file_path[0], 'r')
    return json.load(file)


# 导出到json文件
def export_to_json(json_obj, file_name: str):
    file_path = _get_qfiledialog().getSaveFileName(filter='JSON(*.json)', dir=file_name)
    if file_path[0] == '':
        return
    file = open(file_path[0], 'w')
    file.write(json.dumps(json_obj, indent=2))


# 把数据写入指定路径的 JSON 文件（UTF-8、保留中文），失败时记录日志并返回 False
def export_to_json_path(json_obj, file_path: str) -> bool:
    try:
        Path(file_path).write_text(
            json.dumps(json_obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        return True
    except (OSError, TypeError, ValueError) as e:
        Logger().error(f"写入 JSON 文件失败：{file_path} ({e})")
        return False


# 导出二维数组到csv文件
def export_to_csv(data: list, file_name: str):
    file_path = _get_qfiledialog().getSaveFileName(filter='CSV(*.csv)', dir=file_name)
    if file_path[0] == '':
        return
    file = open(file_path[0], mode='w', newline='')
    writer = csv.writer(file)
    writer.writerows(data)


# 把二维数组写入指定路径的 CSV（UTF-8 BOM，便于 Excel 直接识别中文）
def export_to_csv_path(data: list, file_path: str) -> bool:
    try:
        with open(file_path, mode="w", encoding="utf-8-sig", newline="") as file:
            writer = csv.writer(file)
            writer.writerows(data)
        return True
    except (OSError, UnicodeError) as e:
        Logger().error(f"写入 CSV 文件失败：{file_path} ({e})")
        return False


# 导出一维数据到txt文件
def export_to_txt(data: list, file_name: str):
    file_path = _get_qfiledialog().getSaveFileName(filter='TXT(*.txt)', dir=file_name)
    if file_path[0] == '':
        return
    file = open(file_path[0], mode='w')
    file.write('\n'.join(str(line) for line in data))


# 从csv文件导入
def import_from_csv():
    file_path = _get_qfiledialog().getOpenFileName(filter='CSV(*.csv)')
    if file_path[0] == '':
        return None
    file = open(file_path[0], 'r')
    return list(csv.reader(file))


# 从txt文件导入（每行一条数据）
def import_from_txt():
    file_path = _get_qfiledialog().getOpenFileName(filter='TXT(*.txt)')
    if file_path[0] == '':
        return None
    file = open(file_path[0], mode='r', encoding='utf-8')
    return [line.rstrip('\n') for line in file]


# 从xml或WorkUnit文件导入
def import_from_xml(extension='xml'):
    file_path = _get_qfiledialog().getOpenFileName(filter=f'XML(*.{extension})')
    if file_path[0] == '':
        return None, None
    tree = ElementTree.parse(file_path[0])
    root = tree.getroot()
    return root, file_path[0]
