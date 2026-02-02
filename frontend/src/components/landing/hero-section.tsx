"use client";

import { motion } from "framer-motion";
import { ArrowRight, Play, Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CodeTerminal } from "./code-terminal";

const techLogos = [
  { name: "Next.js", svg: "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm5.5 17.7l-8-12.3v9.5H8V6.8l8.2 12.6c-.2.1-.4.2-.7.3zm1.5-1.2V6.5h-1.5v7.5l-7-10.8c.8-.5 1.7-.8 2.5-1 .3 0 .5-.1.8-.1 4.4 0 8 3.6 8 8 0 2.2-.9 4.2-2.3 5.7l-.5-.3z" },
  { name: "Python", svg: "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm-.2 4.5c.5 0 .9.4.9.9s-.4.9-.9.9-.9-.4-.9-.9.4-.9.9-.9zM17.5 9v4.5c0 2.5-2 4.5-4.5 4.5H9.5c-1.9 0-3.5 1.6-3.5 3.5v1.3c0 .7.6 1.2 1.3 1.2h9.4c.7 0 1.3-.5 1.3-1.2V19h-4v-1h5.5c1.9 0 3.5-1.6 3.5-3.5V9c0-1.9-1.6-3.5-3.5-3.5H17V9h.5zm-6.3 9.5c.5 0 .9.4.9.9s-.4.9-.9.9-.9-.4-.9-.9.4-.9.9-.9z" },
  { name: "Temporal", svg: "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm0 4c4.4 0 8 3.6 8 8s-3.6 8-8 8-8-3.6-8-8 3.6-8 8-8zm0 2c-3.3 0-6 2.7-6 6s2.7 6 6 6 6-2.7 6-6-2.7-6-6-6zm0 2c2.2 0 4 1.8 4 4s-1.8 4-4 4-4-1.8-4-4 1.8-4 4-4z" },
  { name: "Docker", svg: "M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm9 12.9c-.2 1.6-1.3 3.2-2.8 4.2-1.6 1-3.5 1.5-5.5 1.4-2.5-.1-4.7-1.1-6.4-2.9s-2.6-4.2-2.6-6.7c0-.6.3-1.1.8-1.4.5-.2 1.1-.2 1.6.1.4.3.7.6 1 1h.9V6.5h2v2.1h2V6.5h2v2.1h2V6.5h2v2.6c1.5.5 2.5 1.5 2.9 3 .1.3.1.5.1.8z" },
];

export function HeroSection() {
  const handleStartGardening = () => {
    const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
    const redirectUri = `${window.location.origin}/callback`;
    const githubUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=repo`;

    window.location.href = githubUrl;
  };

  return (
    <section className="relative px-6 pt-24 pb-16 lg:px-8 lg:pt-32 lg:pb-24">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Left Content */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center lg:text-left"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1, duration: 0.4 }}
              className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm text-muted-foreground"
            >
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
              Now in Public Beta
            </motion.div>

            {/* Headline */}
            <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl text-balance">
              Your Personal{" "}
              <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
                AI DevOps
              </span>{" "}
              Engineer.
            </h1>

            {/* Subtext */}
            <p className="mt-6 text-lg leading-relaxed text-muted-foreground max-w-xl mx-auto lg:mx-0 text-pretty">
              Automate documentation, fix broken builds, and generate
              professional portfolios in seconds.
            </p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.4 }}
              className="mt-8 flex flex-col sm:flex-row gap-4 justify-center lg:justify-start"
            >
              <Button
                size="lg"
                onClick={handleStartGardening}
                className="group relative overflow-hidden bg-foreground text-background hover:bg-foreground/90 shadow-[0_0_20px_rgba(255,255,255,0.3)] hover:shadow-[0_0_30px_rgba(255,255,255,0.4)] transition-all duration-300"
              >
                <Github className="mr-2 h-4 w-4" />
                Start Gardening
                <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-white/20 bg-transparent hover:bg-white/5 text-foreground"
              >
                <Play className="mr-2 h-4 w-4" />
                View Demo
              </Button>
            </motion.div>

            {/* Social Proof */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.6 }}
              className="mt-12 pt-8 border-t border-white/10"
            >
              <p className="text-xs text-muted-foreground uppercase tracking-widest mb-4">
                Works with your favorite tools
              </p>
              <div className="flex items-center justify-center lg:justify-start gap-8">
                {techLogos.map((logo) => (
                  <div
                    key={logo.name}
                    className="opacity-40 hover:opacity-70 transition-opacity"
                    title={logo.name}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      className="h-8 w-8 fill-current text-foreground"
                      aria-label={logo.name}
                    >
                      <path d={logo.svg} />
                    </svg>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>

          {/* Right Content - Code Terminal */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
            className="relative"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-green-500/20 to-emerald-500/20 blur-3xl -z-10 rounded-full" />
            <CodeTerminal />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
