import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, X } from "lucide-react";

export default function ErrorBanner({ error, onDismiss }) {
  return (
    <AnimatePresence>
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -8, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -8, height: 0 }}
          transition={{ duration: 0.25 }}
          className="rounded-lg overflow-hidden"
          style={{ background: "rgba(255,77,109,.06)", border: "1px solid rgba(255,77,109,.22)" }}
        >
          <div className="flex items-start gap-3 p-3.5">
            <AlertCircle size={14} className="text-[#ff8096] mt-0.5 flex-shrink-0"/>
            <div className="flex-1">
              <p className="font-mono font-semibold text-[#ff8096] text-[11px] mb-1">Error de conexión</p>
              <p className="font-mono text-sub text-[9px] leading-relaxed">{error}</p>
            </div>
            <button onClick={onDismiss} className="text-dim hover:text-sub transition-colors">
              <X size={14}/>
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
