# API Merge Notes

## Summary
`api.py` and `main.py` have been successfully merged into a single unified API file: `api.py`

## Changes Made

### 1. Unified API File (`api.py`)
The new `api.py` now includes all endpoints from both files:

#### From Original `api.py`:
- `/` - Root endpoint
- `/health` - Health check
- `/analyze` - Bug analysis (JSON-based)
- `/download/{filename}` - CSV file download
- `/stats` - Test case statistics
- `/areas` - List available test case areas
- `/detect-areas` - Detect relevant areas (query params)

#### From Original `main.py`:
- `/analyze-bug` - Bug analysis (Form-based with file upload)
- `/detect-area` - Detect relevant areas (form-based)
- `/detect-duplicates` - Find duplicate test cases
- `/fetch-bug-info/{bug_id}` - Fetch bug from TFS/Azure DevOps
- `/fetch-pr-info/{pr_number}` - Fetch PR info from GitHub
- `/summarize-pr/{pr_number}` - AI-powered PR summary

### 2. New Features
- **Version upgraded** to 2.0.0
- **Enhanced CORS** configuration supporting all origins
- **Better error handling** with try-except blocks
- **Unified agent initialization** using `get_agent()` function
- **TFS/Azure DevOps integration** with environment variables
- **GitHub integration** with environment variables
- **Claude AI integration** for PR summarization

### 3. Environment Variables
The unified API requires these environment variables (in `.env` file):

```env
# Anthropic API
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-haiku-4-5

# TFS/Azure DevOps Configuration
TFS_BASE_URL=https://tfs.aderant.com/tfs
TFS_COLLECTION=ADERANT
TFS_PROJECT=ExpertSuite
TFS_PAT=your_personal_access_token

# GitHub Configuration
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_org_or_username
GITHUB_REPO=your_repo_name
```

### 4. Running the Unified API

#### Option 1: Direct Python execution
```bash
cd app/src/backend
python api.py
```

#### Option 2: Using uvicorn
```bash
cd app/src/backend
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

### 5. API Documentation
Once running, access:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 6. Deprecated File
`main.py` has been marked as deprecated with a warning message. The file is kept for reference but should not be used. All new development should use `api.py`.

## Benefits of the Merge

1. **Single Entry Point**: Only one API server to run and maintain
2. **No Port Conflicts**: Both APIs were using port 8000
3. **Unified Documentation**: All endpoints in one Swagger/OpenAPI doc
4. **Better Maintainability**: Single codebase for all API functionality
5. **Consistent Error Handling**: Unified approach across all endpoints
6. **Shared Agent Instance**: More efficient resource usage

## Migration Guide for Clients

### If you were using `main.py` (port 8000):
- No changes needed! All endpoints work the same way
- Just run `python api.py` instead of `python main.py`

### If you were using `api.py` (port 8000):
- No changes needed! All original endpoints are preserved
- You now also have access to TFS/GitHub integration endpoints

### Endpoint Compatibility
All endpoint paths remain the same. The only difference is they're now all served from a single API instance.

## Testing the Merge

1. **Start the unified API**:
   ```bash
   python api.py
   ```

2. **Test health check**:
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test bug analysis** (original api.py endpoint):
   ```bash
   curl -X POST http://localhost:8000/analyze \
     -H "Content-Type: application/json" \
     -d '{"bug_description": "Test", "repro_steps": "Test", "code_changes": "Test"}'
   ```

4. **Test TFS integration** (from main.py):
   ```bash
   curl http://localhost:8000/fetch-bug-info/12345
   ```

5. **Test GitHub integration** (from main.py):
   ```bash
   curl http://localhost:8000/fetch-pr-info/42
   ```

## Notes

- The unified API uses FastAPI's automatic documentation generation
- All endpoints support both synchronous and asynchronous requests
- CORS is configured to allow all origins (configure appropriately for production)
- The agent initialization happens once at startup for better performance
- File uploads work the same way as before using multipart/form-data

## Date
Merged on: December 4, 2025
