#!/usr/bin/env python3
"""生成打包用的「干净默认配置」模板。

打包只带这里生成的模板，不带开发机仓库根目录下的 user_config.json /
ProjectConventions.json，避免把本机的临时设置（主题、窗口尺寸、AI 模型、
工程规范调整等）变成新用户的默认值。

模板内容直接取自代码里的默认值：
  - user_config.json          <- libraries.utils.user_config.DEFAULT_CONFIG
  - ProjectConventions.json   <- data.project_conventions.DEFAULT_CONVENTIONS

用法：python packager/default_configs.py
（package_gui.py 在每次打包前会自动调用，无需手动执行）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGER_DIR = Path(__file__).resolve().parent
ROOT = PACKAGER_DIR.parent
DEFAULTS_DIR = PACKAGER_DIR / "defaults"


# 把代码里的默认值写成打包模板，返回生成的文件路径
def write_default_configs(output_dir: Path = DEFAULTS_DIR) -> list:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from data import project_conventions
    from libraries.utils import user_config

    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, data in (("user_config.json", user_config.DEFAULT_CONFIG),
                       ("ProjectConventions.json", project_conventions.DEFAULT_CONVENTIONS)):
        path = output_dir / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    for path in write_default_configs():
        print(f"已生成默认配置模板: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
