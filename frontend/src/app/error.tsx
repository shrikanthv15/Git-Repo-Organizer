"use client";
import { useEffect } from "react";
import { ErrorLog } from "@/lib/logger";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLog.error("page_error", {
      message: error.message,
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-red-900/20">
      <div className="text-center max-w-md mx-auto px-4">
        <h2 className="text-2xl font-bold text-red-400 mb-2">Something went wrong</h2>
        <p className="text-muted-foreground text-sm mb-4">{error.message}</p>
        <button
          onClick={reset}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-white transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
