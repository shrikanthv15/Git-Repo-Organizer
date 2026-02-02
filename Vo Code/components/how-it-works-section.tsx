"use client";

import { motion } from "framer-motion";
import { Github, Cpu, GitMerge } from "lucide-react";

const steps = [
  {
    icon: Github,
    title: "Connect GitHub",
    description:
      "Link your GitHub account with one click. We securely access your repositories with granular permissions.",
    number: "01",
  },
  {
    icon: Cpu,
    title: "AI Scans Code",
    description:
      "Our AI analyzes your codebase, understanding patterns, detecting issues, and identifying improvement opportunities.",
    number: "02",
  },
  {
    icon: GitMerge,
    title: "Review & Merge",
    description:
      "Review AI-generated fixes and enhancements, then merge with confidence. Full control, zero surprises.",
    number: "03",
  },
];

export function HowItWorksSection() {
  return (
    <section className="relative px-6 py-24 lg:px-8">
      <div className="mx-auto max-w-4xl">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl text-balance">
            How it{" "}
            <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
              works
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            Get started in minutes. No complex setup or configuration required.
          </p>
        </motion.div>

        {/* Timeline */}
        <div className="relative">
          {/* Vertical Line */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-green-500/50 via-emerald-500/30 to-transparent hidden md:block" />

          <div className="space-y-12">
            {steps.map((step, index) => (
              <motion.div
                key={step.title}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.15 }}
                className="relative flex gap-6 md:gap-8"
              >
                {/* Step Number & Icon */}
                <div className="relative flex-shrink-0">
                  <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-white/10 bg-card/80 backdrop-blur-sm">
                    <step.icon className="h-7 w-7 text-green-400" />
                  </div>
                  {/* Glow */}
                  <div className="absolute inset-0 -z-10 rounded-2xl bg-green-500/20 blur-xl" />
                </div>

                {/* Content */}
                <div className="flex-1 pt-2">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-mono text-green-400/70">
                      {step.number}
                    </span>
                    <h3 className="text-xl font-semibold text-foreground">
                      {step.title}
                    </h3>
                  </div>
                  <p className="text-muted-foreground leading-relaxed max-w-lg">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
