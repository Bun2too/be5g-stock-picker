from __future__ import annotations

import csv
import io
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3
from boto3.dynamodb.conditions import Attr, Key

dynamodb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")

SYMBOLS_TABLE = os.environ["SYMBOLS_TABLE"]
SNAPSHOTS_TABLE = os.environ["SNAPSHOTS_TABLE"]
RANKED_PICKS_TABLE = os.environ["RANKED_PICKS_TABLE"]
ALPACA_SECRET_ARN = os.environ.get("ALPACA_SECRET_ARN", "")
ALPACA_DATA_BASE_URL = os.environ.get("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets")
MAX_SYMBOLS_CATALOG = int(os.environ.get("MAX_SYMBOLS_CATALOG", "6000"))
MAX_SYMBOLS_PER_MARKET_REFRESH = int(os.environ.get("MAX_SYMBOLS_PER_MARKET_REFRESH", "300"))


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    job = event.get("job")
    if job == "refresh_symbols":
        return refresh_symbols()
    if job == "refresh_market_snapshots":
        return refresh_market_snapshots()
    if job == "score_symbols":
        return score_symbols()
    raise ValueError(f"Unknown job: {job}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def decimalize(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(round(value, 8)))
    if isinstance(value, dict):
        return {key: decimalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decimalize(item) for item in value]
    return value


def http_text(url: str, headers: dict[str, str] | None = None) -> str:
    request = Request(url, headers=headers or {})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8")


def refresh_symbols() -> dict[str, Any]:
    rows = fetch_us_symbols()
    table = dynamodb.Table(SYMBOLS_TABLE)
    updated_at = now_iso()

    with table.batch_writer() as batch:
        for rank, row in enumerate(rows[:MAX_SYMBOLS_CATALOG], start=1):
            item = {
                "market": "US",
                "symbol": row["symbol"],
                "providerSymbol": row["symbol"],
                "exchange": row["exchange"],
                "name": row["name"],
                "rank": rank,
                "active": True,
                "source": row["source"],
                "updatedAt": updated_at,
            }
            batch.put_item(Item=decimalize(item))

    return {"ok": True, "job": "refresh_symbols", "count": min(len(rows), MAX_SYMBOLS_CATALOG), "updatedAt": updated_at}


def fetch_us_symbols() -> list[dict[str, Any]]:
    urls = [
        ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "NASDAQ", "Symbol", "Security Name"),
        ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "US", "ACT Symbol", "Security Name"),
    ]
    rows: list[dict[str, Any]] = []
    for url, default_exchange, symbol_key, name_key in urls:
        text = http_text(url)
        reader = csv.DictReader(io.StringIO(text), delimiter="|")
        for row in reader:
            symbol = (row.get(symbol_key) or "").strip()
            if not symbol or symbol.startswith("File Creation Time"):
                continue
            if row.get("Test Issue") == "Y" or row.get("ETF") == "Y":
                continue
            rows.append({
                "symbol": symbol.replace("/", "."),
                "exchange": row.get("Exchange") or default_exchange,
                "name": (row.get(name_key) or "").strip(),
                "source": "nasdaqtrader-symbol-directory",
            })
    rows.sort(key=lambda item: (item["exchange"] != "NASDAQ", item["symbol"]))
    return rows


def refresh_market_snapshots() -> dict[str, Any]:
    credentials = alpaca_credentials()
    symbols = active_symbols("US", MAX_SYMBOLS_PER_MARKET_REFRESH)
    table = dynamodb.Table(SNAPSHOTS_TABLE)
    as_of = now_iso()
    written = 0

    for chunk in chunks([item["providerSymbol"] for item in symbols], 100):
        bars = fetch_alpaca_bars(chunk, credentials, timeframe="1Day", limit=260)
        with table.batch_writer() as batch:
            for symbol, series in bars.items():
                metrics = calculate_metrics(series)
                if not metrics:
                    continue
                item = {
                    "symbol": symbol,
                    "asOf": as_of,
                    "market": "US",
                    **metrics,
                }
                batch.put_item(Item=decimalize(item))
                written += 1
        time.sleep(0.25)

    return {"ok": True, "job": "refresh_market_snapshots", "count": written, "asOf": as_of}


def score_symbols() -> dict[str, Any]:
    snapshots = latest_snapshots("US")
    table = dynamodb.Table(RANKED_PICKS_TABLE)
    as_of = now_iso()
    written = 0

    scored = []
    for snap in snapshots:
        score = (
            float(snap.get("momentum3m", 0)) * 0.35
            + float(snap.get("momentum1y", 0)) * 0.35
            + max(0.0, 1.0 - float(snap.get("vol30", 1))) * 0.2
            + max(0.0, 1.0 + float(snap.get("drawdown1y", -1))) * 0.1
        )
        scored.append((max(0.0, min(score, 1.0)), snap))

    scored.sort(key=lambda item: item[0], reverse=True)
    with table.batch_writer() as batch:
        for score, snap in scored[:100]:
            score_key = f"{999999 - int(score * 1_000_000):06d}#{snap['symbol']}"
            item = {
                "universe": "us_most_traded",
                "scoreKey": score_key,
                "symbol": snap["symbol"],
                "market": snap.get("market", "US"),
                "score": score,
                "price": snap.get("price", 0),
                "advUsd": snap.get("advUsd", 0),
                "vol30": snap.get("vol30", 0),
                "drawdown1y": snap.get("drawdown1y", 0),
                "momentum3m": snap.get("momentum3m", 0),
                "momentum1y": snap.get("momentum1y", 0),
                "asOf": as_of,
            }
            batch.put_item(Item=decimalize(item))
            written += 1

    return {"ok": True, "job": "score_symbols", "count": written, "asOf": as_of}


def active_symbols(market: str, limit: int) -> list[dict[str, Any]]:
    table = dynamodb.Table(SYMBOLS_TABLE)
    response = table.query(
        KeyConditionExpression=Key("market").eq(market),
        Limit=limit,
    )
    items = response.get("Items", [])
    return sorted(items, key=lambda item: int(item.get("rank", 999999)))[:limit]


def latest_snapshots(market: str) -> list[dict[str, Any]]:
    table = dynamodb.Table(SNAPSHOTS_TABLE)
    response = table.scan(
        FilterExpression=Attr("market").eq(market),
        ProjectionExpression="symbol, market, price, advUsd, vol30, drawdown1y, momentum3m, momentum1y, asOf",
    )
    newest: dict[str, dict[str, Any]] = {}
    for item in response.get("Items", []):
        current = newest.get(item["symbol"])
        if not current or item.get("asOf", "") > current.get("asOf", ""):
            newest[item["symbol"]] = item
    return list(newest.values())


def alpaca_credentials() -> dict[str, str]:
    if not ALPACA_SECRET_ARN:
        raise RuntimeError("ALPACA_SECRET_ARN is required for market snapshot refresh.")
    payload = secretsmanager.get_secret_value(SecretId=ALPACA_SECRET_ARN)
    secret = json.loads(payload["SecretString"])
    return {
        "APCA-API-KEY-ID": secret["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": secret["ALPACA_API_SECRET"],
    }


def fetch_alpaca_bars(symbols: list[str], headers: dict[str, str], timeframe: str, limit: int) -> dict[str, list[dict[str, Any]]]:
    params = urlencode({
        "symbols": ",".join(symbols),
        "timeframe": timeframe,
        "limit": str(limit),
        "adjustment": "raw",
        "feed": os.environ.get("ALPACA_DATA_FEED", "iex"),
    })
    url = f"{ALPACA_DATA_BASE_URL}/v2/stocks/bars?{params}"
    try:
        payload = json.loads(http_text(url, headers=headers))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Alpaca bars request failed: {exc}") from exc
    return payload.get("bars", {})


def calculate_metrics(bars: list[dict[str, Any]]) -> dict[str, float] | None:
    if len(bars) < 35:
        return None
    closes = [float(bar["c"]) for bar in bars if "c" in bar]
    volumes = [float(bar.get("v", 0)) for bar in bars if "c" in bar]
    if len(closes) < 35:
        return None
    price = closes[-1]
    returns = [(closes[i] / closes[i - 1]) - 1 for i in range(1, len(closes)) if closes[i - 1]]
    recent_returns = returns[-30:] or returns
    avg_return = sum(recent_returns) / len(recent_returns)
    variance = sum((item - avg_return) ** 2 for item in recent_returns) / len(recent_returns)
    high = max(closes)
    adv_usd = sum(close * volume for close, volume in zip(closes[-30:], volumes[-30:])) / min(len(closes), 30)
    return {
        "price": price,
        "advUsd": adv_usd,
        "vol30": variance ** 0.5,
        "drawdown1y": (price / high) - 1 if high else 0,
        "momentum3m": (price / closes[-63]) - 1 if len(closes) >= 63 and closes[-63] else 0,
        "momentum1y": (price / closes[0]) - 1 if closes[0] else 0,
    }


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]
