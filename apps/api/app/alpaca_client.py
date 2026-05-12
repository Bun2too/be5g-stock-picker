from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone

import pandas as pd
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from .config import settings

@dataclass
class Snapshot:
    ticker: str
    price: float
    adv_usd: float
    vol30: float
    drawdown1y: float
    momentum3m: float
    momentum1y: float

def _max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    roll_max = series.cummax()
    dd = (series / roll_max) - 1.0
    return float(dd.min() * -1.0)

def _realized_vol(daily_returns: pd.Series, window: int = 30) -> float:
    r = daily_returns.dropna()
    if len(r) < 3:
        return 0.0
    if len(r) < window + 1:
        return float(r.std() * np.sqrt(252))
    r = r.tail(window)
    return float(r.std() * np.sqrt(252))

class AlpacaAdapter:
    def __init__(self):
        self.data = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_api_secret)
        self.trading = TradingClient(
            settings.alpaca_api_key,
            settings.alpaca_api_secret,
            paper=settings.alpaca_paper,
            url_override=settings.alpaca_base_url,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.6, min=0.6, max=4))
    def fetch_daily_bars(self, tickers: List[str], lookback_days: int = 260, feed: Optional[str] = None) -> pd.DataFrame:
        feed = (feed or settings.alpaca_data_feed).lower()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=int(lookback_days * 1.6))
        req = StockBarsRequest(
            symbol_or_symbols=tickers,
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            feed=feed,
            adjustment="all",
        )
        bars = self.data.get_stock_bars(req).df
        if bars is None or bars.empty:
            return pd.DataFrame()
        bars = bars.reset_index()
        bars.rename(columns={"symbol":"ticker","timestamp":"ts"}, inplace=True)
        bars.sort_values(["ticker","ts"], inplace=True)
        bars = bars.groupby("ticker", as_index=False).tail(lookback_days)
        return bars

    def compute_snapshots(self, tickers: List[str], lookback_days: int = 260) -> Dict[str, Snapshot]:
        bars = self.fetch_daily_bars(tickers, lookback_days=lookback_days)
        out: Dict[str, Snapshot] = {}
        if bars.empty:
            return out

        for t, g in bars.groupby("ticker"):
            g = g.sort_values("ts")
            closes = g["close"].astype(float)
            vols = g["volume"].astype(float)

            last_price = float(closes.iloc[-1])
            adv = float(vols.tail(20).mean() * last_price)

            rets = closes.pct_change()
            vol30 = _realized_vol(rets, window=30)

            dd1y = _max_drawdown(closes.tail(252)) if len(closes) >= 30 else _max_drawdown(closes)

            def momentum(n: int) -> float:
                if len(closes) <= n:
                    return float(closes.iloc[-1] / closes.iloc[0] - 1.0) if len(closes) > 1 else 0.0
                return float(closes.iloc[-1] / closes.iloc[-(n+1)] - 1.0)

            m3 = momentum(63)
            m1y = momentum(252)

            out[t] = Snapshot(
                ticker=t,
                price=last_price,
                adv_usd=adv,
                vol30=float(vol30 if np.isfinite(vol30) else 0.0),
                drawdown1y=float(dd1y if np.isfinite(dd1y) else 0.0),
                momentum3m=float(m3),
                momentum1y=float(m1y),
            )
        return out

    def place_paper_order(self, symbol: str, side: str, qty: float, order_type: str, limit_price: Optional[float], tif: str):
        if not settings.alpaca_paper:
            raise ValueError("Paper trading is disabled (ALPACA_PAPER=false).")

        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        tif_enum = TimeInForce.DAY if tif.lower() == "day" else TimeInForce.GTC

        if order_type == "limit":
            if limit_price is None:
                raise ValueError("limit_price is required for limit orders.")
            req = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif_enum,
                limit_price=limit_price,
            )
        else:
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side_enum,
                time_in_force=tif_enum,
            )
        return self.trading.submit_order(req)
