#!/usr/bin/env python3
"""
Refresh the stock symbol catalog used by the app.

Sources:
- US: Nasdaq Trader market-share-by-symbol monthly files, ranked by volume.
- Taiwan: TWSE STOCK_DAY_ALL endpoint, ranked by latest daily traded value/volume.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps" / "api" / "data" / "symbols.json"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass
class Link:
    href: str
    text: str


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[Link] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append(Link(self._href, " ".join(self._text).strip()))
            self._href = None
            self._text = []


def fetch_text(url: str) -> str:
    response = requests.get(url, timeout=45)
    response.raise_for_status()
    return response.text


def fetch_bytes(url: str) -> bytes:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.content


def cell_value(cell: ET.Element, shared: list[str]) -> str:
    value = cell.find(f"{NS}v")
    if value is None:
        inline = cell.find(f"{NS}is/{NS}t")
        return inline.text if inline is not None and inline.text else ""
    raw = value.text or ""
    if cell.attrib.get("t") == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return ""
    return raw


def read_xlsx_rows(content: bytes) -> list[list[str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for item in tree.findall(f"{NS}si"):
                parts = [node.text or "" for node in item.iter(f"{NS}t")]
                shared.append("".join(parts))

        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in zf.namelist():
            sheet_name = sorted(name for name in zf.namelist() if name.startswith("xl/worksheets/sheet"))[0]
        tree = ET.fromstring(zf.read(sheet_name))

    rows: list[list[str]] = []
    for row in tree.findall(f".//{NS}row"):
        cells: dict[int, str] = {}
        for cell in row.findall(f"{NS}c"):
            ref = cell.attrib.get("r", "A1")
            col = 0
            for char in re.sub(r"\d", "", ref):
                col = col * 26 + ord(char.upper()) - 64
            cells[col - 1] = cell_value(cell, shared).strip()
        if cells:
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)])
    return rows


def normalize_number(value: Any) -> float:
    text = str(value or "").replace(",", "").replace("$", "").strip()
    if not text or text in {"-", "N/A"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def parse_nasdaq_directory() -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for url, exchange in [
        ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "NASDAQ"),
        ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "US"),
    ]:
        text = fetch_text(url)
        reader = csv.DictReader(io.StringIO(text), delimiter="|")
        for row in reader:
            symbol = (row.get("Symbol") or row.get("ACT Symbol") or "").strip()
            if not symbol or symbol.startswith("File Creation Time"):
                continue
            if row.get("Test Issue") == "Y" or row.get("ETF") == "Y":
                continue
            records[symbol] = {
                "name": (row.get("Security Name") or row.get("Company Name") or "").strip(),
                "exchange": row.get("Exchange", exchange) or exchange,
            }
    return records


def latest_market_share_links() -> list[str]:
    url = "https://www.nasdaqtrader.com/trader.aspx?ID=marketsharedaily"
    parser = LinkParser()
    parser.feed(fetch_text(url))
    urls = [
        urljoin(url, link.href)
        for link in parser.links
        if link.href and link.text and re.search(r"20\d\d", link.text) and ".xls" in link.href.lower()
    ]
    if not urls:
        raise RuntimeError("Could not find Nasdaq monthly volume files.")
    return urls[:2]


def parse_us_volume_file(content: bytes) -> list[dict[str, Any]]:
    rows = read_xlsx_rows(content)
    header_index = next(
        i for i, row in enumerate(rows)
        if any(cell.strip().lower() in {"symbol", "issue"} for cell in row)
        or any("symbol" in cell.lower() for cell in row)
    )
    headers = [h.strip() for h in rows[header_index]]
    out: list[dict[str, Any]] = []
    for row in rows[header_index + 1 :]:
        item = dict(zip(headers, row))
        symbol = (item.get("Symbol") or item.get("Security Symbol") or item.get("Issue") or "").strip()
        if not symbol or symbol.lower().startswith("total"):
            continue
        volume = normalize_number(item.get("Consolidated Volume"))
        if not volume:
            volume = max(normalize_number(v) for k, v in item.items() if "volume" in k.lower())
        out.append({"symbol": symbol.replace("/", "."), "volume": volume})
    return out


def build_us_symbols(limit: int = 1000) -> list[dict[str, Any]]:
    directory = parse_nasdaq_directory()
    volume_by_symbol: dict[str, float] = {}
    for url in latest_market_share_links():
        for row in parse_us_volume_file(fetch_bytes(url)):
            symbol = row["symbol"]
            volume_by_symbol[symbol] = volume_by_symbol.get(symbol, 0.0) + row["volume"]

    ranked = sorted(volume_by_symbol.items(), key=lambda item: item[1], reverse=True)
    symbols: list[dict[str, Any]] = []
    for rank, (symbol, volume) in enumerate(ranked, start=1):
        meta = directory.get(symbol)
        if not meta:
            continue
        symbols.append({
            "symbol": symbol,
            "providerSymbol": symbol,
            "market": "US",
            "exchange": meta["exchange"],
            "name": meta["name"],
            "rank": rank,
            "popularityMetric": volume,
            "source": "nasdaqtrader-market-share",
        })
        if len(symbols) >= limit:
            break
    return symbols


def build_tpex_symbols() -> list[dict[str, Any]]:
    url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
    payload = requests.get(url, timeout=45).json()
    rows: list[dict[str, Any]] = []
    for item in payload:
        code = (item.get("SecuritiesCompanyCode") or "").strip()
        name = (item.get("CompanyName") or "").strip()
        if not re.fullmatch(r"\d{4}", code) or code.startswith("0"):
            continue
        value = normalize_number(item.get("TransactionAmount"))
        volume = normalize_number(item.get("TradingShares"))
        rows.append({
            "symbol": code,
            "providerSymbol": f"{code}.TWO",
            "market": "TW",
            "exchange": "TPEx",
            "name": name,
            "popularityMetric": value or volume,
            "source": "tpex-mainboard-quotes",
        })
    return rows


def build_tw_symbols(limit: int = 1500) -> list[dict[str, Any]]:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    payload = requests.get(url, timeout=45).json()
    rows: list[dict[str, Any]] = []
    for item in payload:
        code = (item.get("Code") or item.get("證券代號") or "").strip()
        name = (item.get("Name") or item.get("證券名稱") or "").strip()
        if not re.fullmatch(r"\d{4,6}", code) or code.startswith("0"):
            continue
        value = normalize_number(item.get("TradeValue") or item.get("成交金額"))
        volume = normalize_number(item.get("TradeVolume") or item.get("成交股數"))
        rows.append({
            "symbol": code,
            "providerSymbol": f"{code}.TW",
            "market": "TW",
            "exchange": "TWSE",
            "name": name,
            "popularityMetric": value or volume,
            "source": "twse-stock-day-all",
        })
    rows.extend(build_tpex_symbols())
    deduped = {row["providerSymbol"]: row for row in rows}
    rows = list(deduped.values())
    rows.sort(key=lambda item: item["popularityMetric"], reverse=True)
    for rank, row in enumerate(rows[:limit], start=1):
        row["rank"] = rank
    return rows[:limit]


def main() -> int:
    us = build_us_symbols()
    tw = build_tw_symbols()
    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": [
            "https://www.nasdaqtrader.com/trader.aspx?ID=marketsharedaily",
            "https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs",
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes",
        ],
        "rotation": {
            "us": "Refresh monthly after Nasdaq Trader publishes the newest market-share-by-symbol files.",
            "tw": "Refresh daily after TWSE and TPEx publish end-of-day quote files.",
        },
        "symbols": us + tw,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(us)} US and {len(tw)} Taiwan symbols to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
