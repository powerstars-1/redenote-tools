from __future__ import annotations

import json
import math
import random
from pathlib import Path
from threading import Lock
from typing import Any

import execjs

from service.app.core.exceptions import ServiceError


def parse_cookie_string(cookie: str) -> dict[str, str]:
    cookie_map: dict[str, str] = {}
    for part in cookie.split(";"):
        chunk = part.strip()
        if not chunk or "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        cookie_map[key.strip()] = value.strip()
    if not cookie_map.get("a1"):
        raise ServiceError(
            code="INVALID_COOKIE",
            message="cookie 缺少 a1 字段，无法完成小红书请求签名。",
            status_code=400,
        )
    return cookie_map


def generate_trace_id(length: int = 16) -> str:
    return "".join("abcdef0123456789"[math.floor(16 * random.random())] for _ in range(length))


class SpiderXHSSigner:
    def __init__(self, node_modules_dir: Path) -> None:
        self._node_modules_dir = node_modules_dir
        self._asset_path = Path(__file__).resolve().parent / "assets" / "xhs_xs_xsc_56.js"
        self._runtime: Any | None = None
        self._lock = Lock()

    def build_request_params(
        self,
        *,
        cookie: str,
        api: str,
        data: dict[str, Any] | str | None = None,
        method: str = "POST",
    ) -> tuple[dict[str, str], dict[str, str], str]:
        cookies = parse_cookie_string(cookie)
        serialized = data if isinstance(data, str) else (data or "")
        headers = self._build_headers(a1=cookies["a1"], api=api, data=serialized, method=method)
        payload = ""
        if isinstance(data, dict) and data:
            payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        elif isinstance(data, str):
            payload = data
        return headers, cookies, payload

    def _build_headers(
        self,
        *,
        a1: str,
        api: str,
        data: dict[str, Any] | str | None,
        method: str,
    ) -> dict[str, str]:
        runtime = self._get_runtime()
        try:
            result = runtime.call("get_request_headers_params", api, data or "", a1, method)
        except Exception as exc:
            raise ServiceError(
                code="INTERNAL_ERROR",
                message="签名脚本执行失败，请检查 Spider_XHS 资源是否兼容当前运行环境。",
                status_code=500,
            ) from exc
        return {
            "authority": "edith.xiaohongshu.com",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
            "cache-control": "no-cache",
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.xiaohongshu.com",
            "pragma": "no-cache",
            "referer": "https://www.xiaohongshu.com/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0"
            ),
            "x-b3-traceid": generate_trace_id(16),
            "x-mns": "unload",
            "x-s": str(result["xs"]),
            "x-s-common": str(result["xs_common"]),
            "x-t": str(result["xt"]),
            "x-xray-traceid": generate_trace_id(32),
        }

    def _get_runtime(self) -> Any:
        if self._runtime is not None:
            return self._runtime
        with self._lock:
            if self._runtime is not None:
                return self._runtime

            crypto_js_path = self._node_modules_dir / "crypto-js"
            if not crypto_js_path.exists():
                raise ServiceError(
                    code="INTERNAL_ERROR",
                    message="未找到 Spider_XHS 的 Node 运行依赖，请先在 service 目录执行 npm install。",
                    status_code=500,
                )

            source = self._asset_path.read_text(encoding="utf-8")
            patched_source = source.replace(
                'require("crypto-js")',
                f"require({json.dumps(crypto_js_path.as_posix())})",
                1,
            )
            # Spider_XHS 的脚本里包含少量 Unicode 混淆标识符，Windows 下经 execjs 透传时
            # 可能被错误编码，导致 Node 在运行期直接报语法错误。
            patched_source = patched_source.replace("globalThis.Ιnfinity", "globalThis.IotaInfinity")
            patched_source = patched_source.replace("globalThis.Ιnk", "globalThis.IotaInk")
            try:
                self._runtime = execjs.compile(patched_source)
            except execjs.RuntimeUnavailableError as exc:
                raise ServiceError(
                    code="INTERNAL_ERROR",
                    message="当前环境未检测到可用的 Node.js 运行时。",
                    status_code=500,
                ) from exc
            return self._runtime
