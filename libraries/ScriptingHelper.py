import fnmatch
import re

from ObjectTools import CommonTools


# 根据条件筛选或筛除列表中对象
def filter_objects(objects: list, filter_input: str,
                   case_sensitive: bool, match_whole_word: bool, use_regular_expression: bool,
                   filter_type: str, filter_by_name: bool, inclusion: bool) -> list:
    objects_filtered = []
    for obj in objects:
        if not obj or filter_type != '全部类型' and obj['type'] != filter_type:
            continue
        match = False

        obj_key = obj['name'] if filter_by_name else obj['path']
        # 查找*和?
        if fnmatch.fnmatch(obj_key, filter_input):
            match = True
        else:
            filter_input_for_match = filter_input if case_sensitive else filter_input.lower()
            obj_key = obj_key if case_sensitive else obj_key.lower()

            if match_whole_word:
                if filter_input_for_match == obj_key:
                    match = True
            elif use_regular_expression:
                filter_input_for_match = trans_to_regular_expression(filter_input_for_match)
                try:
                    if re.search(filter_input_for_match, obj_key):
                        match = True
                except:
                    print("regular match except")
            else:
                if filter_input_for_match in obj_key:
                    match = True

        if (inclusion and match) or (not inclusion and not match):
            objects_filtered.append(obj)

    return objects_filtered


# 在对象中筛选未启用的
def filter_objects_by_inclusion(objects: list, inclusion: bool) -> list:
    objects_filtered = []
    for obj in objects:
        included = CommonTools.is_object_included(obj)
        if inclusion == included:
            objects_filtered.append(obj)
    return objects_filtered


# 在对象中筛选特定类型的
def filter_objects_by_type(objects: list, filter_type: str) -> list:
    if filter_type == 'All':
        return objects
    remaining_objects = [obj for obj in objects if obj['type'] == filter_type]
    return remaining_objects


# 简化以支持正则表达式:
# 1. 支持&
def trans_to_regular_expression(text: str) -> str:
    # 去空格
    text.replace(' ', '')
    # 处理&
    idx = text.find('&')
    if idx != -1:
        try:
            idx_left_begin = idx_left_end = idx - 1
            idx_right_begin = idx_right_end = idx + 1
            # 获取&左侧的字符串下标范围
            column_right_count = 0
            while idx_left_begin > 0:
                c = text[idx_left_begin]
                if c == ')':
                    column_right_count += 1
                if c == '(':
                    column_right_count -= 1
                if (c in ")*|") and (column_right_count == 0):
                    idx_left_begin += 1
                    break
                idx_left_begin -= 1
            # 获取&右侧的字符串下标范围
            column_left_count = 0
            while idx_right_end < len(text)-1:
                c = text[idx_right_end]
                if c == ')':
                    column_left_count -= 1
                if c == '(':
                    column_left_count += 1
                if (c in "(*|") and (column_left_count == 0):
                    break
                idx_right_end += 1
            # 替换字符串
            idx_increment = 0
            str_list = list(text)
            str_list.insert(idx_left_begin + idx_increment, "(?=.*")
            idx_increment += 1
            str_list.insert(idx_left_end + idx_increment + 1, ")")
            idx_increment += 1
            str_list.pop(idx + idx_increment)
            idx_increment += -1
            str_list.insert(idx_right_begin + idx_increment, "(?=.*")
            idx_increment += 1
            str_list.insert(idx_right_end + idx_increment + 1, ")")
            text = ''.join(str_list)
            # 继续处理一下个&
            text = trans_to_regular_expression(text)
        except:
            print("trans_to_regular_expression error")
    return text
