"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

interface HeaderProps {
  onRefresh: () => void;
  isLoading: boolean;
}

export function DashboardHeader({ onRefresh, isLoading }: HeaderProps) {
  return (
    <header className="relative z-10 flex h-16 items-center justify-between border-b border-white/10 bg-card/50 backdrop-blur-sm px-6">
      <h1 className="text-xl font-semibold text-foreground">
        <span className="bg-gradient-to-r from-green-400 to-emerald-500 bg-clip-text text-transparent">Mission</span> Control
      </h1>
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={isLoading}
          className="border-white/10 bg-transparent text-muted-foreground hover:bg-white/5 hover:text-foreground hover:border-white/20 transition-all duration-300"
        >
          <RefreshCw
            className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")}
          />
          Refresh
        </Button>
        <Avatar className="h-8 w-8 border border-white/10">
          <AvatarImage src="https://avatar.vercel.sh/gardener" alt="User" />
          <AvatarFallback className="bg-secondary text-xs text-muted-foreground">
            GG
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
