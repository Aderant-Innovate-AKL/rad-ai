"use client";

import { useState } from "react";

interface BugInfo {
  bug_id: string;
  title: string;
  description: string;
  repro_steps: string;
}

interface FileChange {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
}

interface PRInfo {
  pr_number: number;
  title: string;
  files_changed: FileChange[];
  total_files: number;
  total_additions: number;
  total_deletions: number;
}

export default function Home() {
  const [bugId, setBugId] = useState("");
  const [prId, setPrId] = useState("");
  const [bugInfo, setBugInfo] = useState<BugInfo | null>(null);
  const [prInfo, setPrInfo] = useState<PRInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [bugError, setBugError] = useState<string | null>(null);
  const [prError, setPrError] = useState<string | null>(null);

  const handleFetchBugInfo = async () => {
    if (!bugId.trim()) return;
    setIsLoading(true);
    setActiveAction("fetchBug");
    setBugError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/fetch-bug-info/${encodeURIComponent(bugId.trim())}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to fetch bug info");
      }

      const data = await response.json();
      setBugInfo(data);
    } catch (err) {
      setBugError(err instanceof Error ? err.message : "An error occurred");
      setBugInfo(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFetchPRInfo = async () => {
    if (!prId.trim()) return;
    setIsLoading(true);
    setActiveAction("fetchPR");
    setPrError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/fetch-pr-info/${encodeURIComponent(prId.trim())}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to fetch PR info");
      }

      const data = await response.json();
      setPrInfo(data);
    } catch (err) {
      setPrError(err instanceof Error ? err.message : "An error occurred");
      setPrInfo(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnalyzeTestCases = async () => {
    if (!bugId.trim()) return;
    setIsLoading(true);
    setActiveAction("analyze");
    // TODO: Implement API call for test case analysis
    console.log("Analyzing test cases for:", bugId);
    setTimeout(() => setIsLoading(false), 1000);
  };

  const formatBugInfoDisplay = () => {
    if (!bugInfo) return "";

    return `BUG ID: ${bugInfo.bug_id}

📌 TITLE
${bugInfo.title}

📝 DESCRIPTION
${bugInfo.description || "No description provided"}

🔁 REPRODUCTION STEPS
${bugInfo.repro_steps || "No reproduction steps provided"}
`;
  };

  const formatPRInfoDisplay = () => {
    if (!prInfo) return "";

    const filesDisplay = prInfo.files_changed
      .map((f) => {
        const statusIcon =
          f.status === "added" ? "➕" : f.status === "removed" ? "➖" : "📝";
        return `${statusIcon} ${f.filename}\n   +${f.additions} -${f.deletions}`;
      })
      .join("\n\n");

    return `PR #${prInfo.pr_number}

📌 TITLE
${prInfo.title}

📊 SUMMARY
Files Changed: ${prInfo.total_files}
Total Additions: +${prInfo.total_additions}
Total Deletions: -${prInfo.total_deletions}

📁 FILES CHANGED (${prInfo.total_files})
${filesDisplay}
`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiMyMDIwMjAiIGZpbGwtb3BhY2l0eT0iMC4xIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIxIi8+PC9nPjwvZz48L3N2Zz4=')] opacity-40"></div>

      <main className="relative flex min-h-screen flex-col items-center px-6 py-12">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-sm text-emerald-400">
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400"></span>
            AI-Powered Analysis
          </div>
          <h1 className="mb-3 bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-5xl font-bold tracking-tight text-transparent">
            Test Case Analyzer
          </h1>
          <p className="max-w-md text-lg text-slate-400">
            Enter a bug ID or PR number to fetch details and analyze test cases
          </p>
        </div>

        {/* Main Card */}
        <div className="w-full max-w-6xl">
          <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50 p-8 shadow-2xl backdrop-blur-sm">
            {/* Input Fields Row */}
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Bug ID Input */}
              <div>
                <label
                  htmlFor="bugId"
                  className="mb-2 block text-sm font-medium text-slate-300"
                >
                  Bug ID
                </label>
                <input
                  type="text"
                  id="bugId"
                  value={bugId}
                  onChange={(e) => setBugId(e.target.value)}
                  placeholder="Enter bug ID (e.g., 12345)"
                  className="w-full rounded-xl border border-slate-600 bg-slate-900/50 px-5 py-4 text-lg text-white placeholder-slate-500 outline-none transition-all focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleFetchBugInfo();
                    }
                  }}
                />
              </div>

              {/* PR ID Input */}
              <div>
                <label
                  htmlFor="prId"
                  className="mb-2 block text-sm font-medium text-slate-300"
                >
                  PR Number
                </label>
                <input
                  type="text"
                  id="prId"
                  value={prId}
                  onChange={(e) => setPrId(e.target.value)}
                  placeholder="Enter PR number (e.g., 42)"
                  className="w-full rounded-xl border border-slate-600 bg-slate-900/50 px-5 py-4 text-lg text-white placeholder-slate-500 outline-none transition-all focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      handleFetchPRInfo();
                    }
                  }}
                />
              </div>
            </div>

            {/* Info Display Row */}
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Bug Info Display */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">
                  Bug Information
                </label>
                <div className="relative">
                  <textarea
                    readOnly
                    value={
                      isLoading && activeAction === "fetchBug"
                        ? "Loading bug information..."
                        : bugError
                          ? `❌ Error: ${bugError}`
                          : bugInfo
                            ? formatBugInfoDisplay()
                            : "Bug details will appear here after fetching..."
                    }
                    className={`h-96 w-full resize-none rounded-xl border bg-slate-900/70 px-5 py-4 font-mono text-sm leading-relaxed outline-none transition-all ${
                      bugError
                        ? "border-red-500/50 text-red-400"
                        : bugInfo
                          ? "border-blue-500/30 text-slate-300"
                          : "border-slate-600 text-slate-500"
                    }`}
                  />
                </div>
              </div>

              {/* PR Info Display */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">
                  PR File Changes
                </label>
                <div className="relative">
                  <textarea
                    readOnly
                    value={
                      isLoading && activeAction === "fetchPR"
                        ? "Loading PR information..."
                        : prError
                          ? `❌ Error: ${prError}`
                          : prInfo
                            ? formatPRInfoDisplay()
                            : "PR details will appear here after fetching..."
                    }
                    className={`h-96 w-full resize-none rounded-xl border bg-slate-900/70 px-5 py-4 font-mono text-sm leading-relaxed outline-none transition-all ${
                      prError
                        ? "border-red-500/50 text-red-400"
                        : prInfo
                          ? "border-purple-500/30 text-slate-300"
                          : "border-slate-600 text-slate-500"
                    }`}
                  />
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <button
                onClick={handleFetchBugInfo}
                disabled={!bugId.trim() || isLoading}
                className="group flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 px-6 py-4 font-semibold text-white shadow-lg shadow-blue-500/25 transition-all hover:from-blue-500 hover:to-blue-400 hover:shadow-blue-500/40 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
              >
                {isLoading && activeAction === "fetchBug" ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                ) : (
                  <svg
                    className="h-5 w-5 transition-transform group-hover:scale-110"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                )}
                Fetch Bug Info
              </button>

              <button
                onClick={handleFetchPRInfo}
                disabled={!prId.trim() || isLoading}
                className="group flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 px-6 py-4 font-semibold text-white shadow-lg shadow-purple-500/25 transition-all hover:from-purple-500 hover:to-purple-400 hover:shadow-purple-500/40 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
              >
                {isLoading && activeAction === "fetchPR" ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                ) : (
                  <svg
                    className="h-5 w-5 transition-transform group-hover:scale-110"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                )}
                Fetch PR File Changes
              </button>

              <button
                onClick={handleAnalyzeTestCases}
                disabled={!bugId.trim() || isLoading}
                className="group flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-emerald-500 px-6 py-4 font-semibold text-white shadow-lg shadow-emerald-500/25 transition-all hover:from-emerald-500 hover:to-emerald-400 hover:shadow-emerald-500/40 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
              >
                {isLoading && activeAction === "analyze" ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                ) : (
                  <svg
                    className="h-5 w-5 transition-transform group-hover:scale-110"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    />
                  </svg>
                )}
                Find Test Cases
              </button>
            </div>
          </div>

          {/* Helper text */}
          <p className="mt-4 text-center text-sm text-slate-500">
            Connected to backend at{" "}
            <code className="rounded bg-slate-800 px-2 py-0.5 text-emerald-400">
              localhost:8000
            </code>
          </p>
        </div>
      </main>
    </div>
  );
}
