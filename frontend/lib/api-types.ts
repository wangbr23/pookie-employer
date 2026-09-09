export type JobStatus =
  | "new"
  | "seen"
  | "saved"
  | "dismissed"
  | "possibly_closed"
  | "closed_archived";

export type FitBucket = "strong" | "possible" | "stretch" | "needs_review";

export type JobLinkStatus = "active" | "broken" | "possibly_closed" | "closed";

export type SalaryUncertainty =
  | "known"
  | "unknown"
  | "estimated"
  | "conflicting";

export type RemoteUncertainty = "clear" | "unclear" | "conflicting";

export type WorkAuthUncertainty = "clear" | "unclear" | "conflicting";

export type CrawlTrigger = "on_demand" | "manual_script" | "scheduled";

export type CrawlStatus =
  | "running"
  | "partial_success"
  | "success"
  | "failed";

export type SourceRunStatus = "running" | "success" | "failed" | "skipped";

export type SourceKind =
  | "greenhouse"
  | "lever"
  | "ashby"
  | "workday"
  | "netflix"
  | "phenom"
  | "company_page";

export type SourceStatus = "active" | "paused" | "needs_review";

export type ApprovalStatus = "approved" | "suggested" | "rejected";

// ---------------------------------------------------------------------------
// Response shapes — mirror backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface JobLinkResponse {
  id: string;
  source_url: string;
  apply_url: string | null;
  is_primary: boolean;
  status: JobLinkStatus;
  last_checked_at: string | null;
}

export interface JobEvaluationResponse {
  fit_bucket: FitBucket;
  internal_score: string | null;
  matched_skills: string[];
  matched_preferences: string[];
  concerns: string[];
  uncertainties: string[];
  summary: string | null;
  verify_before_applying: string[];
  salary_uncertainty: SalaryUncertainty;
  remote_uncertainty: RemoteUncertainty;
  work_auth_uncertainty: WorkAuthUncertainty;
  model_provider: string;
  model_name: string;
  evaluated_at: string;
}

export interface JobSummaryResponse {
  id: string;
  canonical_title: string;
  canonical_company: string;
  canonical_location: string | null;
  remote_policy: string | null;
  employment_type: string | null;
  salary_min: string | null;
  salary_max: string | null;
  salary_currency: string | null;
  salary_unknown: boolean;
  seniority: string | null;
  status: JobStatus;
  fit_bucket: FitBucket | null;
  first_seen_at: string;
  last_seen_at: string;
  apply_url: string | null;
}

export interface JobDetailResponse extends JobSummaryResponse {
  evaluation: JobEvaluationResponse | null;
  links: JobLinkResponse[];
}

export interface JobListResponse {
  items: JobSummaryResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceRunResponse {
  job_source_id: string;
  source_name: string;
  company_name: string;
  kind: SourceKind;
  status: SourceRunStatus;
  started_at: string;
  finished_at: string | null;
  jobs_discovered: number;
  jobs_inserted: number;
  jobs_updated: number;
  jobs_skipped: number;
  error_summary: string | null;
}

export interface CrawlRunResponse {
  id: string;
  trigger: CrawlTrigger;
  status: CrawlStatus;
  started_at: string;
  finished_at: string | null;
  elapsed_milliseconds: number | null;
  sources_attempted: number;
  sources_succeeded: number;
  sources_failed: number;
  jobs_discovered: number;
  jobs_new: number;
  jobs_updated: number;
  jobs_skipped: number;
  evaluations_completed: number;
  evaluations_pending: number;
  ai_call_count: number;
  estimated_ai_cost: string | null;
  sources: SourceRunResponse[];
}

export interface JobSourceStatusResponse {
  id: string;
  kind: SourceKind;
  name: string;
  company_name: string;
  status: SourceStatus;
  approval_status: ApprovalStatus;
  last_successful_crawl_at: string | null;
  last_error_at: string | null;
  last_error_summary: string | null;
}

export interface CoverageResponse {
  last_crawl_run: CrawlRunResponse | null;
  sources: JobSourceStatusResponse[];
}

export interface RankRunResponse {
  jobs_considered: number;
  jobs_awaiting_evaluation: number;
  evaluations_run: number;
}

// ---------------------------------------------------------------------------
// Deletion responses
// ---------------------------------------------------------------------------

export interface DeleteProfileDataResponse {
  deleted: {
    evaluations: number;
    ai_call_logs: number;
  };
}

export interface DeleteJobHistoryResponse {
  deleted: { feedback_records: number };
  reset: { jobs_to_seen: number };
}

// ---------------------------------------------------------------------------
// Request bodies
// ---------------------------------------------------------------------------

export interface SaveJobRequest {
  reasons?: string[];
  free_text?: string | null;
}

export interface DismissJobRequest {
  reasons: string[];
  free_text?: string | null;
}

// ---------------------------------------------------------------------------
// Error shape returned by the backend
// ---------------------------------------------------------------------------

export interface ApiErrorDetail {
  code: string;
  message: string;
}
