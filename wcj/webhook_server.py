#!/usr/bin/env python3
"""
本地 Webhook 接收服务器
用于接收 openilink-hub 转发的消息，并可将回复发回给发送者。

收到消息后调用 on_message(payload) 处理，默认回显消息内容。

启动示例:
  python3 webhook_server.py --api-url http://localhost:9800 --api-key YOUR_KEY
"""

import json
import hmac
import hashlib
import argparse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


# ---- 运行时配置（由 main() 填入） ----
HMAC_SECRET  = ""
BEARER_TOKEN = ""
HUB_API_URL  = ""   # e.g. http://localhost:9800
CHANNEL_KEY  = ""   # channel api_key，用于发送回复


# ------------------------------------------------------------------ #
#  回复发送                                                            #
# ------------------------------------------------------------------ #

def send_reply(recipient: str, text: str):
    """向指定用户发送文本回复。"""
    if not HUB_API_URL or not CHANNEL_KEY:
        print("  [回复] 未配置 --api-url / --api-key，跳过发送")
        return

    url = f"{HUB_API_URL}/api/v1/channels/send?key={CHANNEL_KEY}"
    body = json.dumps({"recipient": recipient, "text": text}).encode()
    req = urllib.request.Request(
        url,
        data=body,
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

def on_message(payload: dict):
    """收到消息时调用。默认行为：回显收到的文本内容。"""
    sender  = payload.get("sender", "")
    content = payload.get("content", "")
    if not sender:
        return

    reply_text = f"收到你的消息：{content}" if content else "收到消息（无文本内容）"
    send_reply(sender, reply_text)


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

        # 先返回 200，再处理（避免超时）
        self._respond(200, {"ok": True})
        self._print_message(payload)
        on_message(payload)

    def _respond(self, status: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _print_message(self, p: dict):
        ts       = p.get("timestamp", 0)
        time_str = datetime.fromtimestamp(ts / 1000).strftime("%H:%M:%S") if ts else "?"
        print(f"\n{'='*60}")
        print(f"  [{time_str}] 频道: {p.get('channel_id','?')[:8]}  seq: {p.get('seq_id','?')}")
        print(f"  发送者: {p.get('sender','?')}  类型: {p.get('msg_type','?')}")
        print(f"  内容: {p.get('content','') or '(空)'}")
        for i, item in enumerate(p.get("items", [])):
            itype = item.get("type", "?")
            parts = [f"type={itype}"]
            if item.get("text"):   parts.append(f"text={item['text']!r}")
            if item.get("file_name"): parts.append(f"file={item['file_name']}")
            if item.get("media_url"): parts.append(f"url={item['media_url']}")
            print(f"    item[{i}] " + "  ".join(parts))
        print(f"{'='*60}")


# ------------------------------------------------------------------ #
#  入口                                                                #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="openilink-hub 本地 Webhook 服务器")
    parser.add_argument("--host",         default="0.0.0.0",             help="监听地址")
    parser.add_argument("--port",         type=int, default=5000,         help="监听端口 (默认 5000)")
    parser.add_argument("--hmac-secret",  default="",                     help="HMAC secret")
    parser.add_argument("--bearer-token", default="",                     help="Bearer token")
    parser.add_argument("--api-url",      default="http://localhost:9800", help="hub 地址 (默认 http://localhost:9800)")
    parser.add_argument("--api-key",      default="",                     help="channel api_key，用于发送回复")
    args = parser.parse_args()

    global HMAC_SECRET, BEARER_TOKEN, HUB_API_URL, CHANNEL_KEY
    HMAC_SECRET  = args.hmac_secret
    BEARER_TOKEN = args.bearer_token
    HUB_API_URL  = args.api_url.rstrip("/")
    CHANNEL_KEY  = args.api_key

    server = HTTPServer((args.host, args.port), WebhookHandler)
    print(f"Webhook 服务器已启动: http://{args.host}:{args.port}")
    print(f"Webhook URL 填入:  http://host.docker.internal:{args.port}/")
    if CHANNEL_KEY:
        print(f"回复接口:          {HUB_API_URL}/api/v1/channels/send")
    else:
        print("未配置 --api-key，收到消息后不会自动回复")
    print("等待消息...\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")


if __name__ == "__main__":
    main()
