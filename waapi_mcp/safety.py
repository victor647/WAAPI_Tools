# MCP 危险工具确认门：需要显式传入 confirmed=True 才允许执行。
# MCP 协议本身没有人类确认机制，这里用“必须显式传参”的方式防止模型/脚本误触发。
from __future__ import annotations


def require_confirmation(confirmed: bool) -> None:
    if not confirmed:
        raise ValueError(
            "危险操作被拦截：请显式传入 confirmed=True 确认执行"
        )
