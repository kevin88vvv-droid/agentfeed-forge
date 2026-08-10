#!/usr/bin/env python3
"""AgentFeed Forge Free: validate one digital-product JSON file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


VERSION = "0.1.0"
REQUIRED = ("id", "title", "description", "link", "image_link", "availability", "price", "currency", "brand")
AVAILABILITY = {"in_stock", "out_of_stock", "preorder", "backorder"}
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{16,}\b", re.I),
)
PRIVATE_PATHS = (re.compile(r"/(?:Users|home)/[^/\s]+/"), re.compile(r"\b[A-Za-z]:\\Users\\[^\\\s]+\\"))


def iter_strings(value, path="$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from iter_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")


def validate(product):
    issues = []
    product_id = str(product.get("id") or "#1")
    for field in REQUIRED:
        if field not in product or product[field] in (None, ""):
            issues.append({"severity": "error", "code": "MISSING_REQUIRED", "field": field, "message": f"缺少必填欄位：{field}"})
    for field in ("link", "image_link"):
        value = product.get(field)
        if value:
            parsed = urlparse(value) if isinstance(value, str) else None
            if not parsed or parsed.scheme not in {"http", "https"} or not parsed.netloc:
                issues.append({"severity": "error", "code": "INVALID_URL", "field": field, "message": f"{field} 必須是完整 HTTP(S) URL"})
    price = product.get("price")
    if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or price < 0):
        issues.append({"severity": "error", "code": "INVALID_PRICE", "field": "price", "message": "price 必須是數字，不能包含貨幣符號"})
    currency = product.get("currency")
    if currency is not None and (not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency)):
        issues.append({"severity": "error", "code": "INVALID_CURRENCY", "field": "currency", "message": "currency 必須是三碼大寫 ISO 代碼"})
    if product.get("availability") not in (None, *AVAILABILITY):
        issues.append({"severity": "error", "code": "INVALID_AVAILABILITY", "field": "availability", "message": "availability 不在支援清單"})
    if product.get("version") and product.get("listing_version") and product["version"] != product["listing_version"]:
        issues.append({"severity": "error", "code": "VERSION_MISMATCH", "field": "listing_version", "message": "商品頁與交付版本不一致"})
    for path, value in iter_strings(product):
        if any(pattern.search(value) for pattern in SECRET_PATTERNS):
            issues.append({"severity": "error", "code": "SECRET_DETECTED", "field": path, "message": "偵測到疑似秘密值；未回顯原文"})
        if any(pattern.search(value) for pattern in PRIVATE_PATHS):
            issues.append({"severity": "error", "code": "PRIVATE_PATH", "field": path, "message": "偵測到私人本機路徑；未回顯原文"})
    errors = sum(issue["severity"] == "error" for issue in issues)
    return {"tool": "AgentFeed Forge Free", "version": VERSION, "product": product_id, "ready": errors == 0, "error_count": errors, "issues": issues, "pro_boundary": "Free validates one product and does not generate complete feeds, JSON-LD or deployment files."}


def main(argv=None):
    parser = argparse.ArgumentParser(description="免費驗證一個數位商品 JSON；不生成完整 Feed。")
    parser.add_argument("input", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict) and "products" in raw:
            products = raw["products"]
        elif isinstance(raw, dict):
            products = [raw]
        elif isinstance(raw, list):
            products = raw
        else:
            raise ValueError("根節點必須是商品物件、陣列或含 products 的物件")
        if len(products) != 1 or not isinstance(products[0], dict):
            raise ValueError("Free 版一次只能驗證 1 個商品；Pro 可批次處理最多 50 個")
        report = validate(products[0])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ready"] else 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
