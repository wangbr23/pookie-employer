"use client";

import { useCallback, useState } from "react";
import { ForYouView } from "@/components/for-you-view";
import { AllJobsView } from "@/components/all-jobs-view";
import { SavedView } from "@/components/saved-view";
import { DismissedView } from "@/components/dismissed-view";

type View = "for-you" | "all-jobs" | "saved" | "dismissed" | "debug";

const NAV_ITEMS: { view: View; label: string }[] = [
  { view: "for-you", label: "For You" },
  { view: "saved", label: "Saved" },
  { view: "all-jobs", label: "All Jobs" },
  { view: "dismissed", label: "Dismissed" },
  { view: "debug", label: "Debug / Coverage" },
];

export default function Home() {
  const [active, setActive] = useState<View>("for-you");
  const [counts, setCounts] = useState<Partial<Record<View, number>>>({});

  const setForYouCount = useCallback(
    (n: number) => setCounts((prev) => ({ ...prev, "for-you": n })),
    [],
  );
  const setAllJobsCount = useCallback(
    (n: number) => setCounts((prev) => ({ ...prev, "all-jobs": n })),
    [],
  );
  const setSavedCount = useCallback(
    (n: number) => setCounts((prev) => ({ ...prev, saved: n })),
    [],
  );
  const setDismissedCount = useCallback(
    (n: number) => setCounts((prev) => ({ ...prev, dismissed: n })),
    [],
  );

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#fff1f6,_transparent_32%),linear-gradient(180deg,_#fdeef4_0%,_#f8edf8_42%,_#f7f2ff_100%)] text-stone-800">
      <div className="mx-auto flex min-h-screen max-w-[1800px]">
        {/* Sidebar */}
        <aside className="hidden w-[340px] flex-col border-r border-white/70 bg-gradient-to-b from-[#f7d2e5] via-[#f3dff0] to-[#e9e1fb] px-7 py-8 shadow-[inset_-1px_0_0_rgba(255,255,255,0.75)] lg:flex">
          <div className="flex items-center gap-3 text-2xl font-bold tracking-tight text-stone-700">
            <span className="text-fuchsia-400">✦</span>
            Pookie Employer
          </div>

          <nav className="mt-10 space-y-4">
            {NAV_ITEMS.map((item) => {
              const isActive = active === item.view;
              const count = counts[item.view];
              const disabled = item.view === "debug";
              return (
                <button
                  key={item.view}
                  type="button"
                  onClick={() => !disabled && setActive(item.view)}
                  className={[
                    "flex w-full items-center justify-between rounded-[22px] px-5 py-4 text-left text-lg font-semibold transition-colors",
                    isActive
                      ? "bg-gradient-to-r from-fuchsia-400 to-pink-500 text-white shadow-lg shadow-pink-200"
                      : disabled
                        ? "cursor-default text-stone-400"
                        : "text-stone-600 hover:bg-white/35",
                  ].join(" ")}
                >
                  <span className="flex items-center gap-3">
                    <span
                      className={
                        isActive ? "text-white" : "text-fuchsia-400"
                      }
                    >
                      ✦
                    </span>
                    {item.label}
                  </span>
                  {count != null && count > 0 && (
                    <span className="rounded-full bg-white/60 px-2.5 py-1 text-sm font-bold text-stone-600">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          <div className="mt-auto rounded-[24px] bg-white/60 p-5 shadow-sm backdrop-blur">
            <p className="text-sm font-medium text-stone-600">
              made just for you
            </p>
          </div>
        </aside>

        {/* Mobile header */}
        <div className="flex flex-1 flex-col">
          <div className="flex items-center gap-4 overflow-x-auto border-b border-white/60 px-4 py-3 lg:hidden">
            <span className="shrink-0 text-lg font-bold text-stone-700">
              <span className="text-fuchsia-400">✦</span> Pookie
            </span>
            {NAV_ITEMS.filter(
              (i) => i.view !== "debug",
            ).map((item) => (
              <button
                key={item.view}
                type="button"
                onClick={() => setActive(item.view)}
                className={`shrink-0 rounded-full px-4 py-1.5 text-sm font-semibold transition-colors ${
                  active === item.view
                    ? "bg-gradient-to-r from-fuchsia-400 to-pink-500 text-white shadow-sm"
                    : "text-stone-600"
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <section className="flex-1 px-5 py-6 sm:px-8 lg:px-12 lg:py-10">
            {active === "for-you" && (
              <ForYouView onTotalChange={setForYouCount} />
            )}
            {active === "all-jobs" && (
              <AllJobsView onTotalChange={setAllJobsCount} />
            )}
            {active === "saved" && (
              <SavedView onTotalChange={setSavedCount} />
            )}
            {active === "dismissed" && (
              <DismissedView onTotalChange={setDismissedCount} />
            )}
            {active === "debug" && (
              <div className="max-w-6xl py-20 text-center text-stone-500">
                <p className="text-lg">
                  This view is coming soon.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
