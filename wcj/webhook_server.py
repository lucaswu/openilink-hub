#!/usr/bin/env python3
"""
本地 Webhook 接收服务器（多账号·配置文件版）

所有账号共用同一个 Webhook URL，通过 payload 中的 channel_id 自动路由到对应账号。
账号配置写在 accounts.json，修改后无需重启（热重载）。

accounts.json 格式:
  {
    "账号名称1": { "channel_id": "xxx", "api_key": "yyy" },
    "账号名称2": { "channel_id": "xxx", "api_key": "yyy" }
  }

启动示例:
  python3 webhook_server.py --api-url http://localhost:9800

所有账号的 Webhook URL 统一填:
  http://host.docker.internal:5000/
"""

import json
import hmac
import hashlib
import argparse
import os
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


# ---- 运行时配置（由 main() 填入） ----
HMAC_SECRET  = ""
BEARER_TOKEN = ""
HUB_API_URL  = ""
CONFIG_FILE  = "accounts.json"

# 账号映射缓存: { channel_id: {"name": str, "api_key": str} }
_accounts_cache: dict[str, dict] = {}
_accounts_mtime: float = 0.0


# ------------------------------------------------------------------ #
#  配置文件热重载                                                      #
# ------------------------------------------------------------------ #

def _load_accounts() -> dict[str, dict]:
    """读取 accounts.json，文件未修改时直接返回缓存。

    文件格式:
      {
        "账号名称": { "channel_id": "xxx", "api_key": "yyy" },
        ...
      }
    内部转成 { channel_id: {"name": ..., "api_key": ...} } 便于快速查找。
    """
    global _accounts_cache, _accounts_mtime
    try:
        mtime = os.path.getmtime(CONFIG_FILE)
    except FileNotFoundError:
        return _accounts_cache

    if mtime != _accounts_mtime:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        _accounts_cache = {
            entry["channel_id"]: {"name": name, "api_key": entry["api_key"]}
            for name, entry in raw.items()
        }
        _accounts_mtime = mtime
        print(f"[配置] 已加载 {CONFIG_FILE}，共 {len(_accounts_cache)} 个账号")
    return _accounts_cache


def get_account(channel_id: str) -> dict | None:
    """根据 channel_id 返回 {"name": ..., "api_key": ...}，未找到返回 None。"""
    return _load_accounts().get(channel_id)


# ------------------------------------------------------------------ #
#  回复发送                                                            #
# ------------------------------------------------------------------ #

def send_reply(recipient: str, text: str, channel_key: str):
    """向指定用户发送文本回复。"""
    if not HUB_API_URL or not channel_key:
        print("  [回复] 未配置 api_key，跳过发送")
        return

    url = f"{HUB_API_URL}/api/v1/channels/send?key={channel_key}"
    body = json.dumps({"recipient": recipient, "text": text}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            print(f"  [回复] -> {recipient!r}  响应: {result}")
    except Exception as e:
        print(f"  [回复] 发送失败: {e}")


# ------------------------------------------------------------------ #
#  消息处理（在这里写你的业务逻辑）                                      #
# ------------------------------------------------------------------ #

def on_message(payload: dict, channel_key: str):
    """收到消息时调用。默认行为：回显收到的文本内容。"""
    sender  = payload.get("sender", "")
    content = payload.get("content", "")
    if not sender:
        return

    reply_text = f"收到你的消息：{content}" if content else "收到消息（无文本内容）"
    send_reply(sender, reply_text, channel_key)


# ------------------------------------------------------------------ #
#  HTTP 服务器                                                         #
# ------------------------------------------------------------------ #

def _verify_hmac(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)

        # 认证校验
        if HMAC_SECRET:
            sig = self.headers.get("X-Hub-Signature", "")
            if not _verify_hmac(raw, sig, HMAC_SECRET):
                self._respond(401, {"error": "HMAC mismatch"})
                print("[AUTH FAIL] HMAC 校验失败")
                return

        if BEARER_TOKEN:
            if self.headers.get("Authorization", "") != f"Bearer {BEARER_TOKEN}":
                self._respond(401, {"error": "Invalid token"})
                print("[AUTH FAIL] Bearer token 校验失败")
                return

        try:
            payload = json.loads(raw.decode())
        except json.JSONDecodeError as e:
            self._respond(400, {"error": str(e)})
            return

        # 通过 payload 中的 channel_id 找到对应账号
        channel_id = payload.get("channel_id", "")
        account    = get_account(channel_id)
        if account is None:
            # 未知账号：仍然 200，但打印警告（避免 hub 重试）
            self._respond(200, {"ok": True, "warn": "unknown channel_id"})
            print(f"[未知] channel_id={channel_id!r} 不在 {CONFIG_FILE} 中，已忽略")
            return

        # 先返回 200，再处理（避免超时）
        self._respond(200, {"ok": True})
        self._print_message(payload, account["name"])
        on_message(payload, account["api_key"])

    def _respond(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _print_message(self, p: dict, account_name: str = ""):
        ts       = p.get("timestamp", 0)
        time_str = datetime.fromtimestamp(ts / 1000).strftime("%H:%M:%S") if ts else "?"
        print(f"\n{'='*60}")
        print(f"  [{time_str}] 账号: {account_name}  seq: {p.get('seq_id','?')}")
        print(f"  发送者: {p.get('sender','?')}  类型: {p.get('msg_type','?')}")
        print(f"  内容: {p.get('content','') or '(空)'}")
        for i, item in enumerate(p.get("items", [])):
            itype = item.get("type", "?")
            parts = [f"type={itype}"]
            if item.get("text"):      parts.append(f"text={item['text']!r}")
            if item.get("file_name"): parts.append(f"file={item['file_name']}")
            if item.get("media_url"): parts.append(f"url={item['media_url']}")
            print(f"    item[{i}] " + "  ".join(parts))
        print(f"{'='*60}")


# ------------------------------------------------------------------ #
#  入口                                                                #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="openilink-hub 本地 Webhook 服务器（配置文件版）")
    parser.add_argument("--host",         default="0.0.0.0",              help="监听地址")
    parser.add_argument("--port",         type=int, default=5000,          help="监听端口 (默认 5000)")
    parser.add_argument("--hmac-secret",  default="",                      help="HMAC secret")
    parser.add_argument("--bearer-token", default="",                      help="Bearer token")
    parser.add_argument("--api-url",      default="http://localhost:9800",  help="hub 地址")
    parser.add_argument("--config",       default="accounts.json",          help="账号配置文件路径 (默认 accounts.json)")
    args = parser.parse_args()

    global HMAC_SECRET, BEARER_TOKEN, HUB_API_URL, CONFIG_FILE
    HMAC_SECRET  = args.hmac_secret
    BEARER_TOKEN = args.bearer_token
    HUB_API_URL  = args.api_url.rstrip("/")
    CONFIG_FILE  = args.config

    # 如果配置文件不存在，自动创建示例
    if not os.path.exists(CONFIG_FILE):
        example = {
            "账号名称1": {"channel_id": "<channel_id_1>", "api_key": "<api_key_1>"},
            "账号名称2": {"channel_id": "<channel_id_2>", "api_key": "<api_key_2>"},
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(example, f, indent=2, ensure_ascii=False)
        print(f"[配置] 已生成示例文件 {CONFIG_FILE}，请填入真实的 channel_id 和 api_key")

    _load_accounts()

    server = HTTPServer((args.host, args.port), WebhookHandler)
    print(f"Webhook 服务器已启动: http://{args.host}:{args.port}")
    print(f"所有账号统一 Webhook URL: http://host.docker.internal:{args.port}/")
    print(f"账号配置文件: {os.path.abspath(CONFIG_FILE)}（修改后自动热重载，无需重启）")
    print("等待消息...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == "__main__":
    main()
