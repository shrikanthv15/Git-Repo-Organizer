"use client";

import { Github } from "lucide-react";

export default function LoginPage() {
    const handleLogin = () => {
        const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
        const redirectUri = `${window.location.origin}/callback`;
        const githubUrl = `https://github.com/login/oauth/authorize?client_id=${clientId}&redirect_uri=${redirectUri}&scope=repo`;

        window.location.href = githubUrl;
    };

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 dark:bg-black">
            <div className="w-full max-w-md space-y-8 rounded-2xl bg-white p-10 shadow-xl dark:bg-zinc-900">
                <div className="text-center">
                    <h2 className="mt-2 text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
                        Welcome Gardener
                    </h2>
                    <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                        Sign in to access Mission Control
                    </p>
                </div>

                <button
                    onClick={handleLogin}
                    className="flex w-full items-center justify-center gap-3 rounded-lg bg-black px-4 py-3 text-white transition-opacity hover:opacity-90 dark:bg-white dark:text-black"
                >
                    <Github className="h-5 w-5" />
                    Connect with GitHub
                </button>
            </div>
        </div>
    );
}
