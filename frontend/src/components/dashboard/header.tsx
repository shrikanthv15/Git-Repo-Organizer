"use client";

import { RefreshCw, Zap, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

interface HeaderProps {
    onAnalyzeAll: () => void;
    onRefresh: () => void;
    isAnalyzing: boolean;
    isRefreshing: boolean;
    isBackendDown?: boolean;
    batchStatus?: { completed: number; total: number } | null;
}

export function DashboardHeader({
    onAnalyzeAll,
    onRefresh,
    isAnalyzing,
    isRefreshing,
    isBackendDown,
    batchStatus
}: HeaderProps) {
    return (
        <header className="relative z-10 flex flex-col border-b border-white/10 bg-card/50 backdrop-blur-sm">
            <div className="flex h-16 items-center justify-between px-6">
                <div className="flex items-center gap-3">
                    <h1 className="text-xl font-semibold text-foreground">
                        <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">Mission</span> Control
                    </h1>
                    {isBackendDown && (
                        <span className="flex items-center gap-1.5 rounded-full bg-yellow-900/20 px-2.5 py-0.5 text-xs font-medium text-yellow-400">
                            <WifiOff className="h-3 w-3" />
                            Offline
                        </span>
                    )}
                    {!isBackendDown && (
                        <span className="rounded-full bg-green-900/20 px-2.5 py-0.5 text-xs font-medium text-green-400">
                            Online
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    {/* Refresh button - fetches fresh data from DB */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onRefresh}
                        disabled={isRefreshing}
                        className="text-muted-foreground hover:bg-white/5 hover:text-foreground"
                        title="Refresh data from server"
                    >
                        <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
                    </Button>

                    {/* Analyze All button */}
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={onAnalyzeAll}
                        disabled={isAnalyzing}
                        className="border-white/10 bg-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground hover:border-white/20 transition-all duration-300"
                    >
                        {isAnalyzing ? (
                            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Zap className="mr-2 h-4 w-4" />
                        )}
                        {isAnalyzing ? "Analyzing..." : "Analyze All"}
                    </Button>
                    <Avatar className="h-8 w-8 border border-white/10">
                        <AvatarImage src="https://avatar.vercel.sh/gardener" alt="User" />
                        <AvatarFallback className="bg-secondary text-xs text-muted-foreground">
                            GG
                        </AvatarFallback>
                    </Avatar>
                </div>
            </div>

            {/* Batch progress bar */}
            {isAnalyzing && batchStatus && batchStatus.total > 0 && (
                <div className="px-6 pb-3">
                    <div className="mb-1 flex justify-between text-xs font-medium text-muted-foreground">
                        <span>Analyzed {batchStatus.completed}/{batchStatus.total}</span>
                        <span>{Math.round((batchStatus.completed / batchStatus.total) * 100)}%</span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                        <div
                            className="h-full bg-gradient-to-r from-green-500 to-emerald-500 transition-all duration-500 ease-out"
                            style={{ width: `${(batchStatus.completed / batchStatus.total) * 100}%` }}
                        />
                    </div>
                </div>
            )}
        </header>
    );
}

