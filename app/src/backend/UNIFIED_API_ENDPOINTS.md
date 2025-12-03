# Unified API Endpoints Reference

All endpoints are now available at: **http://localhost:8000**

## Core Endpoints

### 🏠 Root & Health
- `GET /` - API information and version
- `GET /health` - Health check with agent status

## 🔍 Bug Analysis Endpoints

### Analyze Bug Reports
1. **POST /analyze** (JSON-based)
   - Content-Type: `application/json`
   - Body: `BugReportRequest` model
   - Returns: `AnalysisResponse` with similar tests and summary
   - Use for: Programmatic API calls

2. **POST /analyze-bug** (Form-based)
   - Content-Type: `multipart/form-data`
   - Supports CSV file upload
   - Auto-detection mode (no CSV) or manual mode (with CSV)
   - Use for: Web forms with file uploads

### Request Example (JSON):
```json
{
  "bug_description": "Application crashes when...",
  "repro_steps": "1. Open app\n2. Click button",
  "code_changes": "Fixed null pointer in module X",
  "top_k": 15,
  "similarity_threshold": 0.5,
  "output_format": "csv"
}
```

### Request Example (Form):
```bash
curl -X POST http://localhost:8000/analyze-bug \
  -F "bug_description=App crashes..." \
  -F "repro_steps=1. Open app..." \
  -F "code_changes=Fixed bug in..." \
  -F "top_k=15"
```

## 📦 Test Case Management

### Test Case Areas
- `GET /areas` - List all available test case areas/families
  - Returns: Area names, descriptions, test counts

- `POST /detect-areas` - Detect relevant areas (query params)
  - Params: `bug_description`, `repro_steps`
  - Returns: Detected areas with confidence scores

- `POST /detect-area` - Detect relevant areas (form-based)
  - Form fields: `bug_description`, `repro_steps`
  - Returns: Same as `/detect-areas` but form-friendly

### Duplicate Detection
- `POST /detect-duplicates`
  - Upload CSV file
  - Form field: `similarity_threshold` (default: 0.85)
  - Returns: Groups of duplicate test cases

## 📊 Statistics & Downloads

- `GET /stats` - Get statistics about loaded test cases
  - Total test cases
  - Areas loaded
  - Memory usage

- `GET /download/{filename}` - Download generated CSV files
  - Example: `/download/bug_analysis_20251204_120952.csv`
  - Returns: CSV file as attachment

## 🐛 TFS/Azure DevOps Integration

### Fetch Bug Information
- `GET /fetch-bug-info/{bug_id}`
  - Example: `/fetch-bug-info/12345`
  - Returns: Bug title, description, repro steps from TFS
  - Requires: TFS environment variables configured

### Response Model:
```json
{
  "bug_id": "12345",
  "title": "Bug title",
  "description": "Bug description",
  "repro_steps": "Reproduction steps"
}
```

## 🔧 GitHub Integration

### Fetch Pull Request Info
- `GET /fetch-pr-info/{pr_number}`
  - Example: `/fetch-pr-info/42`
  - Returns: PR title, state, changed files with stats
  - Requires: GitHub environment variables configured

### Response Model:
```json
{
  "pr_number": 42,
  "title": "PR title",
  "state": "open",
  "files_changed": [
    {
      "filename": "src/main.py",
      "status": "modified",
      "additions": 10,
      "deletions": 5,
      "changes": 15
    }
  ],
  "total_files": 3,
  "total_additions": 50,
  "total_deletions": 20
}
```

### AI-Powered PR Summary
- `GET /summarize-pr/{pr_number}`
  - Example: `/summarize-pr/42`
  - Returns: Claude-generated summary of PR changes
  - Includes: Overall summary, key changes by category
  - Requires: ANTHROPIC_API_KEY configured

### Response Model:
```json
{
  "pr_number": 42,
  "title": "PR title",
  "summary": "AI-generated comprehensive summary...",
  "files_changed": ["file1.py", "file2.js"],
  "total_files": 2
}
```

## 📝 Request/Response Models

### BugReportRequest
```python
{
  "bug_description": str,      # Required
  "repro_steps": str,          # Required
  "code_changes": str,         # Required
  "top_k": int,                # Optional, default: 15
  "similarity_threshold": float, # Optional, default: 0.5
  "output_format": str         # Optional, "csv" or "dict"
}
```

### AnalysisResponse
```python
{
  "success": bool,
  "message": str,
  "summary": {
    "total_similar_tests": int,
    "areas_detected": [...],
    "similarity_scores": {...}
  },
  "csv_path": str,             # Path to generated CSV
  "similar_tests": [...]       # Top 10 similar tests preview
}
```

### HealthResponse
```python
{
  "status": str,               # "healthy" or "unhealthy"
  "agent_initialized": bool,
  "mcp_enabled": bool
}
```

## 🔐 Environment Variables Required

```env
# Required for all operations
ANTHROPIC_API_KEY=your_anthropic_key

# Optional: for TFS integration
TFS_BASE_URL=https://tfs.example.com/tfs
TFS_COLLECTION=YourCollection
TFS_PROJECT=YourProject
TFS_PAT=your_personal_access_token

# Optional: for GitHub integration
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo
```

## 🚀 Quick Start Examples

### 1. Check API Health
```bash
curl http://localhost:8000/health
```

### 2. Analyze a Bug (JSON)
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "bug_description": "Login page crashes on submit",
    "repro_steps": "1. Open login\n2. Click submit",
    "code_changes": "Added null check",
    "top_k": 10
  }'
```

### 3. Fetch Bug from TFS
```bash
curl http://localhost:8000/fetch-bug-info/12345
```

### 4. Get PR Summary
```bash
curl http://localhost:8000/summarize-pr/42
```

### 5. List Available Test Areas
```bash
curl http://localhost:8000/areas
```

### 6. Detect Duplicates
```bash
curl -X POST http://localhost:8000/detect-duplicates \
  -F "csv_file=@test_cases.csv" \
  -F "similarity_threshold=0.85"
```

## 📖 API Documentation

Access interactive documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Both provide:
- Complete endpoint documentation
- Request/response schemas
- Interactive testing interface
- Code examples in multiple languages

## 🎯 Use Cases

### For Developers
- Analyze bugs against test cases
- Fetch bug details from TFS automatically
- Get AI summaries of code changes in PRs
- Detect duplicate test cases

### For QA Engineers
- Find related test cases for new bugs
- Identify gaps in test coverage
- Detect redundant test cases
- Auto-categorize test cases by area

### For Automation
- Integrate with CI/CD pipelines
- Auto-tag PRs with affected test areas
- Generate test coverage reports
- Sync bugs and test cases between systems

## ⚠️ Error Handling

All endpoints return standard HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid input)
- `401` - Authentication failed
- `403` - Forbidden (rate limit, access denied)
- `404` - Resource not found
- `500` - Internal server error
- `503` - Service unavailable (agent not initialized)
- `504` - Request timeout

Error responses include:
```json
{
  "detail": "Error message describing what went wrong"
}
```

## 🔄 CORS Configuration

Currently configured to allow all origins (`*`). For production:
```python
allow_origins=[
    "https://your-frontend.com",
    "http://localhost:3000"
]
```

## 📊 Performance Notes

- Agent initialization happens once at startup
- Subsequent requests reuse the same agent instance
- MCP server enables efficient test case loading
- CSV files are processed asynchronously
- Large PR diffs are truncated to 2000 chars per file

## 🛠️ Troubleshooting

### Agent Not Initialized
- Check logs for startup errors
- Verify ANTHROPIC_API_KEY is set
- Ensure test case CSV files are accessible

### TFS Connection Failed
- Verify TFS_BASE_URL, TFS_COLLECTION, TFS_PROJECT
- Check TFS_PAT token has correct permissions
- Ensure TFS server is accessible

### GitHub API Errors
- Verify GITHUB_TOKEN has correct scopes
- Check rate limits (60/hour without token, 5000/hour with token)
- Ensure repo is accessible with the token

---

**Version**: 2.0.0  
**Last Updated**: December 4, 2025  
**Port**: 8000  
**Host**: 0.0.0.0 (all interfaces)
