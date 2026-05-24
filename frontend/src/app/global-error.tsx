"use client";
import { useEffect } from "react";
import { ErrorLog } from "@/lib/logger";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    ErrorLog.error("root_error", {
      message: error.message,
      digest: error.digest,
      stack: error.stack,
    });
  }, [error]);

  return (
    <html>
      <body>
        <div className="flex items-center justify-center min-h-screen bg-red-950">
          <div className="text-center max-w-md mx-auto px-4">
            <h1 className="text-3xl font-bold text-red-400 mb-2">Critical Error</h1>
            <p className="text-muted-foreground text-sm mb-4">
              The application encountered a fatal error.
            </p>
            <button
              onClick={reset}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-white transition-colors"
            >
              Reload
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
