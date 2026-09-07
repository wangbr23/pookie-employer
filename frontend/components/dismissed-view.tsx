"use client";

import { useEffect, useState } from "react";
import type { JobSummaryResponse, JobStatus } from "@/lib/api-types";
import { listJobs } from "@/lib/api";
import { JobCard } from "./job-card";

const PAGE_SIZE = 20;

type StatusFilter = "all" | "dismissed" | "possibly_closed" | "closed_archived";

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "dismissed", label: "Dismissed" },
  { value: "possibly_closed", label: "Possibly Closed" },
  { value: "closed_archived", label: "Archived" },
];

const ALL_DISMISSED_STATUSES: JobStatus[] = [
  "dismissed",
  "possibly_closed",
  "closed_archived",
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

export function DismissedView({
  onTotalChange,
}: {
  onTotalChange?: (n: number) => void;
}) {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<StatusFilter>("all");
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const statuses: JobStatus[] =
          activeFilter === "all" ? ALL_DISMISSED_STATUSES : [activeFilter];
        const res = await listJobs({
          status: statuses,
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
          message:
            err instanceof Error ? err.message : "Failed to load dismissed jobs",
        });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [search, activeFilter, offset, onTotalChange]);

  const totalPages =
    state.status === "loaded" ? Math.ceil(state.total / PAGE_SIZE) : 0;
  const currentPage =
    state.status === "loaded" ? Math.floor(state.offset / PAGE_SIZE) + 1 : 1;

  return (
    <div className="max-w-6xl">
      <header className="mb-8 flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
          Dismissed
        </p>
        <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
          Dismissed & archived
        </h1>
      </header>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Search dismissed jobs..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="w-full rounded-full border border-stone-200 bg-white/80 px-5 py-2.5 text-sm text-stone-700 placeholder:text-stone-400 focus:border-fuchsia-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-200 sm:max-w-xs"
        />
        <div className="flex flex-wrap gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              onClick={() => {
                setActiveFilter(f.value);
                setOffset(0);
              }}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                activeFilter === f.value
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
        <p className="py-12 text-center text-stone-500">
          Loading dismissed jobs...
        </p>
      )}

      {state.status === "error" && (
        <p className="py-12 text-center text-red-600">{state.message}</p>
      )}

      {state.status === "loaded" && state.jobs.length === 0 && (
        <p className="py-12 text-center text-stone-500">
          {search || activeFilter !== "all"
            ? "No jobs match your filters."
            : "No dismissed or archived jobs yet."}
        </p>
      )}

      {state.status === "loaded" && state.jobs.length > 0 && (
        <>
          <p className="mb-4 text-sm text-stone-500">
            Showing {state.offset + 1}–
            {Math.min(state.offset + state.jobs.length, state.total)} of{" "}
            {state.total} {state.total === 1 ? "job" : "jobs"}
          </p>
          <div className="space-y-5">
            {state.jobs.map((job) => (
              <JobCard key={job.id} job={job} />
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
