"use client";

// Anything that throws while rendering lands here instead of a blank page.
export default function Error({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return (
    <main className="grid h-dvh place-items-center p-6">
      <div className="flex max-w-120 flex-col items-start gap-4 rounded-card bg-card p-7 shadow-card">
        <h1 className="font-[560]">Something went wrong on this page.</h1>
        <p className="text-secondary">Saved conversations are still in this browser. Try again, or reload the page.</p>
        <button
          type="button"
          onClick={() => retry()}
          className="h-10.5 rounded-full bg-ink px-4.5 text-small font-[560] text-on-answer"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
