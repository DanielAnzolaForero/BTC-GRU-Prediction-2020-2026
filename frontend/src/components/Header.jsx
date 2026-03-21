import { motion } from "framer-motion";
import { RefreshCw } from "lucide-react";

export default function Header({ loading, lastUpdated, onRefresh }) {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="sticky top-0 z-50 border-b border-line"
      style={{ background: "rgba(6,10,16,.97)", backdropFilter: "blur(20px)" }}
    >
      <div className="max-w-6xl mx-auto px-5 flex items-center justify-between h-14">

        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg border border-faint bg-card2 flex items-center justify-center flex-shrink-0">
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path d="M7.5 1C10.8 1 13.5 3.5 13.5 7C13.5 10.2 11.1 13 7.8 13C5.3 13 3.5 11 4.3 9C5 7.3 7.5 6.5 7.5 7.8C7.5 9 5.8 10 4.8 9.3"
                    stroke="#818cf8" strokeWidth="1.3" strokeLinecap="round" fill="none"/>
              <circle cx="7.5" cy="7.3" r="1.3" fill="#818cf8"/>
            </svg>
          </div>
          <div>
            <span className="block font-mono font-bold text-ink tracking-[4px] text-xs leading-none">VORTEX</span>
            <span className="block font-mono text-dim text-[8px] tracking-[2px] uppercase mt-0.5">trading intelligence</span>
          </div>
        </div>

        {/* Right */}
        <div className="flex items-center gap-3">
          {/* Live badge */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[8px] font-mono font-medium tracking-widest text-buy"
               style={{ background: "rgba(0,217,126,.07)", borderColor: "rgba(0,217,126,.2)" }}>
            <motion.span
              animate={{ opacity: [1, 0.2, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="w-1.5 h-1.5 rounded-full bg-buy inline-block"
            />
            EN VIVO
          </div>

          {/* Clock */}
          <span className="font-mono text-dim text-[10px] hidden sm:block">{lastUpdated}</span>

          {/* Refresh button */}
          <motion.button
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.96 }}
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-faint bg-card2 font-mono text-[10px] font-semibold text-sub tracking-widest cursor-pointer disabled:opacity-30 transition-colors hover:border-dim hover:text-ink"
          >
            <motion.span animate={loading ? { rotate: 360 } : { rotate: 0 }}
                         transition={loading ? { duration: 0.7, repeat: Infinity, ease: "linear" } : {}}>
              <RefreshCw size={11} />
            </motion.span>
            REFRESH
          </motion.button>
        </div>
      </div>
    </motion.header>
  );
}
