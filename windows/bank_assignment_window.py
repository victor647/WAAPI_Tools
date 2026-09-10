import itertools

from data import project_conventions
from libraries.utils.wwise import soundbank_utils, waapi_utils
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem

from libraries.wwise_object import WwiseObjectType
from ui.BankAssignmentMatrix_ui import Ui_BankAssignmentMatrix


# 资源和Bank矩阵分配
class BankAssignmentMatrix(QDialog, Ui_BankAssignmentMatrix):

    def __init__(self, main_window):
        super().__init__()
        self.setupUi(self)
        self.permutations = []
        self.setup_triggers()
        self.__mainWindow = main_window

    def setup_triggers(self):
        self.btnFillWithChildren.clicked.connect(self.get_children_from_selection)
        self.btnAddRow.clicked.connect(lambda: self.tblMatrix.setRowCount(self.tblMatrix.rowCount() + 1))
        self.btnRemoveRow.clicked.connect(lambda: self.tblMatrix.setRowCount(self.tblMatrix.rowCount() - 1))
        self.btnAddColumn.clicked.connect(lambda: self.tblMatrix.setColumnCount(self.tblMatrix.columnCount() + 1))
        self.btnRemoveColumn.clicked.connect(lambda: self.tblMatrix.setColumnCount(self.tblMatrix.columnCount() - 1))
        self.btnCreateBanks.clicked.connect(self.create_banks_by_matrix)
        self.btnAssignMedia.clicked.connect(self.assign_media_to_banks)

    # 从选中对象名称中提取各层级的节点信息填充列表
    def get_children_from_selection(self):
        selection = waapi_utils.get_selected_objects()
        if len(selection) == 0:
            return
        # 节点数量不一致时无法按层级对齐，提示用户后放弃填充
        segment_counts = sorted({len(obj.name.split('_')) for obj in selection})
        if len(segment_counts) > 1:
            counts = '、'.join(str(count) for count in segment_counts)
            QMessageBox.warning(self, 'SoundBank自动分配工具', f'所选对象的节点数量不一致（{counts} 段），已取消填充，请检查对象命名。')
            return
        # 启用缩写规范时第一列放缩写，对象名本身已带缩写前缀的不再重复添加
        acronym = ''
        if project_conventions.has_acronym_convention():
            category = project_conventions.get_object_category(selection[0])
            acronym = project_conventions.convert_category_to_acronym(category)
        # 每一列对应名称中的一个层级，按出现顺序收集该层级去重后的节点名
        name_levels = []
        for obj in selection:
            segments = obj.name.split('_')
            if acronym and segments[0] == acronym:
                segments = segments[1:]
            for index, segment in enumerate(segments):
                if index == len(name_levels):
                    name_levels.append([])
                if segment and segment not in name_levels[index]:
                    name_levels[index].append(segment)
        level_values = ([[acronym]] if acronym else []) + name_levels
        if not level_values:
            return
        self.tblMatrix.setRowCount(0)
        self.tblMatrix.setColumnCount(len(level_values))
        self.tblMatrix.setRowCount(max(len(values) for values in level_values))
        for column, values in enumerate(level_values):
            for row, value in enumerate(values):
                self.tblMatrix.setItem(row, column, QTableWidgetItem(value))

    # 获取所有Bank名称排列组合
    def get_permutations(self):
        all_lists = []
        for column in range(self.tblMatrix.columnCount()):
            row_list = []
            for row in range(self.tblMatrix.rowCount()):
                item = self.tblMatrix.item(row, column)
                if item and item.text() != '':
                    row_list.append(item.text())
            if len(row_list) > 0:
                all_lists.append(row_list)
        self.permutations = list(itertools.product(*all_lists))

    # 根据矩阵内容创建Bank
    def create_banks_by_matrix(self):
        self.get_permutations()
        waapi_utils.begin_undo_group('Bank矩阵批处理')
        for permutation in self.permutations:
            bank_name = self.get_bank_name(permutation)
            # 拆分开关开启时每个组合生成 _Event / _Media 两个Bank，否则只建一个包含全部内容的Bank
            if project_conventions.split_bank_event_media():
                soundbank_utils.create_sound_bank_by_name(bank_name + '_Event')
                soundbank_utils.create_sound_bank_by_name(bank_name + '_Media')
            else:
                soundbank_utils.create_sound_bank_by_name(bank_name)
        waapi_utils.end_undo_group('Bank矩阵批处理')

    # 通过关键字组合获得Bank名称
    @staticmethod
    def get_bank_name(permutation):
        bank_name = permutation[0]
        if len(permutation) >= 2:
            for index in range(1, len(permutation)):
                bank_name += '_' + permutation[index]
        return bank_name

    # 把所有对象添加到选中的bank中（只含media）
    def assign_media_to_banks(self):
        self.get_permutations()
        waapi_utils.begin_undo_group('Assign Bank Media')
        if hasattr(self.__mainWindow, "get_visible_objects"):
            target_objects = self.__mainWindow.get_visible_objects()
        else:
            target_objects = self.__mainWindow.activeObjects
        for obj in target_objects:
            self.iterate_through_children(obj)
        waapi_utils.end_undo_group('Assign Bank Media')

    # 遍历每个子对象
    def iterate_through_children(self, obj):
        children = waapi_utils.get_child_objects(obj)
        for child in children:
            # 找不到就继续往里层找，直到Sound这一级为止
            if not self.find_matching_bank(child) and child.type != WwiseObjectType.Sound:
                self.iterate_through_children(child)

    # 通过比对枚举找到对应的bank
    def find_matching_bank(self, obj):
        # 在每一种排列组合中搜索
        for permutation in self.permutations:
            match = True
            for item in permutation:
                if item.isupper():
                    item = project_conventions.convert_acronym_to_category(item)
                if item not in obj.path:
                    match = False
                    break
            # 找到符合名称的Bank
            if match:
                bank_name = self.get_bank_name(permutation)
                # 拆分开关开启时媒体内容归属对应的 _Media Bank
                if project_conventions.split_bank_event_media():
                    bank_name += '_Media'
                bank = waapi_utils.find_object_by_name_and_type(bank_name, WwiseObjectType.SoundBank)
                # Wwise搜索会包含所有带有关键词的，需要精确搜索
                if bank and bank.name == bank_name:
                    waapi_utils.set_bank_inclusion_object(bank, obj, False, ['media'])
                return True
        # 每一个组合都不符合，在下级继续找
        return False
