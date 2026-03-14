import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Activity, DollarSign, 
  RefreshCw, Github, Zap, ShieldCheck 
} from 'lucide-react';
import { motion } from 'framer-motion';

// Mock data for initial design
const mockHistory = [
  { time: '10:00', price: 65200 },
  { time: '11:00', price: 65800 },
  { time: '12:00', price: 65400 },
  { time: '13:00', price: 66100 },
  { time: '14:00', price: 66900 },
  { time: '15:00', price: 67200 },
];

const Dashboard = () => {
  const [prediction, setPrediction] = useState<{direction: 'UP' | 'DOWN', prob: number} | null>({
    direction: 'UP',
    prob: 0.87
  });

  return (
    <div className="min-h-screen bg-background text-foreground p-6">
      {/* Header */}
      <nav className="flex justify-between items-center mb-10">
        <div className="flex items-center gap-2">
          <div className="bg-primary p-2 rounded-lg">
            <Zap className="text-white w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold gradient-text">CryptoPredict Pro</h1>
        </div>
        <div className="flex gap-4">
          <button className="glass-card px-4 py-2 text-sm flex items-center gap-2 hover:bg-white/5 transition">
            <Github className="w-4 h-4" /> Portfolio
          </button>
        </div>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Chart Card */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="lg:col-span-2 glass-card p-6"
        >
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="text-xl font-semibold">BTC/USDT Analysis</h2>
              <p className="text-gray-400 text-sm">Real-time market movement and AI forecasting</p>
            </div>
            <div className="flex gap-2">
              <span className="bg-green-500/10 text-green-500 px-3 py-1 rounded-full text-xs font-medium border border-green-500/20">
                LIVE DATA
              </span>
            </div>
          </div>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockHistory}>
                <defs>
                  <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="time" stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#71717a" fontSize={12} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#18181b', border: '1px solid #3f3f46', borderRadius: '8px' }}
                />
                <Area type="monotone" dataKey="price" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Prediction Panel */}
        <div className="space-y-6">
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass-card p-6 border-l-4 border-l-primary"
          >
            <div className="flex items-center gap-2 mb-4">
              <Activity className="text-primary w-5 h-5" />
              <h3 className="font-medium">AI Prediction Model</h3>
            </div>
            
            <div className="text-center py-6">
              <div className={`text-5xl font-bold mb-2 flex items-center justify-center gap-2 ${prediction?.direction === 'UP' ? 'text-green-500' : 'text-red-500'}`}>
                {prediction?.direction === 'UP' ? <TrendingUp className="w-10 h-10" /> : <TrendingDown className="w-10 h-10" />}
                {prediction?.direction}
              </div>
              <p className="text-gray-400 text-sm">Confidence Level</p>
              <div className="mt-4 bg-gray-800 rounded-full h-2 w-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${(prediction?.prob || 0) * 100}%` }}
                  className="bg-primary h-full"
                />
              </div>
              <p className="text-sm mt-1 font-mono text-primary">{(prediction?.prob || 0) * 100}%</p>
            </div>

            <button className="w-full bg-primary hover:bg-primary-dark text-white font-medium py-3 rounded-xl transition flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4" /> Run New Analysis
            </button>
          </motion.div>

          <motion.div 
             initial={{ opacity: 0, x: 20 }}
             animate={{ opacity: 1, x: 0, transition: { delay: 0.1 } }}
             className="glass-card p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <ShieldCheck className="text-accent w-5 h-5" />
              <h3 className="font-medium">Model Metrics</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <p className="text-xs text-gray-400">Accuracy</p>
                <p className="text-lg font-bold">78.4%</p>
              </div>
              <div className="text-center p-3 bg-white/5 rounded-lg">
                <p className="text-xs text-gray-400">LSTM Layers</p>
                <p className="text-lg font-bold">2</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
