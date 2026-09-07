"use client";

import type { JobSummaryResponse, FitBucket } from "@/lib/api-types";

const FIT_LABELS: Record<FitBucket, string> = {
  strong: "Strong Fit",
  possible: "Good Fit",
  stretch: "Stretch",
  needs_review: "Needs Review",
};

const FIT_TONES: Record<FitBucket, string> = {
  strong: "bg-emerald-100 text-emerald-900",
  possible: "bg-sky-100 text-sky-900",
  stretch: "bg-orange-100 text-orange-900",
  needs_review: "bg-amber-100 text-amber-900",
};

const REMOTE_LABELS: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unclear: "Location TBD",
};

function formatSalary(job: JobSummaryResponse): string {
  if (job.salary_unknown || (!job.salary_min && !job.salary_max))
    return "Unknown salary";
  const cur = job.salary_currency ?? "$";
  if (job.salary_min && job.salary_max)
    return `${cur}${Number(job.salary_min).toLocaleString()}–${cur}${Number(job.salary_max).toLocaleString()}`;
  if (job.salary_min) return `From ${cur}${Number(job.salary_min).toLocaleString()}`;
  return `Up to ${cur}${Number(job.salary_max).toLocaleString()}`;
}

function relativeTime(iso: string): string {
  const days = Math.floor(
    (Date.now() - new Date(iso).getTime()) / 86_400_000,
  );
  if (days <= 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 7) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  if (weeks === 1) return "1 week ago";
  if (weeks < 5) return `${weeks} weeks ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return "1 month ago";
  return `${months} months ago`;
}

function initials(company: string): string {
  return company
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

function Badge({ children, tone }: { children: React.ReactNode; tone: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium shadow-sm ${tone}`}
    >
      {children}
    </span>
  );
}

export function JobCard({ job }: { job: JobSummaryResponse }) {
  const bucket = job.fit_bucket;
  const bucketLabel = bucket ? FIT_LABELS[bucket] : null;
  const bucketTone = bucket ? FIT_TONES[bucket] : "";
  const location =
    job.canonical_location ??
    (job.remote_policy ? REMOTE_LABELS[job.remote_policy] : null);
  const remoteLabel = job.remote_policy ? REMOTE_LABELS[job.remote_policy] : null;
  const displayLocation =
    remoteLabel && location && !location.toLowerCase().includes("remote")
      ? `${location} (${remoteLabel})`
      : location ?? "Location unknown";

  return (
    <article className="rounded-[28px] border border-white/80 bg-white/90 p-4 shadow-[0_16px_40px_rgba(186,141,169,0.15)] ring-1 ring-white/70 sm:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-300 via-pink-300 to-amber-200 text-lg font-bold text-white shadow-sm">
            {initials(job.canonical_company)}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
              {job.canonical_company}
            </p>
            <h3 className="mt-1 text-xl font-semibold text-stone-800 sm:text-[1.35rem]">
              {job.canonical_title}
            </h3>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <Badge tone="bg-violet-100 text-violet-900">
            {displayLocation}
          </Badge>
          {job.employment_type && (
            <Badge tone="bg-amber-100 text-amber-900">{job.employment_type}</Badge>
          )}
          <Badge tone="bg-rose-100 text-rose-900">{formatSalary(job)}</Badge>
          {bucketLabel && <Badge tone={bucketTone}>{bucketLabel}</Badge>}
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-4 border-t border-stone-100 pt-4 md:flex-row md:items-end md:justify-between">
        <div className="text-sm text-stone-600">
          <p className="flex flex-wrap gap-x-3 gap-y-1">
            <span>First seen {relativeTime(job.first_seen_at)}</span>
            {job.status === "saved" && (
              <span className="inline-flex items-center rounded-full bg-fuchsia-100 px-2.5 py-1 text-xs font-semibold text-fuchsia-900">
                Saved
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-900 transition-colors hover:bg-rose-100"
          >
            Save
          </button>
          <button
            type="button"
            className="rounded-full border border-stone-200 bg-stone-50 px-4 py-2 text-sm font-semibold text-stone-700 transition-colors hover:bg-stone-100"
          >
            Dismiss
          </button>
          {job.apply_url && (
            <a
              href={job.apply_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-gradient-to-r from-fuchsia-400 to-pink-500 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-pink-200 transition-transform hover:-translate-y-0.5"
            >
              Apply
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
