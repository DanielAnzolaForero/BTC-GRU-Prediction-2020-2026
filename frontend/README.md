# Vortex React — Trading Intelligence Dashboard

Stack: React + Vite + Tailwind CSS + Framer Motion + Recharts

## Inicio rápido

```bash
npm install
npm run dev        # desarrollo → http://localhost:5173
npm run build      # producción → carpeta dist/
```

## Estructura
```
src/
├── lib/
│   ├── config.js      ← API_URL, Supabase keys, constantes
│   └── parser.js      ← parsers y helpers de formato
├── hooks/
│   └── useVortex.js   ← toda la lógica de datos (Supabase + FastAPI)
├── components/
│   ├── Header.jsx
│   ├── HeroCard.jsx   ← precio, señal, barra de confianza
│   ├── PriceChart.jsx ← Recharts AreaChart con selector de ventana
│   ├── HistoryTable.jsx
│   └── ErrorBanner.jsx
└── App.jsx            ← layout con stagger animations (Framer Motion)
```

## Cambiar API URL
Edita `src/lib/config.js` línea 2:
```js
export const API_URL = "https://TU-SERVICIO.onrender.com/TU-RUTA";
```

## Deploy
```bash
npm run build
# Sube la carpeta dist/ a Netlify, Vercel, o GitHub Pages
```
