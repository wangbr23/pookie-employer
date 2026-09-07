"use client";

import { useEffect, useState } from "react";
import type { JobSummaryResponse, FitBucket } from "@/lib/api-types";
import { listJobs } from "@/lib/api";
import { JobCard } from "./job-card";

const PAGE_SIZE = 20;

const BUCKET_FILTERS: { value: FitBucket | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "strong", label: "Strong Fit" },
  { value: "possible", label: "Good Fit" },
  { value: "stretch", label: "Stretch" },
  { value: "needs_review", label: "Needs Review" },
];

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | {
      status: "loaded";
      jobs: JobSummaryResponse[];
      total: number;
      offset: number;
    };

export function AllJobsView({
  onTotalChange,
}: {
  onTotalChange?: (n: number) => void;
}) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [search, setSearch] = useState("");
  const [activeBucket, setActiveBucket] = useState<FitBucket | "all">("all");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await listJobs({
          status: ["new", "seen", "saved"],
          fit_bucket: activeBucket === "all" ? undefined : [activeBucket],
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
          message: err instanceof Error ? err.message : "Failed to load jobs",
        });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [search, activeBucket, offset, onTotalChange]);

  const totalPages =
    state.status === "loaded" ? Math.ceil(state.total / PAGE_SIZE) : 0;
  const currentPage =
    state.status === "loaded" ? Math.floor(state.offset / PAGE_SIZE) + 1 : 1;

  return (
    <div className="max-w-6xl">
      <header className="mb-8 flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
          All Jobs
        </p>
        <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
          Browse jobs
        </h1>
      </header>

      {/* Filters */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Search by title or company..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="w-full rounded-full border border-stone-200 bg-white/80 px-5 py-2.5 text-sm text-stone-700 placeholder:text-stone-400 focus:border-fuchsia-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-200 sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-2">
          {BUCKET_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => {
                setActiveBucket(f.value);
                setOffset(0);
              }}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                activeBucket === f.value
                  ? "bg-gradient-to-r from-fuchsia-400 to-pink-500 text-white shadow-md shadow-pink-200"
                  : "border border-stone-200 bg-white/70 text-stone-600 hover:bg-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {state.status === "loading" && (
        <p className="py-12 text-center text-stone-500">Loading jobs...</p>
      )}

      {state.status === "error" && (
        <p className="py-12 text-center text-red-600">{state.message}</p>
      )}

      {state.status === "loaded" && state.jobs.length === 0 && (
        <p className="py-12 text-center text-stone-500">
          {search || activeBucket !== "all"
            ? "No jobs match your filters."
            : "No active jobs yet. Try running a refresh."}
        </p>
      )}

      {state.status === "loaded" && state.jobs.length > 0 && (
        <>
          <p className="mb-4 text-sm text-stone-500">
            Showing {state.offset + 1}–
            {Math.min(state.offset + state.jobs.length, state.total)} of{" "}
            {state.total} jobs
          </p>
          <div className="space-y-5">
            {state.jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>

          {/* Pagination */}
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
