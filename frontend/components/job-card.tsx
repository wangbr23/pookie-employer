"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { JobSummaryResponse, FitBucket } from "@/lib/api-types";
import { markJobSeen } from "@/lib/api";

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

const DISMISS_REASONS = [
  "Not interested in this role",
  "Wrong location",
  "Compensation too low",
  "Wrong seniority level",
  "Already applied",
  "Company not a fit",
];

const INACTIVE_STATUSES: string[] = ["dismissed", "possibly_closed", "closed_archived"];

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

export interface JobCardProps {
  job: JobSummaryResponse;
  onSave?: (jobId: string) => Promise<void>;
  onDismiss?: (jobId: string, reasons: string[], freeText?: string) => Promise<void>;
}

export function JobCard({ job, onSave, onDismiss }: JobCardProps) {
  const [saving, setSaving] = useState(false);
  const [showDismissForm, setShowDismissForm] = useState(false);
  const [dismissing, setDismissing] = useState(false);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const seenRef = useRef(false);

  useEffect(() => {
    if (job.status === "new" && !seenRef.current) {
      seenRef.current = true;
      markJobSeen(job.id).catch(() => {});
    }
  }, [job.id, job.status]);

  const handleSave = useCallback(async () => {
    if (!onSave || saving) return;
    setSaving(true);
    try {
      await onSave(job.id);
    } finally {
      setSaving(false);
    }
  }, [job.id, onSave, saving]);

  const handleDismissConfirm = useCallback(async () => {
    if (!onDismiss || dismissing || selectedReasons.length === 0) return;
    setDismissing(true);
    try {
      await onDismiss(job.id, selectedReasons, freeText || undefined);
    } finally {
      setDismissing(false);
    }
  }, [job.id, onDismiss, dismissing, selectedReasons, freeText]);

  const toggleReason = useCallback((reason: string) => {
    setSelectedReasons((prev) =>
      prev.includes(reason)
        ? prev.filter((r) => r !== reason)
        : [...prev, reason],
    );
  }, []);

  const showSave = job.status !== "saved" && !!onSave;
  const showDismiss = !INACTIVE_STATUSES.includes(job.status) && !!onDismiss;

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
            {job.status === "dismissed" && (
              <span className="inline-flex items-center rounded-full bg-stone-100 px-2.5 py-1 text-xs font-semibold text-stone-600">
                Dismissed
              </span>
            )}
            {job.status === "possibly_closed" && (
              <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">
                Possibly Closed
              </span>
            )}
            {job.status === "closed_archived" && (
              <span className="inline-flex items-center rounded-full bg-stone-200 px-2.5 py-1 text-xs font-semibold text-stone-500">
                Archived
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {showSave && (
            <button
              type="button"
              disabled={saving}
              onClick={handleSave}
              className="rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-900 transition-colors hover:bg-rose-100 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save"}
            </button>
          )}
          {showDismiss && (
            <button
              type="button"
              onClick={() => setShowDismissForm((v) => !v)}
              className={`rounded-full border px-4 py-2 text-sm font-semibold transition-colors ${
                showDismissForm
                  ? "border-stone-400 bg-stone-200 text-stone-800"
                  : "border-stone-200 bg-stone-50 text-stone-700 hover:bg-stone-100"
              }`}
            >
              Dismiss
            </button>
          )}
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

      {showDismissForm && (
        <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50/80 p-4">
          <p className="mb-3 text-sm font-semibold text-stone-700">
            Why are you dismissing this?
          </p>
          <div className="space-y-2">
            {DISMISS_REASONS.map((reason) => (
              <label
                key={reason}
                className="flex cursor-pointer items-center gap-2.5 text-sm text-stone-600"
              >
                <input
                  type="checkbox"
                  checked={selectedReasons.includes(reason)}
                  onChange={() => toggleReason(reason)}
                  className="rounded border-stone-300 text-fuchsia-500 focus:ring-fuchsia-300"
                />
                {reason}
              </label>
            ))}
          </div>
          <textarea
            placeholder="Anything else? (optional)"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            className="mt-3 w-full rounded-xl border border-stone-200 bg-white/80 px-3 py-2 text-sm text-stone-700 placeholder:text-stone-400 focus:border-fuchsia-300 focus:outline-none focus:ring-2 focus:ring-fuchsia-200"
            rows={2}
          />
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              disabled={selectedReasons.length === 0 || dismissing}
              onClick={handleDismissConfirm}
              className="rounded-full bg-stone-700 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-stone-800 disabled:opacity-40"
            >
              {dismissing ? "Dismissing..." : "Confirm"}
            </button>
            <button
              type="button"
              onClick={() => {
                setShowDismissForm(false);
                setSelectedReasons([]);
                setFreeText("");
              }}
              className="rounded-full border border-stone-200 px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-100"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
