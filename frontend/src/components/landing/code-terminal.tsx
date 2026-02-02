"use client";

import { motion } from "framer-motion";
import { useState, useEffect } from "react";

const lines = [
  { type: "comment", content: "# Error detected in main.py" },
  { type: "error", content: "TypeError: 'NoneType' has no attribute 'items'" },
  { type: "blank", content: "" },
  { type: "ai", content: "🌱 GitHub Gardener analyzing..." },
  { type: "blank", content: "" },
  { type: "success", content: "✓ Found issue: Missing null check at line 42" },
  { type: "code", content: "if data is not None:" },
  { type: "code", content: "    for key, val in data.items():" },
  { type: "blank", content: "" },
  { type: "success", content: "✓ Fix applied and committed!" },
];

export function CodeTerminal() {
  const [visibleLines, setVisibleLines] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setVisibleLines((prev) => {
        if (prev >= lines.length) {
          // Reset after showing all lines
          setTimeout(() => setVisibleLines(0), 2000);
          return prev;
        }
        return prev + 1;
      });
    }, 400);

    return () => clearInterval(timer);
  }, []);

  const getLineColor = (type: string) => {
    switch (type) {
      case "comment":
        return "text-muted-foreground";
      case "error":
        return "text-red-400";
      case "ai":
        return "text-emerald-400";
      case "success":
        return "text-green-400";
      case "code":
        return "text-cyan-300";
      default:
        return "text-foreground";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="relative"
    >
      {/* Glow effect */}
      <div className="absolute -inset-1 bg-gradient-to-r from-green-500/30 via-emerald-500/20 to-teal-500/30 rounded-2xl blur-xl opacity-50" />

      {/* Terminal Window */}
      <div className="relative rounded-xl border border-white/10 bg-black/80 backdrop-blur-xl overflow-hidden shadow-2xl">
        {/* Terminal Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10 bg-white/5">
          <div className="flex gap-2">
            <div className="h-3 w-3 rounded-full bg-red-500/80" />
            <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
            <div className="h-3 w-3 rounded-full bg-green-500/80" />
          </div>
          <span className="ml-2 text-xs text-muted-foreground font-mono">
            github-gardener ~ main.py
          </span>
        </div>

        {/* Terminal Content */}
        <div className="p-4 font-mono text-sm min-h-[280px]">
          {lines.slice(0, visibleLines).map((line, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className={`${getLineColor(line.type)} ${line.type === "blank" ? "h-4" : ""}`}
            >
              {line.content}
            </motion.div>
          ))}
          {visibleLines < lines.length && (
            <motion.span
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.5, repeat: Infinity }}
              className="inline-block w-2 h-4 bg-green-400 ml-1"
            />
          )}
        </div>
      </div>
    </motion.div>
  );
}
