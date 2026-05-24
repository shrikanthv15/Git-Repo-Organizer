# frontend/

Next.js 16 App Router + TypeScript + Tailwind + shadcn/ui (Radix) +
TanStack React Query + framer-motion. Managed via `pnpm`.

## Run frontend alone

```bash
cd frontend
pnpm install
pnpm dev          # http://localhost:3000
pnpm build        # production build (turbopack)
pnpm lint         # eslint
```

Needs the backend API reachable at `NEXT_PUBLIC_API_BASE_URL`
(default: `http://localhost:8000`).

## Code layout (post-E1b / E4)

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── page.tsx                  # /            (landing)
│   ├── callback/page.tsx         # /callback    (OAuth callback)
│   ├── dashboard/page.tsx        # /dashboard   (repo grid)
│   ├── portfolio/page.tsx        # /portfolio   (portfolio studio)
│   ├── repo/[repoId]/page.tsx    # /repo/<id>   (per-repo detail)
│   ├── error.tsx                 # page-level error boundary (E4)
│   └── global-error.tsx          # root-layout error boundary (E4)
├── components/
│   ├── dashboard/
│   │   ├── repo-detail-sheet.tsx       # main RepoDetailSheet orchestration (post-E1b split)
│   │   ├── draft-proposal-editor.tsx   # extracted draft editor (E1b)
│   │   ├── repo-card.tsx               # repo grid card
│   │   └── …
│   ├── landing/                  # landing-page sections
│   └── ui/                       # shadcn/ui primitives (Button, Sheet, ScrollArea, …)
├── hooks/
│   ├── use-gardener.ts           # React Query hooks for all API interactions
│   └── use-draft-proposal.ts     # editor state hook (E1b)
├── lib/
│   ├── utils.ts                  # cn() helper for Tailwind class merging
│   └── logger.ts                 # console.log/error wrapper (E4)
├── services/
│   └── api.ts                    # Axios client with auth interceptor
└── types/
    └── api.ts                    # TypeScript interfaces matching backend Pydantic
```

## How to add a new App Router page

1. Create `app/<route-path>/page.tsx`. Default-export a React component.
2. If it needs client-side state or interactivity, add `"use client";` at the top — otherwise let it be a server component (RSC).
3. For dynamic routes: `app/foo/[id]/page.tsx` — the param is in `params.id`.
4. For auth-gated pages: read the token from localStorage on the client, redirect to `/` if missing. (Server-side auth not yet wired.)

## How the React Query hook works (`hooks/use-gardener.ts`)

Pattern: one hook file exports many small hooks. Each hook wraps either
a query or a mutation:

```ts
export function useRepos() {
    return useQuery({
        queryKey: ["repos"],
        queryFn: async (): Promise<Repo[]> => {
            const { data } = await gardenApi.getRepos();
            return Array.isArray(data) ? data : [];
        },
        // Smart polling: only when a repo is actively drafting
        refetchInterval: (query) => {
            const repos = query.state.data;
            return repos?.some((r) => r.health?.status === "drafting_docs") ? 3_000 : false;
        },
    });
}
```

Mutations follow the same pattern; on success they call
`queryClient.invalidateQueries(["repos"])` to refetch.

For self-contained editor state (like the draft-proposal flow) we
extract into focused hooks like `useDraftProposal` — see
`hooks/use-draft-proposal.ts` for the pattern.

## Logging + error boundaries (E4)

`lib/logger.ts` wraps `console.log/error` with route context. Use it in
client components for non-error info. For uncaught errors, the App
Router boundaries (`app/error.tsx`, `app/global-error.tsx`) render a
nice fallback UI and POST the error to `/api/log` if
`NEXT_PUBLIC_LOG_ENDPOINT` is set.

## Environment variables

Set via `.env.local` (gitignored) or Vercel/Coolify UI:

- `NEXT_PUBLIC_API_BASE_URL` — backend API URL (default `http://localhost:8000`)
- `NEXT_PUBLIC_GITHUB_CLIENT_ID` — for the OAuth redirect URL
- `NEXT_PUBLIC_LOG_ENDPOINT` — optional, where error boundary posts to (default `/api/log`)
