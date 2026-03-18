import { motion, AnimatePresence } from "framer-motion";
import { fmtPrice, fmtConf, fmtTs, confColor } from "../lib/parser";

function getPulseStyle(conf) {
  if (conf >= 0.70) return {
    animation: "pulse-high 4s ease-in-out infinite",
    "--pulse-color": "rgba(0,217,126,.35)",
  };
  if (conf >= 0.55) return {
    animation: "pulse-mid 3s ease-in-out infinite",
    "--pulse-color": "rgba(255,183,3,.3)",
  };
  return {
    animation: "pulse-low 2.5s ease-in-out infinite",
    "--pulse-color": "rgba(255,77,109,.35)",
  };
}

function getTierCls(cls) {
  if (cls === "high") return "text-buy bg-buy/10 border-buy/20";
  if (cls === "mid")  return "text-hold bg-hold/10 border-hold/20";
  return "border text-[#ff8096] bg-[rgba(255,128,150,.08)] border-[rgba(255,128,150,.28)]";
}

export default function HeroCard({ latest, history, loading }) {
  if (!latest) return <HeroSkeleton />;

  const strong   = latest.conf >= 0.60;
  const cColor   = confColor(latest.conf);
  const confCls  = latest.conf >= .70 ? "conf-high" : latest.conf >= .55 ? "conf-mid" : "conf-low";

  return (
    <motion.div
      layout
      className="vx-card"
      style={getPulseStyle(latest.conf)}
    >
      {/* ── Top: price + signal ── */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-0 p-6 sm:p-7">

        {/* Price */}
        <div>
          <p className="font-mono text-dim text-[8px] tracking-[2.5px] uppercase mb-2">Precio en tiempo real</p>
          <AnimatePresence mode="wait">
            <motion.p
              key={latest.price}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="font-mono font-bold text-ink leading-none"
              style={{ fontSize: "clamp(1.9rem, 4.5vw, 2.8rem)", letterSpacing: "-1px" }}
            >
              {fmtPrice(latest.price)}
            </motion.p>
          </AnimatePresence>
          <div className="flex items-center gap-2 mt-3">
            <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-card2 border border-faint font-mono text-[9px] text-dim tracking-widest">
              <svg width="10" height="10" viewBox="0 0 14 14" fill="none">
                <path d="M9 2H4.5C3.67 2 3 2.67 3 3.5V10.5C3 11.33 3.67 12 4.5 12H9C10.1 12 11 11.1 11 10C11 9.4 10.72 8.85 10.28 8.5C10.72 8.15 11 7.6 11 7C11 5.9 10.1 5 9 5H8V2H9ZM8 6H9C9.55 6 10 6.45 10 7C10 7.55 9.55 8 9 8H8V6ZM8 9H9C9.55 9 10 9.45 10 10C10 10.55 9.55 11 9 11H8V9Z" fill="#f7931a"/>
              </svg>
              {latest.symbol}
            </div>
          </div>
        </div>

        {/* Signal — one instance only */}
        <div className="flex flex-col items-end justify-center gap-1 pl-6 border-l border-line sm:flex sm:flex-col sm:items-end">
          <span className="font-mono text-dim text-[8px] tracking-[2.5px] uppercase mb-1">Señal del modelo</span>

          <AnimatePresence mode="wait">
            <motion.div
              key={latest.label}
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.85, opacity: 0 }}
              transition={{ duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
              className="flex flex-col items-end gap-0"
            >
              <span className="font-mono font-light leading-none"
                    style={{ color: latest.cssColor, fontSize: strong ? "1.5rem" : "1rem",
                             opacity: strong ? 1 : 0.58 }}>
                {latest.arrow}
              </span>
              <span className="font-mono font-bold leading-none"
                    style={{ color: latest.cssColor,
                             fontSize: strong ? "clamp(2.4rem,5.5vw,3.2rem)" : "clamp(1.6rem,3.5vw,2.2rem)",
                             opacity: strong ? 1 : 0.58,
                             filter: strong ? "none" : "saturate(0.25)" }}>
                {latest.label}
              </span>
            </motion.div>
          </AnimatePresence>

          {!strong && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="font-mono text-hold text-[8px] tracking-wide mt-1"
            >
              ⚠ señal débil
            </motion.span>
          )}
        </div>
      </div>

      {/* ── Confidence bar — 14px prominent ── */}
      <div className="px-6 sm:px-7 pb-5 pt-1 bg-card2 border-t border-line">
        <div className="flex justify-between items-center mb-2">
          <span className="font-mono text-[8px] tracking-[2px] uppercase text-dim">Confianza del modelo</span>
          <motion.span
            key={latest.conf}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="font-mono font-bold text-[15px]"
            style={{ color: cColor }}
          >
            {fmtConf(latest.conf)}
          </motion.span>
        </div>

        {/* Bar track */}
        <div className="w-full h-3.5 rounded-lg bg-line overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${latest.conf * 100}%` }}
            transition={{ duration: 0.9, ease: [0.4, 0, 0.2, 1] }}
            className="h-full rounded-lg relative overflow-hidden"
            style={{ background: cColor, boxShadow: `0 0 12px ${cColor}66, 0 0 24px ${cColor}22` }}
          >
            {/* Shimmer */}
            <motion.div
              animate={{ x: ["-100%", "200%"] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.5 }}
              className="absolute inset-0 w-1/2"
              style={{ background: "linear-gradient(90deg, transparent, rgba(255,255,255,.15), transparent)" }}
            />
          </motion.div>
        </div>

        <div className="flex justify-between items-center mt-2">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full border font-mono text-[8px] tracking-widest ${getTierCls(latest.tier.cls)}`}>
            {latest.tier.label}
          </span>
          <span className="font-mono text-dim text-[8px] tracking-wide">
            {history.length} señal{history.length !== 1 ? "es" : ""} en sesión
          </span>
        </div>
      </div>

      {/* ── Meta strip ── */}
      <div className="grid grid-cols-3 border-t border-line">
        {[
          { key: "Último fetch", val: fmtTs(latest.ts) },
          { key: "Modelo",       val: "XGBoost v2.1" },
          { key: "Auto-refresh", val: "cada 30 s", green: true },
        ].map((m, i) => (
          <div key={i} className={`flex flex-col gap-1 px-4 py-2.5 ${i < 2 ? "border-r border-line" : ""}`}>
            <span className="font-mono text-[7px] text-dim tracking-[2px] uppercase">{m.key}</span>
            <span className={`font-mono text-[11px] font-medium ${m.green ? "text-buy" : "text-sub"}`}>{m.val}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function HeroSkeleton() {
  return (
    <div className="vx-card animate-pulse">
      <div className="p-7 grid grid-cols-[1fr_auto] gap-6">
        <div className="space-y-3">
          <div className="h-2.5 w-20 bg-faint rounded"></div>
          <div className="h-11 w-56 bg-faint rounded"></div>
          <div className="h-5 w-24 bg-faint rounded"></div>
        </div>
        <div className="flex flex-col items-end gap-3 pl-6 border-l border-line">
          <div className="h-2.5 w-16 bg-faint rounded"></div>
          <div className="h-16 w-28 bg-faint rounded"></div>
        </div>
      </div>
      <div className="px-7 pb-5 pt-2 bg-card2 border-t border-line space-y-2">
        <div className="flex justify-between">
          <div className="h-2 w-20 bg-faint rounded"></div>
          <div className="h-4 w-10 bg-faint rounded"></div>
        </div>
        <div className="h-3.5 w-full bg-faint rounded-lg"></div>
      </div>
    </div>
  );
}
