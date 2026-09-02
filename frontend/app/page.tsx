const forYouJobs = [
  {
    company: "Northstar Systems",
    initials: "NS",
    title: "Senior Frontend Engineer",
    location: "Remote",
    type: "Full-time",
    salary: "$165k-$205k",
    fitBucket: "Strong Fit",
    fitTone: "bg-emerald-100 text-emerald-900",
    saved: true,
    summary:
      "Product engineering role focused on Next.js, design systems, and accessible dashboard experiences.",
    concerns: "Light mobile work; some legacy UI migration.",
    source: "Greenhouse",
    posted: "Posted 2 days ago",
  },
  {
    company: "Harbor Labs",
    initials: "HL",
    title: "Full Stack Engineer",
    location: "Boston, MA",
    type: "Hybrid",
    salary: "$150k-$185k",
    fitBucket: "Strong Fit",
    fitTone: "bg-emerald-100 text-emerald-900",
    saved: false,
    summary:
      "Build customer-facing workflows in React and Python for a small team shipping quickly.",
    concerns: "Occasional on-call rotation.",
    source: "Lever",
    posted: "Posted 1 day ago",
  },
  {
    company: "Cinder Health",
    initials: "CH",
    title: "Frontend Engineer",
    location: "Remote",
    type: "Full-time",
    salary: "$145k-$175k",
    fitBucket: "Needs Review",
    fitTone: "bg-amber-100 text-amber-900",
    saved: false,
    summary:
      "A frontend-heavy role with strong product polish and a lot of component work.",
    concerns: "Healthtech domain and some charting depth to learn.",
    source: "Workday",
    posted: "Posted 3 days ago",
  },
  {
    company: "Atlas Commerce",
    initials: "AC",
    title: "Software Engineer, Platform",
    location: "New York, NY",
    type: "Hybrid",
    salary: "$175k-$215k",
    fitBucket: "Good Fit",
    fitTone: "bg-sky-100 text-sky-900",
    saved: true,
    summary:
      "Improve internal tooling, API workflows, and the admin experience for operational teams.",
    concerns: "More backend breadth than frontend.",
    source: "Ashby",
    posted: "Posted 4 days ago",
  },
  {
    company: "Moss Analytics",
    initials: "MA",
    title: "Product Engineer",
    location: "Remote",
    type: "Full-time",
    salary: "Unknown salary",
    fitBucket: "Good Fit",
    fitTone: "bg-sky-100 text-sky-900",
    saved: false,
    summary:
      "Join a data-rich product team building customer-facing workflows and reporting surfaces.",
    concerns: "Compensation not listed yet.",
    source: "Greenhouse",
    posted: "Posted 5 days ago",
  },
  {
    company: "Juniper Social",
    initials: "JS",
    title: "Senior Software Engineer",
    location: "Chicago, IL",
    type: "Hybrid",
    salary: "$160k-$190k",
    fitBucket: "Needs Review",
    fitTone: "bg-amber-100 text-amber-900",
    saved: false,
    summary:
      "Own features across the stack for creator tools with a strong product design component.",
    concerns: "Role mentions ad tech experience as a plus.",
    source: "Lever",
    posted: "Posted 6 days ago",
  },
] as const;

const navItems = [
  { label: "For You", active: true, count: null },
  { label: "Saved", active: false, count: 3 },
  { label: "All Jobs", active: false, count: 42 },
  { label: "Dismissed", active: false, count: 11 },
  { label: "Debug / Coverage", active: false, count: null },
] as const;

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: string;
}) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-3 py-1 text-sm font-medium shadow-sm",
        tone,
      ].join(" ")}
    >
      {children}
    </span>
  );
}

function JobCard({
  job,
}: {
  job: (typeof forYouJobs)[number];
}) {
  return (
    <article className="rounded-[28px] border border-white/80 bg-white/90 p-4 shadow-[0_16px_40px_rgba(186,141,169,0.15)] ring-1 ring-white/70 sm:p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-fuchsia-300 via-pink-300 to-amber-200 text-lg font-bold text-white shadow-sm">
            {job.initials}
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">
              {job.company}
            </p>
            <h3 className="mt-1 text-xl font-semibold text-stone-800 sm:text-[1.35rem]">
              {job.title}
            </h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">
              {job.summary}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <Badge tone="bg-violet-100 text-violet-900">📍 {job.location}</Badge>
          <Badge tone="bg-amber-100 text-amber-900">{job.type}</Badge>
          <Badge tone="bg-rose-100 text-rose-900">{job.salary}</Badge>
          <Badge tone={job.fitTone}>{job.fitBucket}</Badge>
        </div>
      </div>

      <div className="mt-4 flex flex-col gap-4 border-t border-stone-100 pt-4 md:flex-row md:items-end md:justify-between">
        <div className="space-y-2 text-sm text-stone-600">
          <p>
            <span className="font-semibold text-stone-700">Concerns:</span>{" "}
            {job.concerns}
          </p>
          <p className="flex flex-wrap gap-x-3 gap-y-1">
            <span>
              <span className="font-semibold text-stone-700">Source:</span>{" "}
              {job.source}
            </span>
            <span>{job.posted}</span>
            {job.saved ? (
              <span className="inline-flex items-center rounded-full bg-fuchsia-100 px-2.5 py-1 text-xs font-semibold text-fuchsia-900">
                Saved
              </span>
            ) : null}
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
          <a
            href="#"
            className="rounded-full bg-gradient-to-r from-fuchsia-400 to-pink-500 px-5 py-2 text-sm font-semibold text-white shadow-md shadow-pink-200 transition-transform hover:-translate-y-0.5"
          >
            Apply
          </a>
        </div>
      </div>
    </article>
  );
}

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#fff1f6,_transparent_32%),linear-gradient(180deg,_#fdeef4_0%,_#f8edf8_42%,_#f7f2ff_100%)] text-stone-800">
      <div className="mx-auto flex min-h-screen max-w-[1800px]">
        <aside className="hidden w-[340px] flex-col border-r border-white/70 bg-gradient-to-b from-[#f7d2e5] via-[#f3dff0] to-[#e9e1fb] px-7 py-8 shadow-[inset_-1px_0_0_rgba(255,255,255,0.75)] lg:flex">
          <div className="flex items-center gap-3 text-2xl font-bold tracking-tight text-stone-700">
            <span className="text-fuchsia-400">✦</span>
            Pookie Employer
          </div>

          <nav className="mt-10 space-y-4">
            {navItems.map((item) => (
              <div
                key={item.label}
                className={[
                  "flex items-center justify-between rounded-[22px] px-5 py-4 text-lg font-semibold transition-colors",
                  item.active
                    ? "bg-gradient-to-r from-fuchsia-400 to-pink-500 text-white shadow-lg shadow-pink-200"
                    : "text-stone-600 hover:bg-white/35",
                ].join(" ")}
              >
                <span className="flex items-center gap-3">
                  <span className={item.active ? "text-white" : "text-fuchsia-400"}>
                    ✦
                  </span>
                  {item.label}
                </span>
                {item.count ? (
                  <span className="rounded-full bg-white/60 px-2.5 py-1 text-sm font-bold text-stone-600">
                    {item.count}
                  </span>
                ) : null}
              </div>
            ))}
          </nav>

          <div className="mt-auto rounded-[24px] bg-white/60 p-5 shadow-sm backdrop-blur">
            <p className="text-sm font-medium text-stone-600">made just for you 💕</p>
          </div>
        </aside>

        <section className="flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-10">
          <div className="max-w-6xl">
            <header className="mb-8 flex flex-col gap-3">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-500">
                For You
              </p>
              <div>
                <h1 className="text-4xl font-black tracking-tight text-stone-700 sm:text-5xl">
                  Good morning! ✨
                </h1>
                <p className="mt-3 text-lg text-stone-600">
                  6 sweet software engineering jobs picked for you today.
                </p>
              </div>
            </header>

            <div className="space-y-5">
              {forYouJobs.map((job) => (
                <JobCard key={`${job.company}-${job.title}`} job={job} />
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
