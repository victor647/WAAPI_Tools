# 单实例转发：Wwise 右键菜单反复打开工具时，把对象列表交给已运行的主窗口，而不是再起一个进程。
# 用 QLocalServer / QLocalSocket（Windows 下是命名管道），不引入额外依赖，打包时随 QtNetwork 一起带上。
from __future__ import annotations

import json
import time
from typing import Callable, Optional

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from libraries.utils.log_utils import Logger

# 握手超时：确认没有实例在监听要尽量快，避免拖慢正常启动
CONNECT_TIMEOUT_MS = 500
# 单条消息读写超时（按行分隔，正常一次写完）
WRITE_TIMEOUT_MS = 1000


def encode_payload(object_ids: list, from_wwise: bool) -> str:
    # 转发内容与控制台参数保持同一语义：有 GUID 用 GUID，否则让主实例去读当前选中
    return json.dumps(
        {"object_ids": [str(i) for i in (object_ids or [])], "from_wwise": bool(from_wwise)},
        ensure_ascii=False,
    )


def decode_payload(payload: str) -> Optional[dict]:
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def forward_to_running_instance(server_name: str, payload: str) -> bool:
    # 已有实例在监听则转发并返回 True；没有实例（或转发失败）返回 False，由调用方作为主实例启动
    socket = QLocalSocket()
    socket.connectToServer(server_name)
    if not socket.waitForConnected(CONNECT_TIMEOUT_MS):
        return False
    try:
        socket.write(payload.encode("utf-8") + b"\n")
        _flush_socket(socket)
    except Exception as e:
        Logger().warning(f"向已运行的工具窗口转发失败：{e}")
        return False
    finally:
        socket.disconnectFromServer()
    return True


def _flush_socket(socket: QLocalSocket) -> None:
    # Qt 的本地套接字写入是异步的：必须把缓冲区真正送出去再断开，
    # 否则本函数返回后 socket 被回收，接收方只会看到一个空连接（表现为"转发成功但没反应"）
    app = QCoreApplication.instance()
    deadline = time.monotonic() + WRITE_TIMEOUT_MS / 1000
    while socket.bytesToWrite() > 0 and time.monotonic() < deadline:
        if app is not None:
            app.processEvents()
        socket.waitForBytesWritten(50)


class SingleInstanceServer:
    # 主实例的本地监听：收到其它实例转发的消息后在 GUI 线程回调
    def __init__(self, server_name: str):
        self._server_name = server_name
        self._on_message: Callable[[str], None] = lambda _payload: None
        self._server: Optional[QLocalServer] = None
        self._buffers: dict = {}

    @property
    def is_listening(self) -> bool:
        return self._server is not None

    def start(self, on_message: Callable[[str], None]) -> bool:
        self._on_message = on_message
        server = QLocalServer()
        # 监听失败不影响正常使用，只是失去"转发到已有窗口"的能力
        if not server.listen(self._server_name):
            Logger().warning(f"单实例监听失败，本次按普通启动处理：{server.errorString()}")
            return False
        server.newConnection.connect(self._on_new_connection)
        self._server = server
        return True

    def _on_new_connection(self):
        while self._server is not None and self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            self._buffers[socket] = b""
            socket.readyRead.connect(lambda s=socket: self._on_ready_read(s))
            socket.disconnected.connect(lambda s=socket: self._drop_connection(s))
            # 转发方写完就断开，数据可能已经到达：先主动读一次，避免错过已经发出的 readyRead
            self._on_ready_read(socket)

    def _on_ready_read(self, socket):
        try:
            chunk = bytes(socket.readAll())
        except RuntimeError:
            # 连接对象的 C++ 侧已被 Qt 回收（对方断开后立即释放）
            return
        buffer = self._buffers.get(socket, b"") + chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            payload = line.decode("utf-8", errors="replace").strip()
            if payload:
                self._on_message(payload)
        self._buffers[socket] = buffer

    def _drop_connection(self, socket):
        # 断开时可能还有未读数据（对方写完后立即关闭连接）
        try:
            self._on_ready_read(socket)
        except RuntimeError:
            pass
        self._buffers.pop(socket, None)
        socket.deleteLater()
