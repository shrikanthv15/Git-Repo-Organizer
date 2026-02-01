import { useQuery } from "@tanstack/react-query";
import axios from "axios";
import { type Repo } from "./api-contract";

export function useRepos() {
    return useQuery({
        queryKey: ["repos"],
        queryFn: async (): Promise<Repo[]> => {
            // Feature Flag: Mock Mode
            if (process.env.NEXT_PUBLIC_USE_MOCK === "true") {
                await new Promise((resolve) => setTimeout(resolve, 1000)); // Simulate latency

                return [
                    {
                        id: "1",
                        name: "legacy-monolith",
                        health_score: 45,
                        needs_gardening: true,
                        url: "#",
                    },
                    {
                        id: "2",
                        name: "greenfield-app",
                        health_score: 92,
                        needs_gardening: false,
                        url: "#",
                    },
                    {
                        id: "3",
                        name: "utils-library",
                        health_score: 12,
                        needs_gardening: true,
                        url: "#",
                    },
                ];
            }

            // Real API Call
            const response = await axios.get(
                `${process.env.NEXT_PUBLIC_API_URL}/repos`
            );
            return response.data;
        },
    });
}
