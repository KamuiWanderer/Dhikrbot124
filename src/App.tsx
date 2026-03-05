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
  const [status, setStatus] = useState({ botRunning: false, pythonAvailable: false, pipAvailable: false });
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
    <div className="min-h-screen bg-[#0A0A0B] text-zinc-100 font-sans selection:bg-indigo-500/30">
      {/* Background Glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] bg-indigo-500/10 blur-[120px] rounded-full" />
        <div className="absolute -bottom-[20%] -right-[10%] w-[50%] h-[50%] bg-emerald-500/10 blur-[120px] rounded-full" />
      </div>

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-16">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4"
          >
            <div className="w-14 h-14 bg-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-600/20">
              <Bot className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Telethon Architect</h1>
              <p className="text-zinc-500 text-sm">Production-ready Telegram Bot Framework</p>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <a 
              href="https://github.com/LonamiWebs/Telethon" 
              target="_blank" 
              rel="noopener noreferrer"
              className="px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-xl flex items-center gap-2 hover:bg-zinc-800 transition-colors text-sm font-medium"
            >
              <Github className="w-4 h-4" />
              Telethon Master
            </a>
            <button className="p-2 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 transition-colors">
              <Settings className="w-5 h-5 text-zinc-400" />
            </button>
          </motion.div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Status Card */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 space-y-8"
          >
            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-8 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-indigo-400" />
                  <h2 className="text-xl font-semibold">System Status</h2>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 bg-zinc-950 rounded-full border border-zinc-800">
                  <div className={`w-2 h-2 rounded-full ${status.botRunning ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`} />
                  <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
                    {status.botRunning ? 'Live' : 'Offline'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
                <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-5">
                  <div className="flex items-center gap-3 mb-2">
                    <Cpu className="w-4 h-4 text-zinc-500" />
                    <span className="text-sm text-zinc-400">Python Environment</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                    <span className="font-medium">Python 3.10+ Detected</span>
                  </div>
                </div>
                <div className="bg-zinc-950 border border-zinc-800 rounded-2xl p-5">
                  <div className="flex items-center gap-3 mb-2">
                    <ShieldCheck className="w-4 h-4 text-zinc-500" />
                    <span className="text-sm text-zinc-400">Package Manager</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {status.pipAvailable ? (
                      <>
                        <CheckCircle2 className="w-5 h-5 text-indigo-500" />
                        <span className="font-medium">Pip3 Ready</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-5 h-5 text-amber-500" />
                        <span className="font-medium text-amber-500">Pip3 Missing</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4">
                <button 
                  onClick={toggleBot}
                  disabled={actionLoading}
                  className={`flex-1 py-4 rounded-2xl flex items-center justify-center gap-3 font-semibold transition-all ${
                    status.botRunning 
                    ? 'bg-zinc-800 hover:bg-zinc-700 text-white border border-zinc-700' 
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {actionLoading ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : status.botRunning ? (
                    <>
                      <Square className="w-5 h-5 fill-current" />
                      Stop Bot Process
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5 fill-current" />
                      Start Bot Process
                    </>
                  )}
                </button>
                <button 
                  onClick={installDeps}
                  disabled={installing || status.botRunning}
                  className="px-8 py-4 bg-zinc-950 border border-zinc-800 rounded-2xl font-semibold hover:bg-zinc-900 transition-colors disabled:opacity-50"
                >
                  {installing ? 'Installing...' : 'Install Dependencies'}
                </button>
                <button 
                  onClick={downloadSource}
                  className="px-8 py-4 bg-zinc-950 border border-zinc-800 rounded-2xl font-semibold hover:bg-zinc-900 transition-colors flex items-center justify-center gap-2"
                >
                  <Download className="w-5 h-5" />
                  Download Source
                </button>
              </div>
            </div>

            {/* Features Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-6">
                <div className="w-10 h-10 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-4">
                  <MessageSquare className="w-5 h-5 text-emerald-500" />
                </div>
                <h3 className="font-semibold mb-2">Interactive Buttons</h3>
                <p className="text-sm text-zinc-500">Full support for Success, Danger, and Primary style inline buttons with callback handling.</p>
              </div>
              <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-3xl p-6">
                <div className="w-10 h-10 bg-indigo-500/10 rounded-xl flex items-center justify-center mb-4">
                  <ShieldCheck className="w-5 h-5 text-indigo-500" />
                </div>
                <h3 className="font-semibold mb-2">Async Architecture</h3>
                <p className="text-sm text-zinc-500">Built on Telethon's latest async core for maximum performance and reliability.</p>
              </div>
            </div>
          </motion.div>

          {/* Sidebar / Instructions */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-6"
          >
            <div className="bg-indigo-600/10 border border-indigo-500/20 rounded-3xl p-6">
              <div className="flex items-center gap-2 text-indigo-400 mb-4">
                <AlertCircle className="w-5 h-5" />
                <h3 className="font-semibold">Setup Required</h3>
              </div>
              <p className="text-sm text-zinc-400 mb-6 leading-relaxed">
                To run the bot, you must provide your Telegram API credentials in the environment variables.
              </p>
              <ol className="space-y-4 text-sm">
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-500/20 rounded-full flex items-center justify-center text-xs font-bold text-indigo-400">1</span>
                  <span>Get API_ID and API_HASH from <a href="https://my.telegram.org" className="text-indigo-400 hover:underline">my.telegram.org</a></span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-500/20 rounded-full flex items-center justify-center text-xs font-bold text-indigo-400">2</span>
                  <span>Get BOT_TOKEN from <a href="https://t.me/BotFather" className="text-indigo-400 hover:underline">@BotFather</a></span>
                </li>
                <li className="flex gap-3">
                  <span className="flex-shrink-0 w-6 h-6 bg-indigo-500/20 rounded-full flex items-center justify-center text-xs font-bold text-indigo-400">3</span>
                  <span>Add them to the Secrets panel in AI Studio.</span>
                </li>
              </ol>
            </div>

            <div className="bg-zinc-900/50 border border-zinc-800 rounded-3xl p-6">
              <h3 className="font-semibold mb-4">Quick Links</h3>
              <div className="space-y-3">
                <a href="#" className="flex items-center justify-between p-3 bg-zinc-950 border border-zinc-800 rounded-xl hover:bg-zinc-900 transition-colors group">
                  <span className="text-sm text-zinc-400 group-hover:text-zinc-200">Documentation</span>
                  <ExternalLink className="w-4 h-4 text-zinc-600" />
                </a>
                <a href="#" className="flex items-center justify-between p-3 bg-zinc-950 border border-zinc-800 rounded-xl hover:bg-zinc-900 transition-colors group">
                  <span className="text-sm text-zinc-400 group-hover:text-zinc-200">API Reference</span>
                  <ExternalLink className="w-4 h-4 text-zinc-600" />
                </a>
              </div>
            </div>
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto px-6 py-12 border-t border-zinc-900 mt-12">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-2 text-zinc-600 text-sm">
            <Bot className="w-4 h-4" />
            <span>Telethon Architect v2.0.0-alpha</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-zinc-500">
            <a href="#" className="hover:text-zinc-300 transition-colors">Privacy</a>
            <a href="#" className="hover:text-zinc-300 transition-colors">Terms</a>
            <a href="#" className="hover:text-zinc-300 transition-colors">Support</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
