"""
preprocessing_v2.py
--------------------
Preprocesamiento con los 4 timeframes del dataset de Kaggle.

BUG 3 CORREGIDO : Triple barrera usa clase neutral (2) para timeout.
BUG EXTRAS NaN  : fillna(0) de columnas extras al INICIO del pipeline,
                  antes de cualquier cálculo que las use.
"""
import numpy as np
import pandas as pd
import pandas_ta as ta


# Columnas que vienen de binance_extras con cobertura parcial (últimos 7 días)
# Se rellenan con 0 para preservar toda la historia del CSV
_EXTRAS_COLS = [
    "open_interest", "oi_change_1h", "oi_change_8h",
    "taker_ratio",   "taker_pressure", "taker_ratio_sma8",
    "ls_ratio",      "ls_extreme",     "ls_ratio_sma24",
    "liq_buy_usd",   "liq_sell_usd",   "liq_total", "liq_ratio",
]


class DataPreprocessor:
    def __init__(
        self,
        sequence_length: int = 30,
        look_ahead_macro: int = 24,
        tp_macro: float = 1.5,
        sl_macro: float = 1.0,
        look_ahead_micro: int = 6,
        tp_micro: float = 0.8,
        sl_micro: float = 0.5,
    ):
        self.sequence_length  = sequence_length
        self.look_ahead_macro = look_ahead_macro
        self.tp_macro         = tp_macro
        self.sl_macro         = sl_macro
        self.look_ahead_micro = look_ahead_micro
        self.tp_micro         = tp_micro
        self.sl_micro         = sl_micro

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # ── PASO 0: RELLENAR EXTRAS ANTES DE CUALQUIER CÁLCULO ────────────
        # Esto evita que NaN de columnas con cobertura parcial se propaguen
        # a features derivadas (taker_div_4h, etc.)
        for col in _EXTRAS_COLS:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # ATR solo para Triple Barrier
        df.ta.atr(length=14, append=True)
        col_atr       = [c for c in df.columns
                         if c.startswith("ATR_") or c.startswith("ATRr_")][0]
        df["atr_rel"] = df[col_atr] / df["close"]

        # ── A. ESTRUCTURA DE VELA 1H ──────────────────────────────────────
        hl = (df["high"] - df["low"]).replace(0, 1e-8)
        df["body_ratio"]  = (df["close"] - df["open"]) / hl
        df["upper_wick"]  = (df["high"] - df[["open","close"]].max(axis=1)) / hl
        df["lower_wick"]  = (df[["open","close"]].min(axis=1) - df["low"]) / hl
        df["body_size"]   = np.abs(df["close"] - df["open"]) / hl
        df["is_bullish"]  = (df["close"] > df["open"]).astype(int)

        # Taker ratio del CSV 1h (columna nativa del dataset Kaggle)
        if "taker_buy_vol" in df.columns:
            vol_safe              = df["volume"].replace(0, 1e-8)
            df["taker_ratio_1h"]  = df["taker_buy_vol"] / vol_safe
            df["taker_sell_1h"]   = 1 - df["taker_ratio_1h"]
            df["taker_press_1h"]  = (
                df["taker_ratio_1h"] - df["taker_ratio_1h"].rolling(24).mean()
            )

        if "num_trades" in df.columns:
            trades_sma       = df["num_trades"].rolling(24).mean().replace(0, 1e-8)
            df["rel_trades"] = df["num_trades"] / trades_sma

        # ── B. MOMENTUM MULTI-HORIZONTE ───────────────────────────────────
        for lag in [1, 4, 12, 24, 48, 168]:
            df[f"ret_{lag}h"] = np.log(
                df["close"] / df["close"].shift(lag).replace(0, 1e-8)
            )
        df["mom_accel_4"]  = df["ret_4h"]  - df["ret_4h"].shift(4)
        df["mom_accel_24"] = df["ret_24h"] - df["ret_24h"].shift(24)

        # ── C. VOLUMEN 1H ─────────────────────────────────────────────────
        df["ret_vol"] = np.log(
            df["volume"] / df["volume"].shift(1).replace(0, 1e-8)
        ).replace([np.inf, -np.inf], 0)

        vol_sma24            = df["volume"].rolling(24).mean().replace(0, 1e-8)
        df["rel_vol_24"]     = df["volume"] / vol_sma24
        df["vol_price_corr"] = df["ret_1h"].rolling(24).corr(df["ret_vol"])

        qv              = (df["quote_vol"] if "quote_vol" in df.columns
                           else df["close"] * df["volume"])
        vwap24          = qv.rolling(24).sum() / df["volume"].rolling(24).sum()
        df["vwap_dist"] = (df["close"] - vwap24) / df["close"]

        # ── D. RÉGIMEN DE VOLATILIDAD ─────────────────────────────────────
        atr_sma48        = df["atr_rel"].rolling(48).mean().replace(0, 1e-8)
        df["atr_change"] = (
            df["atr_rel"] / df["atr_rel"].shift(6).replace(0, 1e-8) - 1
        )
        df["vol_regime"] = (df["atr_rel"] > atr_sma48).astype(int)

        # ── E. CONTEXTO 4H (s_) ───────────────────────────────────────────
        if "s_close" in df.columns:
            hl4 = (df["s_high"] - df["s_low"]).replace(0, 1e-8)
            df["body_4h"]        = (df["s_close"] - df["s_open"]) / hl4
            df["upper_wick_4h"]  = (
                df["s_high"] - df[["s_open","s_close"]].max(axis=1)
            ) / hl4
            df["lower_wick_4h"]  = (
                df[["s_open","s_close"]].min(axis=1) - df["s_low"]
            ) / hl4
            df["ret_1c_4h"]      = np.log(
                df["s_close"] / df["s_close"].shift(1).replace(0, 1e-8)
            )
            df["ret_6c_4h"]      = np.log(
                df["s_close"] / df["s_close"].shift(6).replace(0, 1e-8)
            )
            df["divergence_1v4"] = df["ret_1h"] - df["ret_1c_4h"]
            vol_sma_4h           = df["s_volume"].rolling(10).mean().replace(0, 1e-8)
            df["rel_vol_4h"]     = df["s_volume"] / vol_sma_4h

            if "s_taker_buy_vol" in df.columns:
                s_vol_safe        = df["s_volume"].replace(0, 1e-8)
                df["taker_4h"]    = df["s_taker_buy_vol"] / s_vol_safe
                # Divergencia entre taker 1h (CSV) y taker 4h
                if "taker_ratio_1h" in df.columns:
                    df["taker_div_4h"] = df["taker_ratio_1h"] - df["taker_4h"]

        # ── F. MICROESTRUCTURA 15M (m_) ───────────────────────────────────
        if "m_close" in df.columns:
            hl15 = (df["m_high"] - df["m_low"]).replace(0, 1e-8)
            df["body_15m"]      = (df["m_close"] - df["m_open"]) / hl15
            df["ret_1c_15m"]    = np.log(
                df["m_close"] / df["m_close"].shift(1).replace(0, 1e-8)
            )
            df["ret_4c_15m"]    = np.log(
                df["m_close"] / df["m_close"].shift(4).replace(0, 1e-8)
            )
            df["mom_accel_15m"] = df["ret_4c_15m"] - df["ret_4c_15m"].shift(4)
            if "m_taker_buy_vol" in df.columns:
                m_vol_safe      = df["m_volume"].replace(0, 1e-8)
                df["taker_15m"] = df["m_taker_buy_vol"] / m_vol_safe

        # ── G. RÉGIMEN MACRO 1D (d_) ──────────────────────────────────────
        if "d_close" in df.columns:
            df["ret_1d"]        = np.log(
                df["d_close"] / df["d_close"].shift(1).replace(0, 1e-8)
            )
            df["ret_7d"]        = np.log(
                df["d_close"] / df["d_close"].shift(7).replace(0, 1e-8)
            )
            d_hl                = (df["d_high"] - df["d_low"]).replace(0, 1e-8)
            df["d_pos"]         = (df["d_close"] - df["d_low"]) / d_hl
            df["above_d_close"] = (df["close"] > df["d_close"]).astype(int)
            if "d_taker_buy_vol" in df.columns:
                d_vol_safe     = df["d_volume"].replace(0, 1e-8)
                df["taker_1d"] = df["d_taker_buy_vol"] / d_vol_safe

        # ── H. EXTRAS — OI, TAKER RATIO API, LONG/SHORT ──────────────────
        # Estas columnas ya tienen fillna(0) del paso 0
        # Se crean features relativas para los últimos 7 días de datos
        if "open_interest" in df.columns:
            oi = df["open_interest"].replace(0, np.nan)
            oi_sma = oi.rolling(48).mean()
            df["oi_rel"]     = (oi / oi_sma - 1).fillna(0)
            df["oi_chg_1h"]  = oi.pct_change(1).fillna(0)
            df["oi_chg_8h"]  = oi.pct_change(8).fillna(0)

        if "ls_ratio" in df.columns:
            df["ls_ratio_feat"] = df["ls_ratio"]
            ls_sma = df["ls_ratio"].replace(0, np.nan).rolling(24).mean()
            df["ls_vs_sma"]     = (df["ls_ratio"] - ls_sma).fillna(0)

        # ── I. FUNDING RATE (si disponible) ──────────────────────────────
        if "funding_rate" in df.columns:
            df["funding_sign"]    = np.sign(df["funding_rate"])
            df["funding_abs"]     = np.abs(df["funding_rate"])
            df["funding_extreme"] = (
                np.abs(df["funding_rate"])
                > df["funding_rate"].rolling(168).mean().abs() * 2
            ).astype(int)
            if "funding_rate_cum8" in df.columns:
                df["funding_pressure"] = df["funding_rate_cum8"]

        # ── J. TIEMPO CÍCLICO ─────────────────────────────────────────────
        if "open_time" in df.columns:
            dt             = pd.to_datetime(df["open_time"])
            df["hour_sin"] = np.sin(2 * np.pi * dt.dt.hour / 24)
            df["hour_cos"] = np.cos(2 * np.pi * dt.dt.hour / 24)
            df["dow_sin"]  = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
            df["dow_cos"]  = np.cos(2 * np.pi * dt.dt.dayofweek / 7)

        # ── TRIPLE BARRIER ────────────────────────────────────────────────
        df = self._add_triple_barrier(df)

        # ── LIMPIEZA ──────────────────────────────────────────────────────
        raw_prefixes = (
            "open", "high", "low", "close", "volume",
            "EMA_", "BBL_", "BBM_", "BBU_", "BBP_", "BBB_",
            "MACD_", "MACDh_", "MACDs_", "RSI_", "ATRr_", "ATR_",
        )
        raw_exact = {
            "quote_vol", "num_trades", "taker_buy_vol", "taker_buy_quote_vol",
            "s_open", "s_high", "s_low", "s_close", "s_volume",
            "s_quote_vol", "s_num_trades", "s_taker_buy_vol", "s_taker_buy_quote_vol",
            "m_open", "m_high", "m_low", "m_close", "m_volume",
            "m_quote_vol", "m_num_trades", "m_taker_buy_vol", "m_taker_buy_quote_vol",
            "d_open", "d_high", "d_low", "d_close", "d_volume",
            "d_quote_vol", "d_num_trades", "d_taker_buy_vol", "d_taker_buy_quote_vol",
            "funding_rate", "funding_rate_cum8",
            # Extras raw — se procesan arriba, las versiones raw se eliminan
            "open_interest", "oi_change_1h", "oi_change_8h",
            "taker_ratio", "taker_pressure", "taker_ratio_sma8",
            "ls_ratio", "ls_extreme", "ls_ratio_sma24",
            "liq_buy_usd", "liq_sell_usd", "liq_total", "liq_ratio",
        }
        keep = {
            # A — vela 1h
            "body_ratio", "upper_wick", "lower_wick", "body_size", "is_bullish",
            "taker_ratio_1h", "taker_sell_1h", "taker_press_1h", "rel_trades",
            # B — momentum
            "ret_1h", "ret_4h", "ret_12h", "ret_24h", "ret_48h", "ret_168h",
            "mom_accel_4", "mom_accel_24",
            # C — volumen
            "ret_vol", "rel_vol_24", "vol_price_corr", "vwap_dist",
            # D — volatilidad
            "atr_rel", "atr_change", "vol_regime",
            # E — 4h
            "body_4h", "upper_wick_4h", "lower_wick_4h",
            "ret_1c_4h", "ret_6c_4h", "divergence_1v4", "rel_vol_4h",
            "taker_4h", "taker_div_4h",
            # F — 15m
            "body_15m", "ret_1c_15m", "ret_4c_15m", "mom_accel_15m", "taker_15m",
            # G — 1d
            "ret_1d", "ret_7d", "d_pos", "above_d_close", "taker_1d",
            # H — extras API
            "oi_rel", "oi_chg_1h", "oi_chg_8h",
            "ls_ratio_feat", "ls_vs_sma",
            # I — funding
            "funding_sign", "funding_abs", "funding_extreme", "funding_pressure",
            # J — tiempo
            "hour_sin", "hour_cos", "dow_sin", "dow_cos",
            # targets
            "target_macro", "target_micro", "valid_macro", "valid_micro",
        }

        cols_to_drop = [
            c for c in df.columns
            if (c.startswith(raw_prefixes) or c in raw_exact) and c not in keep
        ]
        df.drop(columns=cols_to_drop, inplace=True)
        df.dropna(inplace=True)
        return df

    # ------------------------------------------------------------------
    def _add_triple_barrier(self, df):
        close = df["close"].values
        atr   = df["atr_rel"].values
        n     = len(df)
        maxlk = max(self.look_ahead_macro, self.look_ahead_micro)

        t_mac = np.full(n, 2, dtype=np.int8)   # BUG 3 FIX: neutral = 2
        t_mic = np.full(n, 2, dtype=np.int8)

        for i in range(n - maxlk):
            vol = atr[i] if not (np.isnan(atr[i]) or atr[i] == 0) else 0.005
            cp  = close[i]

            tp, sl = vol * self.tp_macro, vol * self.sl_macro
            for j in range(1, self.look_ahead_macro + 1):
                pct = (close[i+j] - cp) / cp
                if   pct >=  tp: t_mac[i] = 1; break
                elif pct <= -sl: t_mac[i] = 0; break

            tp, sl = vol * self.tp_micro, vol * self.sl_micro
            for j in range(1, self.look_ahead_micro + 1):
                pct = (close[i+j] - cp) / cp
                if   pct >=  tp: t_mic[i] = 1; break
                elif pct <= -sl: t_mic[i] = 0; break

        df["target_macro"] = t_mac
        df["target_micro"] = t_mic
        df["valid_macro"]  = (df["target_macro"] != 2)
        df["valid_micro"]  = (df["target_micro"] != 2)
        return df

    @staticmethod
    def label_report(df):
        for col in ["target_macro", "target_micro"]:
            if col not in df.columns:
                continue
            counts = df[col].value_counts().sort_index()
            total  = len(df)
            print(f"\n{col}:")
            labels = {0: "bajista", 1: "alcista", 2: "neutral"}
            for label, cnt in counts.items():
                print(f"  {labels.get(label,label):>8} ({label}): "
                      f"{cnt:6d} [{cnt/total*100:5.1f}%]")