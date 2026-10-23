"""麦当劳中国 MCP Server 最小客户端骨架。

仅用于本地连通性自测与开发调试：完成 MCP 的 initialize 握手、tools/list 枚举
和 tools/call 调用。正式使用请在 WorkBuddy 等 MCP 客户端中配置连接器。

协议：Streamable HTTP + JSON-RPC 2.0，接入地址 https://mcp.mcd.cn
鉴权：请求头 Authorization: Bearer <MCD_MCP_TOKEN>（从环境变量读取，见 .env.example）

依赖：pip install httpx
"""

import itertools
import os

import httpx

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
PROTOCOL_VERSION = "2025-03-26"  # TODO: 接入后以服务端 initialize 返回为准校正


class McpError(RuntimeError):
    pass


class McdMcpClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("MCD_MCP_TOKEN", "")
        if not self.token or self.token == "YOUR_MCP_TOKEN":
            raise McpError("未配置 MCD_MCP_TOKEN，请先在 .env 中填入真实 Token")
        self._ids = itertools.count(1)
        self._session_id: str | None = None
        self._client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        payload = {"jsonrpc": "2.0", "id": next(self._ids), "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._client.post(MCP_URL, headers=self._headers(), json=payload)
        if resp.status_code == 401:
            raise McpError("401：Token 无效或已过期，请检查配置")
        if resp.status_code == 429:
            raise McpError("429：触发限流（600 次/分钟），请降低调用频率")
        resp.raise_for_status()
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self._session_id = sid
        # TODO: Streamable HTTP 可能以 SSE（text/event-stream）返回，
        # 接入后若 resp 为 SSE 流，需改为逐行解析 data: 字段提取 JSON-RPC 响应。
        data = resp.json()
        if "error" in data:
            raise McpError(f"RPC error: {data['error']}")
        return data["result"]

    def _notify(self, method: str) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        self._client.post(MCP_URL, headers=self._headers(), json=payload)

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
