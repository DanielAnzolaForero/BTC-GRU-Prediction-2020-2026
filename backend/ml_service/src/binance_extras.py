"""
binance_extras.py
-----------------
Enriquece el DataFrame base con datos adicionales de Binance.
No requiere API key — endpoints públicos.

Estrategia por endpoint:
  - Funding Rate   → paginación completa con startTime (soportado)
  - OI / Taker / LS → solo pedir limit=500 sin startTime (ventana ~7 días)
  - Liquidaciones  → solo pedir limit=1000 sin startTime (últimas 24h)
  - Altcoins       → paginación completa con startTime (soportado)
"""

import logging
import time
import numpy as np
import pandas as pd
import requests

logger       = logging.getLogger(__name__)
FUTURES_BASE = "https://fapi.binance.com"
SPOT_BASE    = "https://api.binance.com"


class BinanceExtras:

    def enrich(self, df: pd.DataFrame, symbol: str = "BTCUSDT") -> pd.DataFrame:
        df       = df.copy()
        start_ts = int(pd.to_datetime(df["open_time"].iloc[0]).timestamp() * 800)
        end_ts   = int(pd.to_datetime(df["open_time"].iloc[-1]).timestamp() * 800)
        added    = []

        # ── A. Funding Rate — historia completa con paginación ────────────
        df_fr = self._fetch_funding_rate(symbol, start_ts, end_ts)
        if df_fr is not None:
            df = self._merge_col(df, df_fr, "funding_rate")
            df["funding_rate_cum8"] = (
                df["funding_rate"].rolling(3, min_periods=1).sum()
            )
            added.append("funding_rate")

        # ── B. Open Interest — últimos ~500 registros (sin startTime) ─────
        df_oi = self._fetch_recent_1h(
            f"{FUTURES_BASE}/futures/data/openInterestHist",
            symbol, val_col="sumOpenInterest", out_col="open_interest",
        )
        if df_oi is not None:
            df = self._merge_col(df, df_oi, "open_interest")
            oi = df["open_interest"].replace(0, np.nan)
            df["oi_change_1h"] = oi.pct_change(1)
            df["oi_change_8h"] = oi.pct_change(8)
            df["oi_rel"]       = oi / oi.rolling(48).mean() - 1
            added.append("open_interest")

        # ── C. Taker Buy/Sell Ratio — últimos ~500 registros ─────────────
        df_tr = self._fetch_recent_1h(
            f"{FUTURES_BASE}/futures/data/takerlongshortRatio",
            symbol, val_col="buySellRatio", out_col="taker_ratio",
        )
        if df_tr is not None:
            df = self._merge_col(df, df_tr, "taker_ratio")
            sma8 = df["taker_ratio"].rolling(8).mean()
            df["taker_pressure"] = df["taker_ratio"] - sma8
            added.append("taker_ratio")

        # ── D. Long/Short Ratio — últimos ~500 registros ──────────────────
        df_ls = self._fetch_recent_1h(
            f"{FUTURES_BASE}/futures/data/globalLongShortAccountRatio",
            symbol, val_col="longShortRatio", out_col="ls_ratio",
        )
        if df_ls is not None:
            df = self._merge_col(df, df_ls, "ls_ratio")
            sma24 = df["ls_ratio"].rolling(24).mean()
            std168 = df["ls_ratio"].rolling(168).std()
            df["ls_extreme"] = (
                np.abs(df["ls_ratio"] - sma24) > std168 * 1.5
            ).astype(int)
            added.append("ls_ratio")

        # ── E. Liquidaciones — últimas 24h sin startTime ──────────────────
        df_liq = self._fetch_liquidations(symbol)
        if df_liq is not None:
            df = self._merge_col(df, df_liq, "liq_buy_usd")
            df = self._merge_col(df, df_liq, "liq_sell_usd")
            total = (df["liq_buy_usd"] + df["liq_sell_usd"]).replace(0, np.nan)
            df["liq_ratio"] = df["liq_buy_usd"] / total
            df["liq_total"] = np.log1p(total)
            added.append("liquidaciones")

        # ── F. Activos correlados — historia completa ─────────────────────
        for alt in ["ETHUSDT", "BNBUSDT"]:
            prefix = alt.replace("USDT", "").lower()
            df_alt = self._fetch_klines(alt, start_ts, end_ts)
            if df_alt is not None:
                df = self._merge_col(df, df_alt, f"{prefix}_ret_1h")
                df = self._merge_col(df, df_alt, f"{prefix}_ret_4h")
                df[f"{prefix}_div"] = (
                    df["ret_1h"] - df[f"{prefix}_ret_1h"]
                )
                added.append(prefix)

        print(f"  Extras cargados: {added}")
        return df

    # ------------------------------------------------------------------
    # Fetch helpers
    # ------------------------------------------------------------------
    def _fetch_funding_rate(self, symbol, start_ts, end_ts):
        rows, cur = [], start_ts
        try:
            while True:
                r = requests.get(
                    f"{FUTURES_BASE}/fapi/v1/fundingRate",
                    params={"symbol": symbol, "startTime": cur,
                            "endTime": end_ts, "limit": 1000},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                if not data: break
                rows.extend(data)
                if len(data) < 1000: break
                cur = data[-1]["fundingTime"] + 1
            if not rows: return None
            df = pd.DataFrame(rows)
            df["open_time"]    = pd.to_datetime(df["fundingTime"], unit="ms")
            df["funding_rate"] = df["fundingRate"].astype(float)
            return df[["open_time", "funding_rate"]].sort_values("open_time")
        except Exception as e:
            logger.error(f"Error funding_rate: {e}"); return None

    def _fetch_recent_1h(self, url, symbol, val_col, out_col):
        """Sin startTime — devuelve los últimos 500 registros del endpoint."""
        try:
            r = requests.get(
                url,
                params={"symbol": symbol, "period": "1h", "limit": 500},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if not data: return None
            df = pd.DataFrame(data)
            ts_col = "timestamp" if "timestamp" in df.columns else "createTime"
            df["open_time"] = pd.to_datetime(df[ts_col], unit="ms")
            df[out_col]     = df[val_col].astype(float)
            return df[["open_time", out_col]].sort_values("open_time")
        except Exception as e:
            logger.error(f"Error {out_col}: {e}"); return None

    def _fetch_liquidations(self, symbol):
        """Últimas liquidaciones sin startTime — solo ~24h disponibles."""
        try:
            r = requests.get(
                f"{FUTURES_BASE}/fapi/v1/allForceOrders",
                params={"symbol": symbol, "limit": 1000},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if not data: return None
            df = pd.DataFrame(data)
            df["open_time"]  = pd.to_datetime(df["time"], unit="ms").dt.floor("h")
            df["usd_val"]    = df["price"].astype(float) * df["executedQty"].astype(float)
            df["is_buy"]     = (df["side"] == "BUY").astype(int)

            liq_buy  = df[df["is_buy"] == 1].groupby("open_time")["usd_val"].sum()
            liq_sell = df[df["is_buy"] == 0].groupby("open_time")["usd_val"].sum()

            out = pd.DataFrame({
                "liq_buy_usd":  liq_buy,
                "liq_sell_usd": liq_sell,
            }).fillna(0).reset_index()
            return out
        except Exception as e:
            logger.error(f"Error liquidaciones: {e}"); return None

    def _fetch_klines(self, symbol, start_ts, end_ts):
        prefix   = symbol.replace("USDT", "").lower()
        rows, cur = [], start_ts
        try:
            while True:
                r = requests.get(
                    f"{SPOT_BASE}/api/v3/klines",
                    params={"symbol": symbol, "interval": "1h",
                            "startTime": cur, "endTime": end_ts,
                            "limit": 1000},
                    timeout=10,
                )
                r.raise_for_status()
                data = r.json()
                if not data: break
                rows.extend(data)
                if len(data) < 1000: break
                cur = data[-1][0] + 1
            if not rows: return None
            df = pd.DataFrame(rows, columns=[
                "open_time","open","high","low","close","volume",
                "close_time","qav","trades","tbbav","tbqav","ignore"
            ])
            df["open_time"]         = pd.to_datetime(df["open_time"], unit="ms")
            close                   = df["close"].astype(float)
            df[f"{prefix}_ret_1h"]  = np.log(close / close.shift(1))
            df[f"{prefix}_ret_4h"]  = np.log(close / close.shift(4))
            return df[["open_time", f"{prefix}_ret_1h",
                        f"{prefix}_ret_4h"]].sort_values("open_time")
        except Exception as e:
            logger.error(f"Error klines {symbol}: {e}"); return None

    # ------------------------------------------------------------------
    # Merge helper — una columna a la vez
    # ------------------------------------------------------------------
    def _merge_col(self, df: pd.DataFrame,
                   df_extra: pd.DataFrame, col: str) -> pd.DataFrame:
        if col not in df_extra.columns:
            return df
        series      = df_extra.set_index("open_time")[col]
        df          = df.set_index("open_time")
        df[col]     = series.reindex(df.index, method="ffill")
        return df.reset_index()
