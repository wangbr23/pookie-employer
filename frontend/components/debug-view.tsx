"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  CoverageResponse,
  CrawlRunResponse,
  CrawlStatus,
  JobSourceStatusResponse,
  SourceRunResponse,
  SourceRunStatus,
} from "@/lib/api-types";
import {
  getCoverage,
  triggerRefresh,
  getCrawlRun,
  deleteProfileData,
  deleteJobHistory,
} from "@/lib/api";
import { ApiError } from "@/lib/api";

type CoverageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "loaded"; data: CoverageResponse };

type RefreshState =
  | { status: "idle" }
  | { status: "running"; runId: string }
  | { status: "done"; run: CrawlRunResponse }
  | { status: "error"; message: string };

const POLL_INTERVAL = 2000;

export function DebugView() {
  const [coverage, setCoverage] = useState<CoverageState>({ status: "loading" });
  const [refresh, setRefresh] = useState<RefreshState>({ status: "idle" });
  const [reloadKey, setReloadKey] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const data = await getCoverage();
        if (!cancelled) setCoverage({ status: "loaded", data });
      } catch (err) {
        if (!cancelled)
          setCoverage({
            status: "error",
            message:
              err instanceof Error ? err.message : "Failed to load coverage",
          });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const handleRefresh = useCallback(async () => {
    setRefresh({ status: "running", runId: "" });
    try {
      const run = await triggerRefresh();
      if (run.status === "running") {
        setRefresh({ status: "running", runId: run.id });
        pollRef.current = setInterval(async () => {
          try {
            const updated = await getCrawlRun(run.id);
            if (updated.status !== "running") {
              if (pollRef.current) clearInterval(pollRef.current);
              pollRef.current = null;
              setRefresh({ status: "done", run: updated });
              setReloadKey((k) => k + 1);
            }
          } catch {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
          }
        }, POLL_INTERVAL);
      } else {
        setRefresh({ status: "done", run });
        setReloadKey((k) => k + 1);
      }
    } catch (err) {
      if (err instanceof ApiError && err.detail.code === "refresh_already_running") {
        setRefresh({ status: "error", message: "A refresh is already running." });
      } else {
        setRefresh({
          status: "error",
          message: err instanceof Error ? err.message : "Failed to trigger refresh",
        });
      }
    }
  }, []);

  const isRefreshing = refresh.status === "running";

  return (
    <div className="max-w-6xl">
      <header className="mb-8 flex flex-col gap-3">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
          Debug
        </p>
        <div className="flex items-center gap-4">
          <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
            Coverage
          </h1>
          <button
            type="button"
            disabled={isRefreshing}
            onClick={handleRefresh}
            className="rounded-full bg-gradient-to-r from-fuchsia-400 to-pink-500 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {isRefreshing ? "Refreshing…" : "Refresh Jobs"}
          </button>
        </div>
      </header>

      {refresh.status === "error" && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50/80 px-5 py-3 text-sm text-red-700">
          {refresh.message}
        </div>
      )}

      {refresh.status === "done" && (
        <RefreshResult run={refresh.run} onDismiss={() => setRefresh({ status: "idle" })} />
      )}

      {coverage.status === "loading" && (
        <p className="py-12 text-center text-stone-500">Loading coverage data…</p>
      )}

      {coverage.status === "error" && (
        <p className="py-12 text-center text-red-600">{coverage.message}</p>
      )}

      {coverage.status === "loaded" && (
        <>
          <LastCrawlRun run={coverage.data.last_crawl_run} />
          <SourceTable sources={coverage.data.sources} />
        </>
      )}

      <DataManagement />
    </div>
  );
}

type DeletionState =
  | { status: "idle" }
  | { status: "confirming" }
  | { status: "deleting" }
  | { status: "done"; message: string }
  | { status: "error"; message: string };

function DeletionAction({
  title,
  description,
  confirmWord,
  onDelete,
}: {
  title: string;
  description: string;
  confirmWord: string;
  onDelete: () => Promise<string>;
}) {
  const [state, setState] = useState<DeletionState>({ status: "idle" });
  const [input, setInput] = useState("");

  const handleConfirm = useCallback(async () => {
    setState({ status: "deleting" });
    try {
      const message = await onDelete();
      setState({ status: "done", message });
      setInput("");
    } catch (err) {
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "Deletion failed",
      });
    }
  }, [onDelete]);

  if (state.status === "done") {
    return (
      <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-5">
        <p className="text-sm font-semibold text-emerald-800">{title}</p>
        <p className="mt-1 text-sm text-emerald-700">{state.message}</p>
        <button
          type="button"
          onClick={() => setState({ status: "idle" })}
          className="mt-3 text-sm font-medium text-emerald-600 hover:text-emerald-800"
        >
          Dismiss
        </button>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50/80 p-5">
        <p className="text-sm font-semibold text-red-800">{title}</p>
        <p className="mt-1 text-sm text-red-700">{state.message}</p>
        <button
          type="button"
          onClick={() => setState({ status: "idle" })}
          className="mt-3 text-sm font-medium text-red-600 hover:text-red-800"
        >
          Dismiss
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-stone-200 bg-white/70 p-5">
      <p className="text-sm font-semibold text-stone-700">{title}</p>
      <p className="mt-1 text-sm text-stone-500">{description}</p>
      {state.status === "idle" && (
        <button
          type="button"
          onClick={() => setState({ status: "confirming" })}
          className="mt-3 rounded-full border border-red-300 px-4 py-1.5 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50"
        >
          Delete…
        </button>
      )}
      {(state.status === "confirming" || state.status === "deleting") && (
        <div className="mt-3">
          <label className="block text-sm text-stone-600">
            Type <span className="font-mono font-bold text-red-600">{confirmWord}</span> to confirm:
          </label>
          <div className="mt-1.5 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={state.status === "deleting"}
              className="rounded-lg border border-stone-300 px-3 py-1.5 text-sm text-stone-800 outline-none focus:border-red-400 focus:ring-1 focus:ring-red-200 disabled:opacity-50"
              autoFocus
            />
            <button
              type="button"
              disabled={input !== confirmWord || state.status === "deleting"}
              onClick={handleConfirm}
              className="rounded-full bg-red-500 px-4 py-1.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              {state.status === "deleting" ? "Deleting…" : "Confirm"}
            </button>
            <button
              type="button"
              disabled={state.status === "deleting"}
              onClick={() => {
                setState({ status: "idle" });
                setInput("");
              }}
              className="text-sm text-stone-500 hover:text-stone-700 disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DataManagement() {
  const handleDeleteProfile = useCallback(async () => {
    const result = await deleteProfileData();
    return `Deleted ${result.deleted.evaluations} evaluations and ${result.deleted.ai_call_logs} AI call logs.`;
  }, []);

  const handleDeleteHistory = useCallback(async () => {
    const result = await deleteJobHistory();
    return `Deleted ${result.deleted.feedback_records} feedback records. Reset ${result.reset.jobs_to_seen} jobs to seen.`;
  }, []);

  return (
    <div className="mt-8 rounded-2xl border border-red-100 bg-red-50/30 p-6">
      <h2 className="mb-1 text-lg font-bold text-stone-700">Data Management</h2>
      <p className="mb-5 text-sm text-stone-500">
        These actions permanently delete data and cannot be undone.
      </p>
      <div className="space-y-4">
        <DeletionAction
          title="Delete Profile Data"
          description="Removes all AI evaluations and call logs. Jobs and raw postings are preserved so you can re-evaluate."
          confirmWord="delete-profile"
          onDelete={handleDeleteProfile}
        />
        <DeletionAction
          title="Delete Job History"
          description="Removes all saved/dismissed feedback. Affected jobs revert to seen status."
          confirmWord="delete-history"
          onDelete={handleDeleteHistory}
        />
      </div>
    </div>
  );
}

function RefreshResult({
  run,
  onDismiss,
}: {
  run: CrawlRunResponse;
  onDismiss: () => void;
}) {
  return (
    <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50/80 px-5 py-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-emerald-800">
            Refresh complete — <StatusBadge status={run.status} />
          </p>
          <p className="mt-1 text-sm text-emerald-700">
            {run.jobs_new} new, {run.jobs_updated} updated, {run.jobs_skipped} skipped
            {" · "}
            {run.sources_succeeded}/{run.sources_attempted} sources succeeded
            {run.sources_failed > 0 && (
              <span className="text-red-600"> · {run.sources_failed} failed</span>
            )}
            {" · "}
            {formatElapsed(run.elapsed_milliseconds)}
          </p>
        </div>
        <button
          type="button"
          onClick={onDismiss}
          className="text-emerald-500 hover:text-emerald-700"
          aria-label="Dismiss"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function LastCrawlRun({ run }: { run: CrawlRunResponse | null }) {
  if (!run) {
    return (
      <div className="mb-8 rounded-2xl border border-stone-200 bg-white/70 p-6">
        <p className="text-sm text-stone-500">
          No refresh has been run yet. Click &ldquo;Refresh Jobs&rdquo; to start.
        </p>
      </div>
    );
  }

  return (
    <div className="mb-8 rounded-2xl border border-stone-200 bg-white/70 p-6">
      <h2 className="mb-4 text-lg font-bold text-stone-700">Last Refresh</h2>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <Stat label="Status" value={<StatusBadge status={run.status} />} />
        <Stat label="Started" value={formatTime(run.started_at)} />
        <Stat label="Elapsed" value={formatElapsed(run.elapsed_milliseconds)} />
        <Stat label="Trigger" value={run.trigger.replace(/_/g, " ")} />
        <Stat label="Jobs discovered" value={String(run.jobs_discovered)} />
        <Stat label="New jobs" value={String(run.jobs_new)} />
        <Stat label="Updated" value={String(run.jobs_updated)} />
        <Stat label="Skipped" value={String(run.jobs_skipped)} />
        <Stat
          label="Sources"
          value={`${run.sources_succeeded}/${run.sources_attempted} ok`}
        />
        {run.sources_failed > 0 && (
          <Stat
            label="Failed sources"
            value={String(run.sources_failed)}
            warn
          />
        )}
        <Stat label="Evaluations done" value={String(run.evaluations_completed)} />
        {run.evaluations_pending > 0 && (
          <Stat
            label="Evaluations pending"
            value={String(run.evaluations_pending)}
            warn
          />
        )}
        <Stat label="AI calls" value={String(run.ai_call_count)} />
        {run.estimated_ai_cost != null && (
          <Stat label="Est. AI cost" value={`$${run.estimated_ai_cost}`} />
        )}
      </div>

      {run.sources.length > 0 && (
        <>
          <h3 className="mb-3 mt-6 text-sm font-semibold text-stone-600">
            Source runs
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-stone-200 text-stone-500">
                  <th className="pb-2 pr-4 font-medium">Source</th>
                  <th className="pb-2 pr-4 font-medium">Company</th>
                  <th className="pb-2 pr-4 font-medium">Status</th>
                  <th className="pb-2 pr-4 font-medium text-right">Discovered</th>
                  <th className="pb-2 pr-4 font-medium text-right">Inserted</th>
                  <th className="pb-2 pr-4 font-medium text-right">Updated</th>
                  <th className="pb-2 font-medium">Error</th>
                </tr>
              </thead>
              <tbody>
                {run.sources.map((sr) => (
                  <SourceRunRow key={sr.job_source_id} run={sr} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function SourceRunRow({ run }: { run: SourceRunResponse }) {
  return (
    <tr className="border-b border-stone-100 last:border-b-0">
      <td className="py-2 pr-4 font-medium text-stone-700">{run.source_name}</td>
      <td className="py-2 pr-4 text-stone-600">{run.company_name}</td>
      <td className="py-2 pr-4">
        <SourceRunStatusBadge status={run.status} />
      </td>
      <td className="py-2 pr-4 text-right tabular-nums">{run.jobs_discovered}</td>
      <td className="py-2 pr-4 text-right tabular-nums">{run.jobs_inserted}</td>
      <td className="py-2 pr-4 text-right tabular-nums">{run.jobs_updated}</td>
      <td className="py-2 text-stone-500">
        {run.error_summary && (
          <span className="text-red-600">{run.error_summary}</span>
        )}
      </td>
    </tr>
  );
}

function SourceTable({ sources }: { sources: JobSourceStatusResponse[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="rounded-2xl border border-stone-200 bg-white/70 p-6">
      <h2 className="mb-4 text-lg font-bold text-stone-700">Source Health</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-stone-200 text-stone-500">
              <th className="pb-2 pr-4 font-medium">Source</th>
              <th className="pb-2 pr-4 font-medium">Company</th>
              <th className="pb-2 pr-4 font-medium">Kind</th>
              <th className="pb-2 pr-4 font-medium">Status</th>
              <th className="pb-2 pr-4 font-medium">Approval</th>
              <th className="pb-2 pr-4 font-medium">Last success</th>
              <th className="pb-2 font-medium">Last error</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((s) => (
              <tr key={s.id} className="border-b border-stone-100 last:border-b-0">
                <td className="py-2 pr-4 font-medium text-stone-700">{s.name}</td>
                <td className="py-2 pr-4 text-stone-600">{s.company_name}</td>
                <td className="py-2 pr-4 text-stone-500">{s.kind}</td>
                <td className="py-2 pr-4">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
                      s.status === "active"
                        ? "bg-emerald-100 text-emerald-700"
                        : s.status === "paused"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-stone-100 text-stone-600"
                    }`}
                  >
                    {s.status}
                  </span>
                </td>
                <td className="py-2 pr-4">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${
                      s.approval_status === "approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : s.approval_status === "rejected"
                          ? "bg-red-100 text-red-700"
                          : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {s.approval_status}
                  </span>
                </td>
                <td className="py-2 pr-4 text-stone-500">
                  {s.last_successful_crawl_at
                    ? formatTime(s.last_successful_crawl_at)
                    : "—"}
                </td>
                <td className="py-2 text-stone-500">
                  {s.last_error_at ? (
                    <span className="text-red-600" title={s.last_error_summary ?? undefined}>
                      {formatTime(s.last_error_at)}
                      {s.last_error_summary && ` — ${s.last_error_summary}`}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  warn,
}: {
  label: string;
  value: React.ReactNode;
  warn?: boolean;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-stone-500">{label}</p>
      <p
        className={`mt-0.5 text-lg font-bold tabular-nums ${warn ? "text-amber-600" : "text-stone-700"}`}
      >
        {value}
      </p>
    </div>
  );
}

function StatusBadge({ status }: { status: CrawlStatus }) {
  const cls: Record<CrawlStatus, string> = {
    running: "bg-blue-100 text-blue-700",
    success: "bg-emerald-100 text-emerald-700",
    partial_success: "bg-amber-100 text-amber-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${cls[status]}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

function SourceRunStatusBadge({ status }: { status: SourceRunStatus }) {
  const cls: Record<SourceRunStatus, string> = {
    running: "bg-blue-100 text-blue-700",
    success: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-700",
    skipped: "bg-stone-100 text-stone-600",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${cls[status]}`}
    >
      {status}
    </span>
  );
}

function formatElapsed(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
