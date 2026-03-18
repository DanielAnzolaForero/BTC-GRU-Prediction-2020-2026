import { motion, AnimatePresence } from "framer-motion";
import { fmtPrice, fmtConf, fmtTs, confColor } from "../lib/parser";

const PillMap = {
  buy:  "vx-pill-buy",
  sell: "vx-pill-sell",
  hold: "vx-pill-hold",
};

export default function HistoryTable({ history }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="vx-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-line">
        <div>
          <p className="font-mono font-semibold text-sub text-[11px] tracking-wide">HISTORIAL DE SEÑALES</p>
          <p className="font-mono text-dim text-[8px] mt-0.5 tracking-wide">SESIÓN ACTUAL</p>
        </div>
        <span className="font-mono text-[9px] text-dim px-2.5 py-0.5 rounded-full bg-card2 border border-faint tracking-wide">
          {history.length} señal{history.length !== 1 ? "es" : ""}
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full" style={{ borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr className="bg-card2">
              {["Timestamp","Señal","Precio","Prob.","Δ Precio"].map((h, i) => (
                <th key={h} className={`px-3.5 py-2.5 font-mono text-[7px] tracking-[2px] uppercase text-dim border-b border-line font-medium ${i >= 2 ? "text-right" : "text-left"}`}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center font-mono text-[8px] text-dim tracking-[2px]">
                    SIN SEÑALES AÚN
                  </td>
                </tr>
              ) : history.map((e, i) => {
                const prev  = history[i + 1];
                let delta   = null;
                if (prev) {
                  const diff = e.price - prev.price;
                  const pct  = ((diff / prev.price) * 100).toFixed(2);
                  delta = { pct, color: diff > 0 ? "#00d97e" : diff < 0 ? "#ff4d6d" : "#64748b", sign: diff >= 0 ? "+" : "" };
                }
                return (
                  <motion.tr
                    key={e.ts.toISOString() + e.price}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.25, delay: i * 0.03 }}
                    className={`border-b border-line/60 transition-colors hover:bg-white/[.015] ${i === 0 ? "bg-buy/[.025]" : i % 2 === 1 ? "bg-card2/50" : ""}`}
                  >
                    <td className="px-3.5 py-2.5 font-mono text-[9px] text-dim">{fmtTs(e.ts)}</td>
                    <td className="px-3.5 py-2.5">
                      <span className={PillMap[e.colorKey]}>{e.arrow} {e.label}</span>
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono font-semibold text-ink text-[12px]">
                      {fmtPrice(e.price)}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono font-semibold text-[12px]"
                        style={{ color: confColor(e.conf) }}>
                      {fmtConf(e.conf)}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-mono font-semibold text-[11px]"
                        style={{ color: delta?.color ?? "#64748b" }}>
                      {delta ? `${delta.sign}${delta.pct}%` : "—"}
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
