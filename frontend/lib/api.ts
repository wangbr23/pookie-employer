import type {
  ApiErrorDetail,
  CoverageResponse,
  CrawlRunResponse,
  DismissJobRequest,
  JobDetailResponse,
  JobListResponse,
  JobSummaryResponse,
  FitBucket,
  JobStatus,
  RankRunResponse,
  SaveJobRequest,
} from "./api-types";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: ApiErrorDetail,
  ) {
    super(detail.message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    let detail: ApiErrorDetail;
    try {
      const body = await res.json();
      detail = body.detail ?? { code: "unknown", message: res.statusText };
    } catch {
      detail = { code: "unknown", message: res.statusText };
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | string[] | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val === undefined) continue;
    if (Array.isArray(val)) {
      for (const v of val) sp.append(key, v);
    } else {
      sp.set(key, String(val));
    }
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export interface ListJobsParams {
  status?: JobStatus[];
  fit_bucket?: FitBucket[];
  search?: string;
  limit?: number;
  offset?: number;
}

export function listJobs(params: ListJobsParams = {}): Promise<JobListResponse> {
  return request<JobListResponse>(
    `/api/jobs${qs({
      status: params.status,
      fit_bucket: params.fit_bucket,
      search: params.search,
      limit: params.limit,
      offset: params.offset,
    })}`,
  );
}

export function getJob(jobId: string): Promise<JobDetailResponse> {
  return request<JobDetailResponse>(`/api/jobs/${jobId}`);
}

// ---------------------------------------------------------------------------
// Feedback
// ---------------------------------------------------------------------------

export function saveJob(
  jobId: string,
  body?: SaveJobRequest,
): Promise<JobSummaryResponse> {
  return request<JobSummaryResponse>(`/api/jobs/${jobId}/save`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
}

export function dismissJob(
  jobId: string,
  body: DismissJobRequest,
): Promise<JobSummaryResponse> {
  return request<JobSummaryResponse>(`/api/jobs/${jobId}/dismiss`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function markJobSeen(jobId: string): Promise<JobSummaryResponse> {
  return request<JobSummaryResponse>(`/api/jobs/${jobId}/seen`, {
    method: "POST",
  });
}

// ---------------------------------------------------------------------------
// Refresh / crawl
// ---------------------------------------------------------------------------

export function triggerRefresh(): Promise<CrawlRunResponse> {
  return request<CrawlRunResponse>("/api/crawl/run", { method: "POST" });
}

export function getCrawlRun(runId: string): Promise<CrawlRunResponse> {
  return request<CrawlRunResponse>(`/api/crawl/runs/${runId}`);
}

// ---------------------------------------------------------------------------
// Rank
// ---------------------------------------------------------------------------

export function triggerRank(): Promise<RankRunResponse> {
  return request<RankRunResponse>("/api/rank/run", { method: "POST" });
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------

export async function exportSavedJobs(format: "csv" | "json" = "csv"): Promise<void> {
  const res = await fetch(`/api/export/saved?format=${format}`);
  if (!res.ok) {
    let detail: ApiErrorDetail;
    try {
      const body = await res.json();
      detail = body.detail ?? { code: "unknown", message: res.statusText };
    } catch {
      detail = { code: "unknown", message: res.statusText };
    }
    throw new ApiError(res.status, detail);
  }
  const blob = await res.blob();
  const ext = format === "json" ? "json" : "csv";
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `saved_jobs.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Coverage / debug
// ---------------------------------------------------------------------------

export function getCoverage(): Promise<CoverageResponse> {
  return request<CoverageResponse>("/api/debug/coverage");
}
