"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Repo } from "@/app/dashboard/page";
import {
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Shield,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface RepoDetailSheetProps {
  repo: Repo | null;
  open: boolean;
  onClose: () => void;
}

const mockLogs = [
  { type: "info", message: "Scanning repository structure..." },
  { type: "info", message: "Analyzing 142 files across 23 directories" },
  { type: "success", message: "TypeScript configuration: Valid" },
  { type: "warning", message: "Found 3 deprecated dependencies" },
  { type: "error", message: "Security vulnerability in lodash@4.17.15" },
  { type: "info", message: "Checking CI/CD pipeline configuration..." },
  { type: "success", message: "GitHub Actions workflow: Healthy" },
  { type: "info", message: "Generating fix recommendations..." },
];

const mockFixes = [
  {
    id: "1",
    title: "Update deprecated dependencies",
    description: "Upgrade 3 packages to their latest versions",
    icon: FileCode,
    priority: "medium",
  },
  {
    id: "2",
    title: "Patch security vulnerability",
    description: "Update lodash to v4.17.21 to fix CVE-2021-23337",
    icon: Shield,
    priority: "high",
  },
  {
    id: "3",
    title: "Optimize bundle size",
    description: "Tree-shake unused exports to reduce bundle by 23%",
    icon: Zap,
    priority: "low",
  },
];

export function RepoDetailSheet({ repo, open, onClose }: RepoDetailSheetProps) {
  if (!repo) return null;

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full border-white/10 bg-card/95 backdrop-blur-xl sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="text-foreground">
            <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">{repo.name}</span>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-6 flex flex-col gap-6">
          <div>
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">
              Analysis Log
            </h4>
            <div className="rounded-xl border border-white/10 bg-secondary/50 p-3 font-mono text-xs">
              <ScrollArea className="h-48">
                <div className="flex flex-col gap-1.5">
                  {mockLogs.map((log, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-muted-foreground/50">$</span>
                      <span
                        className={cn(
                          log.type === "success" && "text-green-400",
                          log.type === "warning" && "text-amber-400",
                          log.type === "error" && "text-red-400",
                          log.type === "info" && "text-muted-foreground"
                        )}
                      >
                        {log.message}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground/50">$</span>
                    <span className="inline-block h-3 w-1.5 animate-pulse bg-green-400" />
                  </div>
                </div>
              </ScrollArea>
            </div>
          </div>

          <div>
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">
              Available Fixes
            </h4>
            <div className="flex flex-col gap-2">
              {mockFixes.map((fix) => (
                <div
                  key={fix.id}
                  className="group flex items-center gap-3 rounded-xl border border-white/10 bg-secondary/50 p-3 transition-all duration-300 hover:bg-secondary/80 hover:border-white/20"
                >
                  <div
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-lg",
                      fix.priority === "high" && "bg-red-500/10 text-red-400",
                      fix.priority === "medium" &&
                        "bg-amber-500/10 text-amber-400",
                      fix.priority === "low" &&
                        "bg-green-500/10 text-green-400"
                    )}
                  >
                    <fix.icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">{fix.title}</p>
                    <p className="text-xs text-muted-foreground">{fix.description}</p>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs text-green-400 opacity-0 transition-opacity hover:bg-green-500/10 hover:text-green-300 group-hover:opacity-100"
                  >
                    Apply
                  </Button>
                </div>
              ))}
            </div>
          </div>

          <Button className="mt-auto w-full bg-gradient-to-r from-green-500 to-emerald-500 text-background font-medium hover:from-green-400 hover:to-emerald-400 shadow-[0_0_20px_rgba(34,197,94,0.3)]">
            <CheckCircle2 className="mr-2 h-4 w-4" />
            Apply All Fixes
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
