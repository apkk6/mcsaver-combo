"""麦当劳中国 MCP Server 最小客户端（零第三方依赖，仅 Python 标准库）。

仅用于本地连通性自测与开发调试：完成 MCP 的 initialize 握手、tools/list 枚举
和 tools/call 调用。正式使用请在 WorkBuddy 等 MCP 客户端中配置连接器。

协议：Streamable HTTP + JSON-RPC 2.0，接入地址 https://mcp.mcd.cn
鉴权：请求头 Authorization: Bearer <MCD_MCP_TOKEN>（从环境变量读取，见 .env.example）

2026-10-23 接入实测校正：
- 服务端 initialize 返回 protocolVersion "2025-06-18"（原占位 2025-03-26 已更新）；
- initialize / tools/list / tools/call 均以 application/json 返回；
  SSE（text/event-stream）兜底解析已保留；
- 服务端未下发 Mcp-Session-Id，无状态调用即可跑通。
"""

import itertools
import json
import os
import urllib.error
import urllib.request

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
PROTOCOL_VERSION = "2025-06-18"  # 2026-10-23 实测：服务端 initialize 返回 2025-06-18


class McpError(RuntimeError):
    pass


class McdMcpClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("MCD_MCP_TOKEN", "")
        if not self.token or self.token == "YOUR_MCP_TOKEN":
            raise McpError("未配置 MCD_MCP_TOKEN，请先在 .env 中填入真实 Token")
        self._ids = itertools.count(1)
        self._session_id: str | None = None

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["mcp-session-id"] = self._session_id
        return headers

    def _post(self, payload: dict) -> dict:
        """发送一次 JSON-RPC 请求并返回响应中的 result 字段。"""
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            MCP_URL, data=body, headers=self._headers(), method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
                content_type = resp.headers.get("content-type", "")
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self._session_id = sid
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise McpError("401：Token 无效或已过期，请检查配置")
            if exc.code == 429:
                raise McpError("429：触发限流（600 次/分钟），请降低调用频率")
            raise
        # SSE（text/event-stream）兜底：逐行取最后一条 data: 载荷
        if "text/event-stream" in content_type:
            last = None
            for line in raw.splitlines():
                if line.startswith("data:"):
                    candidate = line[5:].strip()
                    if candidate and candidate != "[DONE]":
                        last = candidate
            data = json.loads(last) if last else {}
        else:
            data = json.loads(raw) if raw.strip() else {}
        if "error" in data:
            raise McpError(f"RPC error: {data['error']}")
        return data.get("result", {})

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": next(self._ids), "method": method}
        if params is not None:
            payload["params"] = params
        return self._post(payload)

    def _notify(self, method: str) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        self._post(payload)

    def initialize(self) -> dict:
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mcsaver-combo-dev", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized")
        return result

    def list_tools(self) -> list[dict]:
        """枚举服务端全部 Tool（含 inputSchema），接入后据此校正各调用参数。"""
        return self._rpc("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict) -> dict:
        return self._rpc("tools/call", {"name": name, "arguments": arguments})


if __name__ == "__main__":
    client = McdMcpClient()
    print(client.initialize())
    for tool in client.list_tools():
        print(tool["name"], "-", tool.get("description", "")[:60])
