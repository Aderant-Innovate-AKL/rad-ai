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
  state: string;
  files_changed: FileChange[];
  total_files: number;
  total_additions: number;
  total_deletions: number;
  summary: string;
  bug_id?: string;
  bug_info?: BugInfo;
}

interface TestCaseData {
  id: string;
  title: string;
  state?: string;
  area?: string;
  description?: string;
  steps?: string;
}

interface SimilarTest {
  test_case: TestCaseData;
  similarity_score: number;
}

interface AnalysisResponse {
  similar_tests: SimilarTest[];
  claude_analysis: {
    related_tests?: Array<{ test_id: string; title: string; relevance: string; suggested_action: string }>;
    new_test_suggestions?: Array<{ title: string; description: string; priority: string }>;
    summary?: string;
  };
  duplicate_analysis: Array<{ test_ids: string[]; reason: string }>;
  summary: {
    total_tests_analyzed?: number;
    related_tests_found?: number;
    duplicates_found?: number;
  };
  csv_path?: string;
  csv_filename?: string;
  download_url?: string;
}

interface ParsedBugContext {
  bug_description: string;
  repro_steps: string;
  code_changes: string;
  confidence: string;
  notes: string;
}

export default function Home() {
  const [prId, setPrId] = useState("");
  const [prInfo, setPrInfo] = useState<PRInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [prError, setPrError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Get bug info from PR response (auto-extracted from PR description)
  const bugInfo = prInfo?.bug_info || null;
  const bugId = prInfo?.bug_id || null;

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
    if (!bugInfo) {
      if (bugId) {
        // Bug ID was found but TFS fetch failed
        setAnalysisError(`Bug #${bugId} was found in PR description, but failed to fetch bug details from TFS. Check TFS connectivity or configuration.`);
      } else {
        // No bug ID found in PR description
        setAnalysisError("Please fetch a PR that contains a bug ID (e.g., #12345) in its description");
      }
      return;
    }

    setIsLoading(true);
    setActiveAction("analyze");
    setAnalysisError(null);

    try {
      // Step 1: Parse bug context using Claude AI
      console.log("Step 1: Parsing bug context with AI...");
      
      const bugInfoText = formatBugInfoDisplay();
      const prInfoText = prInfo ? formatPRInfoDisplay() : "";
      
      const parseFormData = new FormData();
      parseFormData.append("bug_info", bugInfoText);
      parseFormData.append("pr_info", prInfoText);
      
      const parseResponse = await fetch("http://localhost:8000/parse-bug-context", {
        method: "POST",
        body: parseFormData,
      });
      
      if (!parseResponse.ok) {
        const errorData = await parseResponse.json();
        throw new Error(errorData.detail || "Failed to parse bug context");
      }
      
      const parsedContext: ParsedBugContext = await parseResponse.json();
      console.log("✓ Bug context parsed successfully");
      console.log(`  Confidence: ${parsedContext.confidence}`);
      
      // Step 2: Use parsed context for test case analysis
      console.log("Step 2: Analyzing test cases with parsed context...");
      
      const formData = new FormData();
      formData.append("bug_description", parsedContext.bug_description);
      formData.append("repro_steps", parsedContext.repro_steps);
      formData.append("code_changes", parsedContext.code_changes);
      formData.append("top_k", "15");

      const response = await fetch("http://localhost:8000/analyze-bug", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to analyze test cases");
      }

      const data = await response.json();
      setAnalysisResult(data);
      setShowModal(true);
      console.log("✓ Analysis complete!");
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
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

    // Clean up AI summary - remove markdown headers like "# PR Summary" or "# Pull Request Summary"
    const cleanSummary = (prInfo.summary || "No AI summary available")
      .replace(/^#\s*(PR|Pull Request)\s*Summary\s*\n*/i, "")
      .trim();

    return `PR #${prInfo.pr_number} (${prInfo.state})

📌 TITLE
${prInfo.title}

🤖 AI SUMMARY (Anthropic Claude)
${cleanSummary}

📊 GITHUB STATS
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
            Test Link AI
          </h1>
          <p className="max-w-md text-lg text-slate-400">
            Enter a PR number to fetch details and analyze test cases.
            Bug ID will be extracted automatically from PR description (e.g., #12345)
          </p>
        </div>

        {/* Main Card */}
        <div className="w-full max-w-6xl">
          <div className="rounded-2xl border border-slate-700/50 bg-slate-800/50 p-8 shadow-2xl backdrop-blur-sm">
            {/* PR Input Field */}
            <div className="mb-6">
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
                    if (prId.trim()) {
                      handleFetchPRInfo();
                    }
                  }
                }}
              />
              {bugId && (
                <div className="mt-2 flex items-center gap-2 text-sm text-emerald-400">
                  <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                  Bug #{bugId} detected in PR description
                </div>
              )}
            </div>

            {/* Analysis Error Display */}
            {analysisError && (
              <div className="mb-4 rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3 text-red-400">
                ❌ {analysisError}
              </div>
            )}

            {/* Info Display Row */}
            <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
              {/* Bug Info Display */}
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-300">
                  Bug Information {bugId ? `(#${bugId})` : "(auto-detected from PR)"}
                </label>
                <div className="relative">
                  <textarea
                    readOnly
                    value={
                      bugInfo
                        ? formatBugInfoDisplay()
                        : prInfo && bugId
                          ? `Bug #${bugId} was found in PR description, but failed to fetch details from TFS.\n\nPossible causes:\n• TFS server is not reachable\n• TFS credentials are not configured\n• Bug ID does not exist in TFS`
                          : prInfo && !bugId
                            ? "No bug ID found in PR description.\nPR descriptions should contain a bug ID with # prefix (e.g., #12345)"
                            : "Bug details will appear here after fetching PR info..."
                    }
                    className={`h-96 w-full resize-none rounded-xl border bg-slate-900/70 px-5 py-4 font-mono text-sm leading-relaxed outline-none transition-all ${
                      bugInfo
                        ? "border-blue-500/30 text-slate-300"
                        : prInfo && bugId
                          ? "border-red-500/50 text-red-400"
                          : prInfo && !bugId
                            ? "border-amber-500/50 text-amber-400"
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
                        ? "Loading PR information and generating AI summary...\nThis may take a moment."
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
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
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
                Fetch PR Info & Bug
              </button>

              <button
                onClick={handleAnalyzeTestCases}
                disabled={!bugInfo || isLoading}
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

        {/* Analysis Results Modal */}
        {showModal && analysisResult && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="relative max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-800 shadow-2xl">
              {/* Modal Header */}
              <div className="flex items-center justify-between border-b border-slate-700 bg-slate-900/50 px-6 py-4">
                <h2 className="text-xl font-bold text-white">
                  🔍 Test Case Analysis Results
                </h2>
                <button
                  onClick={() => setShowModal(false)}
                  className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-700 hover:text-white"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal Content */}
              <div className="max-h-[calc(90vh-120px)] overflow-y-auto p-6">
                {/* Summary Stats */}
                <div className="mb-6 grid grid-cols-3 gap-4">
                  <div className="rounded-xl bg-blue-500/10 border border-blue-500/30 p-4 text-center">
                    <div className="text-3xl font-bold text-blue-400">
                      {analysisResult.summary?.total_tests_analyzed || analysisResult.similar_tests?.length || 0}
                    </div>
                    <div className="text-sm text-slate-400">Tests Analyzed</div>
                  </div>
                  <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4 text-center">
                    <div className="text-3xl font-bold text-emerald-400">
                      {analysisResult.summary?.related_tests_found || analysisResult.claude_analysis?.related_tests?.length || 0}
                    </div>
                    <div className="text-sm text-slate-400">Related Tests</div>
                  </div>
                  <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 p-4 text-center">
                    <div className="text-3xl font-bold text-amber-400">
                      {analysisResult.summary?.duplicates_found || analysisResult.duplicate_analysis?.length || 0}
                    </div>
                    <div className="text-sm text-slate-400">Duplicates Found</div>
                  </div>
                </div>

                {/* Similar Tests Table */}
                {analysisResult.similar_tests && analysisResult.similar_tests.length > 0 && (
                  <div className="mb-6">
                    <h3 className="mb-3 text-lg font-semibold text-emerald-400">📋 Similar Test Cases</h3>
                    <div className="overflow-x-auto rounded-xl border border-slate-700">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-900/50 text-slate-300">
                          <tr>
                            <th className="px-4 py-3 font-medium">ID</th>
                            <th className="px-4 py-3 font-medium">Title</th>
                            <th className="px-4 py-3 font-medium">Similarity</th>
                            <th className="px-4 py-3 font-medium">State</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {analysisResult.similar_tests.map((test, idx) => (
                            <tr key={idx} className="bg-slate-800/50 hover:bg-slate-700/50">
                              <td className="px-4 py-3 font-mono text-blue-400">{test.test_case.id}</td>
                              <td className="px-4 py-3 text-slate-300">{test.test_case.title}</td>
                              <td className="px-4 py-3">
                                <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                                  test.similarity_score >= 0.8 ? "bg-emerald-500/20 text-emerald-400" :
                                  test.similarity_score >= 0.6 ? "bg-amber-500/20 text-amber-400" :
                                  "bg-slate-500/20 text-slate-400"
                                }`}>
                                  {(test.similarity_score * 100).toFixed(1)}%
                                </span>
                              </td>
                              <td className="px-4 py-3 text-slate-400">{test.test_case.state || "N/A"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Claude Analysis - Related Tests */}
                {analysisResult.claude_analysis?.related_tests && analysisResult.claude_analysis.related_tests.length > 0 && (
                  <div className="mb-6">
                    <h3 className="mb-3 text-lg font-semibold text-purple-400">🤖 AI-Identified Related Tests</h3>
                    <div className="overflow-x-auto rounded-xl border border-slate-700">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-900/50 text-slate-300">
                          <tr>
                            <th className="px-4 py-3 font-medium">Test ID</th>
                            <th className="px-4 py-3 font-medium">Title</th>
                            <th className="px-4 py-3 font-medium">Relevance</th>
                            <th className="px-4 py-3 font-medium">Suggested Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {analysisResult.claude_analysis.related_tests.map((test, idx) => (
                            <tr key={idx} className="bg-slate-800/50 hover:bg-slate-700/50">
                              <td className="px-4 py-3 font-mono text-purple-400">{test.test_id}</td>
                              <td className="px-4 py-3 text-slate-300">{test.title}</td>
                              <td className="px-4 py-3 text-slate-400">{test.relevance}</td>
                              <td className="px-4 py-3">
                                <span className="rounded-full bg-purple-500/20 px-2 py-1 text-xs text-purple-400">
                                  {test.suggested_action}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* New Test Suggestions */}
                {analysisResult.claude_analysis?.new_test_suggestions && analysisResult.claude_analysis.new_test_suggestions.length > 0 && (
                  <div className="mb-6">
                    <h3 className="mb-3 text-lg font-semibold text-amber-400">💡 Suggested New Tests</h3>
                    <div className="overflow-x-auto rounded-xl border border-slate-700">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-slate-900/50 text-slate-300">
                          <tr>
                            <th className="px-4 py-3 font-medium">Title</th>
                            <th className="px-4 py-3 font-medium">Description</th>
                            <th className="px-4 py-3 font-medium">Priority</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                          {analysisResult.claude_analysis.new_test_suggestions.map((suggestion, idx) => (
                            <tr key={idx} className="bg-slate-800/50 hover:bg-slate-700/50">
                              <td className="px-4 py-3 font-medium text-slate-300">{suggestion.title}</td>
                              <td className="px-4 py-3 text-slate-400">{suggestion.description}</td>
                              <td className="px-4 py-3">
                                <span className={`rounded-full px-2 py-1 text-xs font-medium ${
                                  suggestion.priority === "high" ? "bg-red-500/20 text-red-400" :
                                  suggestion.priority === "medium" ? "bg-amber-500/20 text-amber-400" :
                                  "bg-slate-500/20 text-slate-400"
                                }`}>
                                  {suggestion.priority}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* AI Summary */}
                {analysisResult.claude_analysis?.summary && (
                  <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                    <h3 className="mb-2 text-lg font-semibold text-slate-300">📝 Analysis Summary</h3>
                    <p className="whitespace-pre-wrap text-slate-400">{analysisResult.claude_analysis.summary}</p>
                  </div>
                )}
              </div>

              {/* Modal Footer */}
              <div className="border-t border-slate-700 bg-slate-900/50 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    {analysisResult.csv_filename && analysisResult.download_url && (
                      <a
                        href={`http://localhost:8000${analysisResult.download_url}`}
                        download={analysisResult.csv_filename}
                        className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-6 py-2 font-medium text-white transition-colors hover:bg-emerald-500"
                      >
                        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Download CSV Report
                      </a>
                    )}
                  </div>
                  <button
                    onClick={() => setShowModal(false)}
                    className="rounded-xl bg-slate-700 px-6 py-2 font-medium text-white transition-colors hover:bg-slate-600"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
