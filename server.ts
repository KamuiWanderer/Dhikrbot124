import express from "express";
import { createServer as createViteServer } from "vite";
import { spawn, spawnSync, ChildProcess } from "child_process";
import path from "path";
import fs from "fs";

import AdmZip from "adm-zip";

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;
  let botProcess: ChildProcess | null = null;

  app.use(express.json());

  // API Routes
  app.get("/api/status", (req, res) => {
    const pythonAvailable = spawnSync("python3", ["--version"]).status === 0;
    const pipAvailable = spawnSync("pip3", ["--version"]).status === 0;
    res.json({
      botRunning: botProcess !== null && !botProcess.killed,
      pythonAvailable,
      pipAvailable,
    });
  });

  app.get("/api/bot/download", (req, res) => {
    try {
      const zip = new AdmZip();
      const rootDir = process.cwd();
      
      // Add files and directories, excluding node_modules, etc.
      const items = fs.readdirSync(rootDir);
      for (const item of items) {
        if (["node_modules", "dist", ".next", ".git", "code.zip"].includes(item)) continue;
        
        const fullPath = path.join(rootDir, item);
        const stats = fs.statSync(fullPath);
        
        if (stats.isDirectory()) {
          zip.addLocalFolder(fullPath, item);
        } else {
          zip.addLocalFile(fullPath);
        }
      }

      const buffer = zip.toBuffer();
      res.set("Content-Type", "application/zip");
      res.set("Content-Disposition", "attachment; filename=dhikr-bot-source.zip");
      res.send(buffer);
    } catch (err) {
      console.error("Failed to create zip:", err);
      res.status(500).json({ error: "Failed to create zip" });
    }
  });

  app.post("/api/bot/install", (req, res) => {
    const reqPath = path.resolve(process.cwd(), "bot", "requirements.txt");
    if (!fs.existsSync(reqPath)) {
      return res.status(404).json({ error: "requirements.txt not found" });
    }

    const installProcess = spawn("pip3", ["install", "--user", "-r", reqPath], {
      stdio: "inherit",
    });

    installProcess.on("exit", (code) => {
      if (code === 0) {
        res.json({ message: "Dependencies installed successfully" });
      } else {
        res.status(500).json({ error: `Installation failed with code ${code}` });
      }
    });
  });

  app.post("/api/bot/start", (req, res) => {
    if (botProcess && !botProcess.killed) {
      return res.status(400).json({ error: "Bot is already running" });
    }

    const botPath = path.resolve(process.cwd(), "bot", "main.py");
    if (!fs.existsSync(botPath)) {
      return res.status(404).json({ error: "Bot script not found" });
    }

    botProcess = spawn("python3", [botPath], {
      stdio: "inherit",
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    botProcess.on("exit", (code) => {
      console.log(`Bot process exited with code ${code}`);
      botProcess = null;
    });

    res.json({ message: "Bot started" });
  });

  app.post("/api/bot/stop", (req, res) => {
    if (botProcess) {
      botProcess.kill();
      botProcess = null;
      return res.json({ message: "Bot stopped" });
    }
    res.status(400).json({ error: "Bot is not running" });
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static("dist"));
    app.get("*", (req, res) => {
      res.sendFile(path.resolve("dist", "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
    
    // Auto-start bot in production
    if (process.env.NODE_ENV === "production" && !botProcess) {
      const botPath = path.resolve(process.cwd(), "bot", "main.py");
      if (fs.existsSync(botPath)) {
        console.log("Auto-starting bot in production...");
        botProcess = spawn("python3", [botPath], {
          stdio: "inherit",
          env: { ...process.env, PYTHONUNBUFFERED: "1" },
        });
        botProcess.on("exit", (code) => {
          console.log(`Bot process exited with code ${code}`);
          botProcess = null;
        });
      }
    }
  });
}

startServer().catch((err) => {
  console.error("Failed to start server:", err);
});
