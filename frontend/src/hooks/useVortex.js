import { useState, useEffect, useCallback, useRef } from "react";
import { API_URL, SB_URL, SB_KEY, SB_TABLE, MAX_HISTORY, REFRESH_INTERVAL } from "../lib/config";
import { parseAPIRow, parseSupabaseRow } from "../lib/parser";

export function useVortex() {
  const [history, setHistory]       = useState([]);
  const [latest, setLatest]         = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [fetchCount, setFetchCount] = useState(0);
  const [sbLoaded, setSbLoaded]     = useState(false);
  const timerRef                    = useRef(null);

  // ── Load Supabase history ──────────────────────────────────
  const loadSupabase = useCallback(async () => {
    try {
      const url = `${SB_URL}/rest/v1/${SB_TABLE}`
        + `?select=id,created_at,symbol,prediction,probability,price_at_prediction`
        + `&order=created_at.desc&limit=${MAX_HISTORY}`;

      const res = await fetch(url, {
        headers: { apikey: SB_KEY, Authorization: "Bearer " + SB_KEY, Accept: "application/json" },
      });
      if (!res.ok) throw new Error(`Supabase ${res.status}`);
      const rows = await res.json();
      if (Array.isArray(rows) && rows.length) {
        const parsed = rows.map(parseSupabaseRow);
        setHistory(parsed);
        setLatest(parsed[0]);
      }
    } catch (e) {
      console.warn("Supabase load failed:", e.message);
    } finally {
      setSbLoaded(true);
    }
  }, []);

  // ── Fetch live signal ──────────────────────────────────────
  const fetchLive = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const ctrl = new AbortController();
      const tid  = setTimeout(() => ctrl.abort(), 15_000);
      const res  = await fetch(API_URL, {
        method: "GET", headers: { Accept: "application/json" }, signal: ctrl.signal,
      });
      clearTimeout(tid);
      if (!res.ok) throw new Error(`HTTP ${res.status} — ${res.statusText}`);
      const data = await res.json();
      if (!data.prediction)    throw new Error('Campo "prediction" ausente.');
      if (!data.current_price) throw new Error('Campo "current_price" ausente.');

      const entry = parseAPIRow(data);
      setFetchCount(c => c + 1);
      setLatest(entry);
      setHistory(prev => {
        const last = prev[0];
        const dupe = last &&
          last.price === entry.price &&
          last.label === entry.label &&
          last.conf  === entry.conf;
        if (dupe) return prev;
        const next = [entry, ...prev];
        return next.length > MAX_HISTORY ? next.slice(0, MAX_HISTORY) : next;
      });
    } catch (err) {
      let msg = err.message;
      if (err.name === "AbortError")       msg = "Timeout (15s) — Render puede estar dormido. Intenta de nuevo.";
      if (msg.includes("Failed to fetch")) msg = "Error de red o CORS. Verifica CORSMiddleware en tu FastAPI.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Init ──────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      await loadSupabase();
      await fetchLive();
      timerRef.current = setInterval(fetchLive, REFRESH_INTERVAL);
    })();
    return () => clearInterval(timerRef.current);
  }, []);

  return { history, latest, loading, error, fetchCount, sbLoaded, refresh: fetchLive };
}
