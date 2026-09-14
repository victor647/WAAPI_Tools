# 从 Wwise SDK 帮助文档（.chm）生成 libraries/wwise_object_properties.py。
#
# 用法（在仓库根目录执行）：
#   python .agents/skills/wwise-waapi/scripts/gen_object_properties.py
#   python .agents/skills/wwise-waapi/scripts/gen_object_properties.py --chm <路径> --output <路径>
#
# 数据来自文档的 "Wwise Objects Reference"（每个对象类型一页）与
# ak.wwise.core.object.get 的内置访问器列表，换 Wwise 版本后重新执行即可。
import argparse
import html
import os
import re
import subprocess
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_CHM = Path(r"G:\H74\Sound\Wwise_2023.1.18.8899\SDK\Help\WwiseSDK-Windows.chm")
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_OUTPUT = REPO_ROOT / "libraries" / "wwise_object_properties.py"

# 插件详情页的文件名前缀 -> 这些插件在 WAAPI 里共用的宿主类型名
PLUGIN_HOST_TYPES = (("effect_", "effect"), ("source_", "sourceplugin"))

# WAQL 里可写在 return 中的对象表达式，文档没有和内置访问器列在同一张表里
WAQL_OBJECT_EXPRESSIONS = (
    "children descendants ancestors referencesTo this owner workunit parent "
    "activeSource randomizer validity duration loudness audioSourceTrimValues "
    "maxDurationSource maxDurationSourceObject maxRadiusAttenuation maxRadiusAttenuationObject "
    "audioSourceLanguage switchContainerChildContext musicTransitionRoot musicPlaylistRoot "
    "nodeType mediaId conversionHash contentHash"
).split()

INDEX_ENTRY = re.compile(r'<a class="el" href="(wwiseobject_[^"]+?)\.html">([^<]+)</a>')
ACCESSOR_ITEM = re.compile(r"<li>\s*([^<]+?)\s*</li>")
VERSION_IN_PATH = re.compile(r"(\d{4}\.\d+(?:\.\d+)*)")


class DocTableParser(HTMLParser):
    # 只收集最外层 class="doxtable" 表格的行，表格内嵌套的取值表不参与
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.row = None
        self.cell = None
        self.rows = []

    @property
    def in_root_table(self):
        return bool(self.stack) and self.stack[-1]

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            is_root = dict(attrs).get("class") == "doxtable" and not any(self.stack)
            self.stack.append(is_root)
        elif tag == "tr" and self.in_root_table:
            self.row = []
        elif tag in ("td", "th") and self.row is not None and self.in_root_table:
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            if self.stack:
                self.stack.pop()
        elif tag == "tr" and self.row is not None and self.in_root_table:
            self.rows.append(self.row)
            self.row = None
        elif tag in ("td", "th") and self.cell is not None and self.in_root_table:
            self.row.append(re.sub(r"\s+", " ", "".join(self.cell)).strip())
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def decompile_chm(chm_path: Path, work_dir: Path) -> Path:
    out_dir = work_dir / "chm"
    out_dir.mkdir(parents=True, exist_ok=True)
    hh_exe = Path(os.environ.get("WINDIR", r"C:\Windows")) / "hh.exe"
    subprocess.Popen([str(hh_exe), "-decompile", str(out_dir), str(chm_path)])
    # hh.exe 立即返回，只能靠文件数稳定来判断解包结束
    deadline = time.time() + 600
    last_count = -1
    stable_rounds = 0
    while time.time() < deadline:
        time.sleep(1)
        count = len(list(out_dir.glob("*.html")))
        if count and count == last_count:
            stable_rounds += 1
            if stable_rounds >= 3:
                break
        else:
            stable_rounds = 0
        last_count = count
    if not (out_dir / "wobjects_index.html").exists():
        raise RuntimeError(f"解包失败，未找到 wobjects_index.html：{chm_path}")
    return out_dir


def parse_page_names(page_path: Path) -> list:
    parser = DocTableParser()
    parser.feed(read_text(page_path))
    return [row[0] for row in parser.rows[1:] if len(row) >= 8 and row[0]]


def parse_index(index_path: Path) -> dict:
    # 返回 {页面名: 文档中给出的类型名}，插件页的类型名是插件显示名，只用于识别页面
    return {stem: html.unescape(name).strip() for stem, name in INDEX_ENTRY.findall(read_text(index_path))}


def parse_builtin_accessors(get_page_path: Path) -> list:
    text = read_text(get_page_path)
    marker = text.find("built-in accessors")
    if marker < 0:
        raise RuntimeError(f"未在 {get_page_path.name} 中找到内置访问器列表")
    start = text.find("<ul>", marker)
    end = text.find("</ul>", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"未在 {get_page_path.name} 中解析出内置访问器列表")
    names = []
    for raw in ACCESSOR_ITEM.findall(text[start:end]):
        name = html.unescape(raw).strip()
        if name:
            names.append(name)
    return names


def collect_pages(chm_dir: Path) -> tuple:
    index = parse_index(chm_dir / "wobjects_index.html")
    type_names: dict = {}
    plugin_names: dict = {}
    for stem, doc_name in index.items():
        page_path = chm_dir / f"{stem}.html"
        if not page_path.exists():
            continue
        names = parse_page_names(page_path)
        page_stem = stem.removeprefix("wwiseobject_")
        host = next((host for prefix, host in PLUGIN_HOST_TYPES if page_stem.startswith(prefix)), None)
        if host is None:
            type_names[doc_name.lower()] = {name.lower() for name in names}
        else:
            plugin_names.setdefault(host, set()).update(name.lower() for name in names)
    # 插件宿主类型（Effect / SourcePlugin）在 WAAPI 里只有通用属性，把同族插件属性并进来
    for host, names in plugin_names.items():
        type_names.setdefault(host, set()).update(names)
    return type_names, plugin_names


def normalize_accessors(names: list) -> set:
    normalized = set()
    for name in names:
        normalized.add(name.lower())
        if ":" in name:
            normalized.add(name.split(":", 1)[1].lower())
    return normalized


def wrap_names(names: list, indent: str, width: int = 104) -> str:
    lines = []
    current = ""
    for name in names:
        if current and len(current) + 1 + len(name) > width:
            lines.append(current)
            current = name
        else:
            current = f"{current} {name}".strip()
    if current:
        lines.append(current)
    return "\n".join(f'{indent}"{line} "' for line in lines)


def render_module(source_version: str, builtin: list, type_names: dict) -> str:
    out = [
        "# 本文件由脚本生成，请勿手工修改。",
        "# 数据来源：Wwise SDK 帮助文档 WwiseSDK-Windows.chm 的 \"Wwise Objects Reference\" 与",
        "#          ak.wwise.core.object.get 的内置访问器列表。",
        "# 生成脚本：.agents/skills/wwise-waapi/scripts/gen_object_properties.py",
        f"# 文档版本：{source_version}",
        "#",
        "# 用途：不向 Wwise 发请求就判断某个对象类型上是否存在某个属性/引用/列表（名称不区分大小写）。",
        "",
        f'SOURCE_VERSION = "{source_version}"',
        "",
        "# 与对象类型无关的内置访问器（ak.wwise.core.object.get 的 return 可用名）",
        "BUILTIN_ACCESSORS = frozenset((",
        wrap_names(builtin, "    "),
        ").split())",
        "",
        "# 对象类型（小写）-> 该类型可用的属性/引用/列表（小写）；Effect 与 SourcePlugin 已并入同族插件属性",
        "TYPE_PROPERTIES = {",
    ]
    for type_name in sorted(type_names):
        names = sorted(type_names[type_name])
        if not names:
            out.append(f'    "{type_name}": frozenset(),')
            continue
        out.append(f'    "{type_name}": frozenset((')
        out.append(wrap_names(names, "        "))
        out.append("    ).split()),")
    out.append("}")
    out.append("")
    return "\n".join(out)


def detect_version(chm_path: Path) -> str:
    for part in reversed(chm_path.parts):
        match = VERSION_IN_PATH.search(part)
        if match:
            return match.group(1)
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="由 Wwise SDK 帮助文档生成对象属性表")
    parser.add_argument("--chm", type=Path, default=DEFAULT_CHM, help="WwiseSDK-Windows.chm 路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="生成的 python 文件路径")
    parser.add_argument("--version", default="", help="写入文件的文档版本号，默认从 chm 路径推断")
    args = parser.parse_args()

    if not args.chm.exists():
        print(f"找不到 chm 文件：{args.chm}")
        return 1

    with tempfile.TemporaryDirectory(prefix="wwise_chm_") as temp_dir:
        chm_dir = decompile_chm(args.chm, Path(temp_dir))
        type_names, plugin_names = collect_pages(chm_dir)
        builtin = sorted(normalize_accessors(parse_builtin_accessors(chm_dir / "ak_wwise_core_object_get.html")))
        builtin = sorted(set(builtin) | {name.lower() for name in WAQL_OBJECT_EXPRESSIONS})
        content = render_module(args.version or detect_version(args.chm), builtin, type_names)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    property_count = sum(len(names) for names in type_names.values())
    print(f"已写入 {args.output}")
    print(f"类型 {len(type_names)} 个，属性/引用/列表条目 {property_count} 条，内置访问器 {len(builtin)} 个")
    print(f"插件宿主：{ {host: len(names) for host, names in plugin_names.items()} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
