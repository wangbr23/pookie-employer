"use client";

import { useCallback, useEffect, useState } from "react";
import type { JobSummaryResponse } from "@/lib/api-types";
import { listJobs, dismissJob } from "@/lib/api";
import { JobCard } from "./job-card";

const PAGE_SIZE = 20;

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "loaded";
      jobs: JobSummaryResponse[];
      total: number;
      offset: number;
    };

export function SavedView({
  onTotalChange,
}: {
  onTotalChange?: (n: number) => void;
}) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await listJobs({
          status: ["saved"],
          search: search || undefined,
          limit: PAGE_SIZE,
          offset,
        });
        if (cancelled) return;
        setState({
          status: "loaded",
          jobs: res.items,
          total: res.total,
          offset,
        });
        onTotalChange?.(res.total);
      } catch (err) {
        if (cancelled) return;
        setState({
          status: "error",
          message: err instanceof Error ? err.message : "Failed to load saved jobs",
        });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [search, offset, onTotalChange]);

  const handleDismiss = useCallback(
    async (jobId: string, reasons: string[], freeText?: string) => {
      await dismissJob(jobId, { reasons, free_text: freeText });
      setState((prev) => {
        if (prev.status !== "loaded") return prev;
        return {
          ...prev,
          jobs: prev.jobs.filter((j) => j.id !== jobId),
          total: prev.total - 1,
        };
      });
    },
    [],
  );

  const totalPages =
    state.status === "loaded" ? Math.ceil(state.total / PAGE_SIZE) : 0;
  const currentPage =
    state.status === "loaded" ? Math.floor(state.offset / PAGE_SIZE) + 1 : 1;

  return (
    <div className="max-w-6xl">
      <header className="mb-8 flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
          Saved
        </p>
        <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
          Saved jobs
        </h1>
      </header>

      <div className="mb-6">
        <input
          type="text"
          placeholder="Search saved jobs..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="w-full rounded-full border border-stone-200 bg-white/80 px-5 py-2.5 text-sm text-stone-700 placeholder:text-stone-400 focus:border-fuchsia-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-200 sm:max-w-xs"
        />
      </div>

      {state.status === "loading" && (
        <p className="py-12 text-center text-stone-500">Loading saved jobs...</p>
      )}

      {state.status === "error" && (
        <p className="py-12 text-center text-red-600">{state.message}</p>
      )}

      {state.status === "loaded" && state.jobs.length === 0 && (
        <p className="py-12 text-center text-stone-500">
          {search
            ? "No saved jobs match your search."
            : "No saved jobs yet. Save jobs you're interested in to see them here."}
        </p>
      )}

      {state.status === "loaded" && state.jobs.length > 0 && (
        <>
          <p className="mb-4 text-sm text-stone-500">
            Showing {state.offset + 1}–
            {Math.min(state.offset + state.jobs.length, state.total)} of{" "}
            {state.total} saved {state.total === 1 ? "job" : "jobs"}
          </p>
          <div className="space-y-5">
            {state.jobs.map((job) => (
              <JobCard key={job.id} job={job} onDismiss={handleDismiss} />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-3">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="rounded-full border border-stone-200 bg-white/70 px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-white disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-stone-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="rounded-full border border-stone-200 bg-white/70 px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-white disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
