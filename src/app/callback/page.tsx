"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/services/api";
import { Rocket, AlertTriangle, Terminal } from "lucide-react";
import { AxiosError } from "axios";

interface ErrorDetails {
    status?: number;
    url?: string;
    message: string;
}

export default function CallbackPage() {
    const searchParams = useSearchParams();
    const router = useRouter();
    const [status, setStatus] = useState<"processing" | "failed">("processing");
    const [errorDetails, setErrorDetails] = useState<ErrorDetails | null>(null);

    useEffect(() => {
        const code = searchParams.get("code");

        if (!code) {
            setStatus("failed");
            setErrorDetails({ message: "No OAuth code received from GitHub." });
            return;
        }

        const exchangeCode = async () => {
            // Explicitly construct URL for visibility
            const targetUrl = "/auth/exchange";
            console.log("Attempting Handshake:", targetUrl, "with code:", code);

            try {
                const response = await api.post(targetUrl, { code });
                const { access_token } = response.data;

                localStorage.setItem("access_token", access_token);
                router.push("/dashboard");
            } catch (error) {
                console.error("Auth Failed", error);
                setStatus("failed");

                if (error instanceof AxiosError) {
                    setErrorDetails({
                        status: error.response?.status,
                        url: error.config?.url || targetUrl,
                        message: error.message,
                    });
                } else {
                    setErrorDetails({ message: "An unexpected error occurred." });
                }
            }
        };

        exchangeCode();
    }, [searchParams, router]);

    if (status === "failed") {
        return (
            <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-4 dark:bg-black">
                <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-xl dark:bg-zinc-900 border border-gray-200 dark:border-zinc-800">
                    <div className="mb-6 flex flex-col items-center text-center">
                        <AlertTriangle className="h-12 w-12 text-red-500 mb-4" />
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                            Authentication Failed
                        </h1>
                    </div>

                    {/* Diagnostic Card */}
                    <div className="bg-gray-100 dark:bg-zinc-950 rounded-lg p-4 font-mono text-sm mb-6 overflow-x-auto">
                        <div className="flex items-center gap-2 mb-2 text-gray-500 border-b border-gray-200 pb-2 dark:border-zinc-800">
                            <Terminal className="h-4 w-4" />
                            <span>System Diagnostics</span>
                        </div>

                        {errorDetails?.status === 404 && (
                            <div className="space-y-2">
                                <p className="text-red-600 font-bold">Error 404: Endpoint Not Found</p>
                                <p>Tried to POST to:</p>
                                <p className="bg-gray-200 dark:bg-zinc-900 p-2 rounded text-xs break-all">
                                    {errorDetails.url ? `${process.env.NEXT_PUBLIC_API_BASE_URL}${errorDetails.url}` : "Unknown URL"}
                                </p>
                                <p className="text-gray-500 italic mt-2">
                                    Action: Verify `auth/exchange` route exists in Backend `routers/auth.py`.
                                </p>
                            </div>
                        )}

                        {errorDetails?.status === 401 && (
                            <div className="space-y-2">
                                <p className="text-orange-600 font-bold">Token Rejected (401)</p>
                                <p>The backend refused the code using:</p>
                                <p className="text-xs text-gray-500">{errorDetails.message}</p>
                            </div>
                        )}

                        {!errorDetails?.status && (
                            <div className="text-red-600">
                                {errorDetails?.message}
                            </div>
                        )}
                    </div>

                    <button
                        onClick={() => router.push("/login")}
                        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white hover:bg-blue-700 transition-colors"
                    >
                        Return to Login
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-black">
            <Rocket className="h-12 w-12 animate-bounce text-blue-600" />
            <h1 className="text-xl font-medium text-gray-900 dark:text-white">
                Establishing Secure Link...
            </h1>
        </div>
    );
}
