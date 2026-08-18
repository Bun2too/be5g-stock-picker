from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SYMBOLS_FILE = DATA_DIR / "symbols.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"

SEEDED_SYMBOLS = [
    {"symbol": "NVDA", "providerSymbol": "NVDA", "market": "US", "exchange": "NASDAQ", "name": "NVIDIA Corporation", "rank": 1, "popularityMetric": 0, "source": "seed"},
    {"symbol": "TSLA", "providerSymbol": "TSLA", "market": "US", "exchange": "NASDAQ", "name": "Tesla, Inc.", "rank": 2, "popularityMetric": 0, "source": "seed"},
    {"symbol": "AAPL", "providerSymbol": "AAPL", "market": "US", "exchange": "NASDAQ", "name": "Apple Inc.", "rank": 3, "popularityMetric": 0, "source": "seed"},
    {"symbol": "MSFT", "providerSymbol": "MSFT", "market": "US", "exchange": "NASDAQ", "name": "Microsoft Corporation", "rank": 4, "popularityMetric": 0, "source": "seed"},
    {"symbol": "AMZN", "providerSymbol": "AMZN", "market": "US", "exchange": "NASDAQ", "name": "Amazon.com, Inc.", "rank": 5, "popularityMetric": 0, "source": "seed"},
    {"symbol": "2330", "providerSymbol": "2330.TW", "market": "TW", "exchange": "TWSE", "name": "TSMC", "rank": 1, "popularityMetric": 0, "source": "seed"},
    {"symbol": "2317", "providerSymbol": "2317.TW", "market": "TW", "exchange": "TWSE", "name": "Hon Hai", "rank": 2, "popularityMetric": 0, "source": "seed"},
    {"symbol": "2454", "providerSymbol": "2454.TW", "market": "TW", "exchange": "TWSE", "name": "MediaTek", "rank": 3, "popularityMetric": 0, "source": "seed"},
    {"symbol": "2303", "providerSymbol": "2303.TW", "market": "TW", "exchange": "TWSE", "name": "UMC", "rank": 4, "popularityMetric": 0, "source": "seed"},
]

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dynamodb_resource():
    import boto3

    return boto3.resource("dynamodb", region_name=settings.aws_region)


def _uses_dynamodb() -> bool:
    return (
        settings.symbol_store_backend.lower() == "dynamodb"
        and bool(settings.aws_symbols_table)
        and bool(settings.aws_portfolios_table)
    )


def _plain_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {key: _plain_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain_value(item) for item in value]
    return value


def _dedupe_symbols(symbols: List[str]) -> List[str]:
    return list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))


def catalog_payload() -> Dict[str, Any]:
    fallback = {
        "updatedAt": None,
        "sources": [],
        "rotation": {
            "us": "Run scripts/update_symbol_catalog.py monthly.",
            "tw": "Run scripts/update_symbol_catalog.py daily after TWSE close.",
        },
        "symbols": SEEDED_SYMBOLS,
    }
    return _read_json(SYMBOLS_FILE, fallback)


def all_symbols() -> List[Dict[str, Any]]:
    if _uses_dynamodb():
        table = _dynamodb_resource().Table(settings.aws_symbols_table)
        items: List[Dict[str, Any]] = []
        response = table.scan()
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        return [_plain_value(item) for item in items]
    return list(catalog_payload().get("symbols", []))


def search_symbols(query: str = "", markets: Optional[List[str]] = None, limit: int = 50) -> List[Dict[str, Any]]:
    normalized = query.strip().lower()
    market_set = {market.upper() for market in markets or [] if market}
    matches: List[Dict[str, Any]] = []
    source = _dynamodb_symbols_by_market(market_set) if _uses_dynamodb() and market_set else all_symbols()
    for item in source:
        if market_set and item.get("market") not in market_set:
            continue
        haystack = " ".join([
            str(item.get("symbol", "")),
            str(item.get("providerSymbol", "")),
            str(item.get("name", "")),
            str(item.get("exchange", "")),
        ]).lower()
        if normalized and normalized not in haystack:
            continue
        matches.append(item)
    matches.sort(key=lambda item: (item.get("rank") or 999999, item.get("symbol", "")))
    return matches[: max(1, min(limit, 250))]


def _dynamodb_symbols_by_market(markets: set[str]) -> List[Dict[str, Any]]:
    from boto3.dynamodb.conditions import Key

    table = _dynamodb_resource().Table(settings.aws_symbols_table)
    items: List[Dict[str, Any]] = []
    for market in markets:
        response = table.query(KeyConditionExpression=Key("market").eq(market))
        items.extend(response.get("Items", []))
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("market").eq(market),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
    return [_plain_value(item) for item in items]


def top_symbols(market: str, limit: int) -> List[Dict[str, Any]]:
    return search_symbols(markets=[market], limit=limit)


def symbol_map() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for item in all_symbols():
        out[f"{item.get('market')}:{item.get('symbol')}"] = item
        out[str(item.get("providerSymbol", "")).upper()] = item
    return out


def symbols_for_screen(universe: str, selected_symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    if universe == "us_most_traded":
        return top_symbols("US", 1000)
    if universe == "tw_popular":
        return top_symbols("TW", 1500)
    if universe == "mixed_portfolio":
        lookup = symbol_map()
        picked: List[Dict[str, Any]] = []
        for raw in selected_symbols or []:
            key = raw.strip().upper()
            item = lookup.get(key)
            if item:
                picked.append(item)
        return picked
    return []


def catalog_meta() -> Dict[str, Any]:
    if _uses_dynamodb():
        counts: Dict[str, int] = {}
        updated_at = None
        for item in all_symbols():
            market = item.get("market", "unknown")
            counts[market] = counts.get(market, 0) + 1
            if item.get("updatedAt") and (updated_at is None or item["updatedAt"] > updated_at):
                updated_at = item["updatedAt"]
        return {
            "updatedAt": updated_at,
            "counts": counts,
            "sources": ["dynamodb"],
            "rotation": {
                "us": "EventBridge scheduled Lambda refresh.",
                "tw": "Disabled until TW_STOCK_ENABLED and a Taiwan data adapter are configured.",
            },
        }

    payload = catalog_payload()
    counts: Dict[str, int] = {}
    for item in payload.get("symbols", []):
        market = item.get("market", "unknown")
        counts[market] = counts.get(market, 0) + 1
    return {
        "updatedAt": payload.get("updatedAt"),
        "counts": counts,
        "sources": payload.get("sources", []),
        "rotation": payload.get("rotation", {}),
    }


def get_portfolio(owner_key: str) -> Dict[str, Any]:
    if _uses_dynamodb():
        table = _dynamodb_resource().Table(settings.aws_portfolios_table)
        response = table.get_item(Key={"ownerKey": owner_key})
        item = response.get("Item")
        if not item:
            return {"symbols": [], "updatedAt": None}
        return _plain_value({
            "symbols": item.get("symbols", []),
            "updatedAt": item.get("updatedAt"),
        })
    payload = _read_json(PORTFOLIOS_FILE, {})
    return payload.get(owner_key, {"symbols": [], "updatedAt": None})


def save_portfolio(owner_key: str, symbols: List[str]) -> Dict[str, Any]:
    deduped = _dedupe_symbols(symbols)
    if _uses_dynamodb():
        item = {"ownerKey": owner_key, "symbols": deduped[:100], "updatedAt": _now()}
        table = _dynamodb_resource().Table(settings.aws_portfolios_table)
        table.put_item(Item=item)
        return {"symbols": item["symbols"], "updatedAt": item["updatedAt"]}
    with _lock:
        payload = _read_json(PORTFOLIOS_FILE, {})
        payload[owner_key] = {"symbols": deduped[:100], "updatedAt": _now()}
        _write_json(PORTFOLIOS_FILE, payload)
        return payload[owner_key]
