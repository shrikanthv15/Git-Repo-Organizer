const LOG_ENDPOINT = process.env.NEXT_PUBLIC_LOG_ENDPOINT;
const DEFAULT_CONTEXT = {
  route: typeof window !== "undefined" ? window.location.pathname : "unknown",
  userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
  timestamp: new Date().toISOString(),
};

export const ErrorLog = {
  error: async (message: string, context?: Record<string, any>) => {
    const payload = { ...DEFAULT_CONTEXT, ...context, level: "error", message };
    console.error(`[${payload.route}]`, message, context);

    if (LOG_ENDPOINT) {
      try {
        await fetch(LOG_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(() => {});
      } catch (e) {
        // Ignore
      }
    }
  },

  info: async (message: string, context?: Record<string, any>) => {
    const payload = { ...DEFAULT_CONTEXT, ...context, level: "info", message };
    console.info(`[${payload.route}]`, message, context);

    if (LOG_ENDPOINT) {
      try {
        await fetch(LOG_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }).catch(() => {});
      } catch (e) {
        // Ignore
      }
    }
  },
};
