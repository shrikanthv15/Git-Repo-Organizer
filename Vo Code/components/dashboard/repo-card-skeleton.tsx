import { Skeleton } from "@/components/ui/skeleton";

export function RepoCardSkeleton() {
  return (
    <div className="rounded-2xl border border-white/10 bg-card/50 backdrop-blur-sm p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Skeleton className="h-5 w-32 bg-white/5" />
          <Skeleton className="mt-2 h-4 w-20 bg-white/5" />
        </div>
        <Skeleton className="h-12 w-12 rounded-full bg-white/5" />
      </div>
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-3 w-24 bg-white/5" />
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-14 rounded-full bg-white/5" />
          <Skeleton className="h-5 w-10 rounded-full bg-white/5" />
        </div>
      </div>
    </div>
  );
}
