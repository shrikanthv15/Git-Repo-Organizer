"use client";

import { Home, Briefcase, Settings, Leaf } from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const navItems = [
  { id: "home", icon: Home, label: "Home" },
  { id: "portfolio", icon: Briefcase, label: "Portfolio" },
  { id: "settings", icon: Settings, label: "Settings" },
];

export function DashboardSidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="relative z-10 flex w-16 flex-col items-center border-r border-white/10 bg-card/50 backdrop-blur-sm py-4">
      <div className="mb-8 flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20">
        <Leaf className="h-5 w-5 text-green-400" />
      </div>
      <nav className="flex flex-1 flex-col items-center gap-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onTabChange(item.id)}
            className={cn(
              "group relative flex h-10 w-10 items-center justify-center rounded-lg transition-all duration-300",
              activeTab === item.id
                ? "bg-white/10 text-foreground"
                : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
            )}
            aria-label={item.label}
          >
            {activeTab === item.id && (
              <span className="absolute left-0 h-6 w-0.5 rounded-r bg-gradient-to-b from-green-400 to-emerald-500 shadow-[0_0_8px_2px_rgba(34,197,94,0.5)]" />
            )}
            <item.icon className="h-5 w-5" />
          </button>
        ))}
      </nav>
    </aside>
  );
}
