"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { gardenApi } from "@/services/api";
import { Rocket, AlertTriangle, Terminal } from "lucide-react";
import { AxiosError } from "axios";

interface ErrorDetails {
    status?: number;
    url?: string;
    message: string;
}

function CallbackContent() {
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
            try {
                const { data } = await gardenApi.exchangeAuth(code);
                localStorage.setItem("access_token", data.access_token);
                router.push("/dashboard");
            } catch (error) {
                console.error("Auth exchange failed:", error);
                setStatus("failed");

                if (error instanceof AxiosError) {
                    setErrorDetails({
                        status: error.response?.status,
                        url: error.config?.url,
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
                <div className="w-full max-w-lg rounded-2xl border border-gray-200 bg-white p-8 shadow-xl dark:border-zinc-800 dark:bg-zinc-900">
                    <div className="mb-6 flex flex-col items-center text-center">
                        <AlertTriangle className="mb-4 h-12 w-12 text-red-500" />
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                            Authentication Failed
                        </h1>
                    </div>

                    <div className="mb-6 overflow-x-auto rounded-lg bg-gray-100 p-4 font-mono text-sm dark:bg-zinc-950">
                        <div className="mb-2 flex items-center gap-2 border-b border-gray-200 pb-2 text-gray-500 dark:border-zinc-800">
                            <Terminal className="h-4 w-4" />
                            <span>System Diagnostics</span>
                        </div>

                        {errorDetails?.status === 404 && (
                            <div className="space-y-2">
                                <p className="font-bold text-red-600">
                                    Error 404: Endpoint Not Found
                                </p>
                                <p>
                                    Verify the backend is running and{" "}
                                    <code>/api/auth/exchange</code> route exists.
                                </p>
                            </div>
                        )}

                        {errorDetails?.status === 400 && (
                            <div className="space-y-2">
                                <p className="font-bold text-orange-600">
                                    Bad Request (400)
                                </p>
                                <p className="text-xs text-gray-500">
                                    The OAuth code may have expired. Try logging in
                                    again.
                                </p>
                            </div>
                        )}

                        {errorDetails?.status === 401 && (
                            <div className="space-y-2">
                                <p className="font-bold text-orange-600">
                                    Token Rejected (401)
                                </p>
                                <p className="text-xs text-gray-500">
                                    {errorDetails.message}
                                </p>
                            </div>
                        )}

                        {errorDetails?.status === 502 && (
                            <div className="space-y-2">
                                <p className="font-bold text-orange-600">
                                    Gateway Error (502)
                                </p>
                                <p className="text-xs text-gray-500">
                                    Backend could not reach GitHub. Check
                                    GITHUB_CLIENT_SECRET.
                                </p>
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
                        className="w-full rounded-lg bg-blue-600 px-4 py-3 font-semibold text-white transition-colors hover:bg-blue-700"
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

export default function CallbackPage() {
    return (
        <Suspense
            fallback={
                <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-black">
                    <Rocket className="h-12 w-12 animate-bounce text-blue-600" />
                </div>
            }
        >
            <CallbackContent />
        </Suspense>
    );
}
