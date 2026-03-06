import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Bot, 
  Terminal, 
  Play, 
  Square, 
  Settings, 
  Github, 
  AlertCircle, 
  CheckCircle2, 
  ExternalLink,
  Cpu,
  MessageSquare,
  ShieldCheck,
  Download
} from 'lucide-react';

export default function App() {
  const [status, setStatus] = useState({ 
    botRunning: false, 
    pythonAvailable: false, 
    pipAvailable: false,
    dbStats: { users: 0, tasks: 0, contributions: 0 }
  });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [installing, setInstalling] = useState(false);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to fetch status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const toggleBot = async () => {
    setActionLoading(true);
    try {
      const endpoint = status.botRunning ? '/api/bot/stop' : '/api/bot/start';
      await fetch(endpoint, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      console.error('Failed to toggle bot:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const installDeps = async () => {
    setInstalling(true);
    try {
      const res = await fetch('/api/bot/install', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        alert('Dependencies installed successfully!');
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      console.error('Failed to install dependencies:', err);
      alert('Failed to install dependencies. Check console.');
    } finally {
      setInstalling(false);
    }
  };

  const downloadSource = () => {
    window.open('/api/bot/download', '_blank');
  };

  return (
    <div className="min-h-screen bg-[#09090B] text-zinc-100 font-sans selection:bg-emerald-500/30">
      {/* Background Glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-emerald-500/5 blur-[120px] rounded-full" />
        <div className="absolute -bottom-[10%] -right-[10%] w-[40%] h-[40%] bg-indigo-500/5 blur-[120px] rounded-full" />
      </div>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-5"
          >
            <div className="w-16 h-16 bg-emerald-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-emerald-600/20 rotate-3">
              <Bot className="w-9 h-9 text-white -rotate-3" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white">Dhikr Bot <span className="text-emerald-500">Control</span></h1>
              <p className="text-zinc-500 text-sm font-medium">Enterprise Management Interface</p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3"
          >
            <button 
              onClick={downloadSource}
              className="px-5 py-2.5 bg-zinc-900 border border-zinc-800 rounded-xl flex items-center gap-2 hover:bg-zinc-800 transition-all text-sm font-semibold text-zinc-300 active:scale-95"
            >
              <Download className="w-4 h-4" />
              Source Code
            </button>
            <button className="p-2.5 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 transition-all active:scale-95">
              <Settings className="w-5 h-5 text-zinc-400" />
            </button>
          </motion.div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Quick Stats */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="lg:col-span-4 grid grid-cols-1 sm:grid-cols-3 gap-6"
          >
            <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-3xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-indigo-500/10 rounded-lg">
                  <Cpu className="w-5 h-5 text-indigo-400" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Active Users</h3>
              </div>
              <div className="text-4xl font-bold text-white">{status.dbStats.users.toLocaleString()}</div>
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-3xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-emerald-500/10 rounded-lg">
                  <Play className="w-5 h-5 text-emerald-400" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Active Tasks</h3>
              </div>
              <div className="text-4xl font-bold text-white">{status.dbStats.tasks.toLocaleString()}</div>
            </div>
            <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-3xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-amber-500/10 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-amber-400" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider">Total Dhikr</h3>
              </div>
              <div className="text-4xl font-bold text-white">{status.dbStats.contributions.toLocaleString()}</div>
            </div>
          </motion.div>

          {/* Main Control Panel */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-3 space-y-6"
          >
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none">
                <Terminal className="w-32 h-32" />
              </div>
              
              <div className="flex items-center justify-between mb-10">
                <div className="flex items-center gap-4">
                  <div className={`w-3 h-3 rounded-full ${status.botRunning ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.5)] animate-pulse' : 'bg-zinc-700'}`} />
                  <h2 className="text-2xl font-bold text-white">Bot Engine Status</h2>
                </div>
                <div className="px-4 py-1.5 bg-zinc-950 rounded-full border border-zinc-800 text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em]">
                  {status.botRunning ? 'Operational' : 'Standby'}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
                <div className="bg-zinc-950/50 border border-zinc-800/50 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
                  <span className="text-xs font-bold text-zinc-600 uppercase tracking-widest block mb-3">Runtime Environment</span>
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    <span className="font-semibold text-zinc-200">Python 3.10.x</span>
                  </div>
                </div>
                <div className="bg-zinc-950/50 border border-zinc-800/50 rounded-2xl p-6 hover:border-zinc-700 transition-colors">
                  <span className="text-xs font-bold text-zinc-600 uppercase tracking-widest block mb-3">Package Manager</span>
                  <div className="flex items-center gap-3">
                    {status.pipAvailable ? (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        <span className="font-semibold text-zinc-200">Pip3 Verified</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-5 h-5 text-amber-500" />
                        <span className="font-semibold text-amber-500">Pip3 Missing</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <button 
                  onClick={toggleBot}
                  disabled={actionLoading}
                  className={`flex-[2] py-5 rounded-2xl flex items-center justify-center gap-3 font-bold text-lg transition-all active:scale-[0.98] ${
                    status.botRunning 
                    ? 'bg-zinc-800 hover:bg-zinc-700 text-white border border-zinc-700' 
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-xl shadow-emerald-600/20'
                  } disabled:opacity-50`}
                >
                  {actionLoading ? (
                    <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : status.botRunning ? (
                    <>
                      <Square className="w-5 h-5 fill-current" />
                      Terminate Process
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5 fill-current" />
                      Initialize Engine
                    </>
                  )}
                </button>
                <button 
                  onClick={installDeps}
                  disabled={installing || status.botRunning}
                  className="flex-1 py-5 bg-zinc-950 border border-zinc-800 rounded-2xl font-bold hover:bg-zinc-900 transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  {installing ? 'Installing...' : 'Sync Dependencies'}
                </button>
              </div>
            </div>

            {/* System Logs Placeholder */}
            <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-8">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold text-lg flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-emerald-500" />
                  Live Activity
                </h3>
                <span className="text-[10px] text-zinc-600 font-bold uppercase tracking-widest">Real-time</span>
              </div>
              <div className="space-y-3 font-mono text-xs text-zinc-500">
                <div className="flex gap-4">
                  <span className="text-emerald-500/50">[SYSTEM]</span>
                  <span>Dashboard initialized successfully.</span>
                </div>
                <div className="flex gap-4">
                  <span className="text-indigo-500/50">[DATABASE]</span>
                  <span>Connected to MongoDB cluster.</span>
                </div>
                <div className="flex gap-4">
                  <span className={status.botRunning ? "text-emerald-500/50" : "text-zinc-700"}>[ENGINE]</span>
                  <span>{status.botRunning ? "Bot process is active and listening for events." : "Engine is currently idle."}</span>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Sidebar */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <div className="bg-emerald-600/5 border border-emerald-500/10 rounded-3xl p-6">
              <h3 className="font-bold mb-4 text-emerald-400">Quick Actions</h3>
              <div className="space-y-3">
                <button className="w-full p-4 bg-zinc-950 border border-zinc-800 rounded-2xl text-left text-sm font-semibold hover:bg-zinc-900 transition-all flex items-center justify-between group">
                  <span>Broadcast Alert</span>
                  <ExternalLink className="w-4 h-4 text-zinc-700 group-hover:text-emerald-500 transition-colors" />
                </button>
                <button className="w-full p-4 bg-zinc-950 border border-zinc-800 rounded-2xl text-left text-sm font-semibold hover:bg-zinc-900 transition-all flex items-center justify-between group">
                  <span>Export Analytics</span>
                  <ExternalLink className="w-4 h-4 text-zinc-700 group-hover:text-emerald-500 transition-colors" />
                </button>
              </div>
            </div>

            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6">
              <h3 className="font-bold mb-4">Infrastructure</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-500">Region</span>
                  <span className="text-sm font-semibold">Global-Edge</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-500">Database</span>
                  <span className="text-sm font-semibold">MongoDB Atlas</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-500">Version</span>
                  <span className="text-sm font-semibold">v2.4.0-stable</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-6 py-12 border-t border-zinc-900/50 mt-12">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3 text-zinc-600 text-xs font-bold uppercase tracking-widest">
            <Bot className="w-4 h-4" />
            <span>Dhikr Bot Enterprise Control</span>
          </div>
          <div className="flex items-center gap-8 text-xs font-bold text-zinc-600 uppercase tracking-widest">
            <a href="#" className="hover:text-emerald-500 transition-colors">Documentation</a>
            <a href="#" className="hover:text-emerald-500 transition-colors">Security</a>
            <a href="#" className="hover:text-emerald-500 transition-colors">Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
