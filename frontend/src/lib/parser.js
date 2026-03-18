export function buildEntry(raw, price, confRaw, symbol, ts) {
  const r      = String(raw).trim().toUpperCase();
  const isBuy  = r === "BUY"  || r === "1" || r === "UP";
  const isSell = r === "SELL" || r === "0" || r === "DOWN";
  const isHold = !isBuy && !isSell;
  const conf   = Math.max(0, Math.min(1, confRaw));

  return {
    isBuy, isSell, isHold,
    price: parseFloat(price) || 0,
    conf,
    symbol: String(symbol || "BTCUSDT").toUpperCase(),
    label:    isBuy ? "BUY"        : isSell ? "SELL"        : "HOLD",
    arrow:    isBuy ? "↑"          : isSell ? "↓"           : "→",
    cssColor: isBuy ? "var(--buy)" : isSell ? "var(--sell)" : "var(--hold)",
    hexColor: isBuy ? "#00d97e"    : isSell ? "#ff4d6d"     : "#ffb703",
    colorKey: isBuy ? "buy"        : isSell ? "sell"        : "hold",
    tier:     getTier(conf),
    ts,
  };
}

export function parseAPIRow(data) {
  return buildEntry(
    data.prediction,
    data.current_price,
    parseFloat(data.probability ?? 0.5),
    data.symbol,
    new Date()
  );
}

export function parseSupabaseRow(row) {
  return buildEntry(
    row.prediction,
    row.price_at_prediction,
    parseFloat(row.probability ?? 0.5),
    row.symbol,
    row.created_at ? new Date(row.created_at) : new Date()
  );
}

export function getTier(c) {
  if (c >= .85) return { label: "Muy alta confianza", cls: "high" };
  if (c >= .70) return { label: "Alta confianza",     cls: "high" };
  if (c >= .55) return { label: "Confianza media",    cls: "mid"  };
  return               { label: "Baja confianza",     cls: "low"  };
}

export function confColor(c) {
  return c >= .70 ? "#00d97e" : c >= .55 ? "#ffb703" : "#ff8096";
}

export function fmtPrice(n) {
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtConf(n) { return (n * 100).toFixed(1) + "%"; }

export function fmtTs(d) {
  return d.toLocaleString("es-CO", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export function fmtTime(d) {
  return d.toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
