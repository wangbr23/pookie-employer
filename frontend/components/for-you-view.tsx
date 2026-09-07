"use client";

import { useEffect, useState } from "react";
import type { JobSummaryResponse, FitBucket } from "@/lib/api-types";
import { listJobs } from "@/lib/api";
import { JobCard } from "./job-card";

const BUCKET_ORDER: FitBucket[] = ["strong", "possible", "stretch", "needs_review"];

const BUCKET_HEADINGS: Record<FitBucket, string> = {
  strong: "Strong Fits",
  possible: "Good Fits",
  stretch: "Stretch Picks",
  needs_review: "Needs Review",
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; groups: { bucket: FitBucket; jobs: JobSummaryResponse[] }[] };

export function ForYouView({ onTotalChange }: { onTotalChange?: (n: number) => void }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await listJobs({
          status: ["new", "seen"],
          limit: 200,
        });
        if (cancelled) return;
        const byBucket = new Map<FitBucket, JobSummaryResponse[]>();
        for (const job of res.items) {
          const b = job.fit_bucket ?? "needs_review";
          const arr = byBucket.get(b);
          if (arr) arr.push(job);
          else byBucket.set(b, [job]);
        }
        const groups = BUCKET_ORDER.filter((b) => byBucket.has(b)).map((b) => ({
          bucket: b,
          jobs: byBucket.get(b)!,
        }));
        setState({ status: "loaded", groups });
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
    return () => { cancelled = true; };
  }, [onTotalChange]);

  return (
    <div className="max-w-6xl">
      <header className="mb-8 flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
          For You
        </p>
        <div>
          <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
            New jobs for you
          </h1>
          {state.status === "loaded" && (
            <p className="mt-3 text-lg text-stone-600">
              {state.groups.reduce((n, g) => n + g.jobs.length, 0)} jobs picked
              for you across {state.groups.length} fit{" "}
              {state.groups.length === 1 ? "category" : "categories"}.
            </p>
          )}
        </div>
      </header>

      {state.status === "loading" && (
        <p className="py-12 text-center text-stone-500">Loading jobs...</p>
      )}

      {state.status === "error" && (
        <p className="py-12 text-center text-red-600">{state.message}</p>
      )}

      {state.status === "loaded" && state.groups.length === 0 && (
        <p className="py-12 text-center text-stone-500">
          No new jobs right now. Try refreshing your sources.
        </p>
      )}

      {state.status === "loaded" &&
        state.groups.map(({ bucket, jobs }) => (
          <section key={bucket} className="mb-10">
            <h2 className="mb-4 text-lg font-bold text-stone-700">
              {BUCKET_HEADINGS[bucket]}{" "}
              <span className="text-sm font-normal text-stone-400">
                ({jobs.length})
              </span>
            </h2>
            <div className="space-y-5">
              {jobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          </section>
        ))}
    </div>
  );
}
