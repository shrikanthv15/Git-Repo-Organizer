"use client";

import { motion } from "framer-motion";
import { Wrench, Sparkles, Microscope, GitBranch, Shield, Zap } from "lucide-react";

const features = [
  {
    icon: Wrench,
    title: "Auto-Fixer",
    description:
      "Automatically detect and fix bugs, syntax errors, and common issues across your entire codebase.",
    gradient: "from-orange-500/20 to-red-500/20",
    iconColor: "text-orange-400",
  },
  {
    icon: Sparkles,
    title: "Portfolio Architect",
    description:
      "Generate stunning developer portfolios from your GitHub activity and project contributions.",
    gradient: "from-purple-500/20 to-pink-500/20",
    iconColor: "text-purple-400",
  },
  {
    icon: Microscope,
    title: "Deep Analysis",
    description:
      "AI-powered code review that catches security vulnerabilities, performance issues, and tech debt.",
    gradient: "from-blue-500/20 to-cyan-500/20",
    iconColor: "text-blue-400",
  },
  {
    icon: GitBranch,
    title: "Smart Branching",
    description:
      "Intelligent branch management with automated PR descriptions and merge conflict resolution.",
    gradient: "from-green-500/20 to-emerald-500/20",
    iconColor: "text-green-400",
  },
  {
    icon: Shield,
    title: "Security Guard",
    description:
      "Continuous security scanning with automatic dependency updates and vulnerability patches.",
    gradient: "from-red-500/20 to-rose-500/20",
    iconColor: "text-red-400",
  },
  {
    icon: Zap,
    title: "Instant Docs",
    description:
      "Auto-generate comprehensive documentation, READMEs, and API references from your code.",
    gradient: "from-yellow-500/20 to-amber-500/20",
    iconColor: "text-yellow-400",
  },
];

export function FeaturesSection() {
  return (
    <section className="relative px-6 py-24 lg:px-8">
      <div className="mx-auto max-w-7xl">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl text-balance">
            Everything you need to{" "}
            <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">
              grow your code
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            A complete AI-powered toolkit for modern developers who want to ship
            faster and maintain cleaner codebases.
          </p>
        </motion.div>

        {/* Bento Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="group relative"
            >
              {/* Hover gradient border effect */}
              <div className="absolute -inset-px rounded-2xl bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 from-green-500/50 via-emerald-500/50 to-teal-500/50 blur-sm" />

              <div className="relative h-full rounded-2xl border border-white/10 bg-card/50 backdrop-blur-sm p-6 transition-all duration-300 hover:border-white/20 hover:bg-card/80">
                {/* Icon */}
                <div
                  className={`mb-4 inline-flex items-center justify-center rounded-xl bg-gradient-to-br ${feature.gradient} p-3`}
                >
                  <feature.icon className={`h-6 w-6 ${feature.iconColor}`} />
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
