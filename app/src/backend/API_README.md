# Test Case Analysis API

REST API backend for the Test Case Analysis Agent, ready for frontend integration.

## Features

- ✅ Analyze bug reports and find related test cases
- ✅ Export results to CSV format
- ✅ Download generated CSV files
- ✅ Auto-detect relevant test case areas
- ✅ Get statistics and area information
- ✅ CORS enabled for frontend integration
- ✅ Interactive API documentation (Swagger UI)

## Quick Start

### 1. Start the API Server

```bash
cd app/src/backend
python api.py
```

Or using uvicorn directly:
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

### 2. View API Documentation

Open your browser and navigate to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 3. Test the API

Run the test client:
```bash
python test_api.py
```

This will test all endpoints and verify the API is working correctly.

## API Endpoints

### Health & Info

- **GET /**  
  Root endpoint with API information

- **GET /health**  
  Health check - returns agent status
  
  Response:
  ```json
  {
    "status": "healthy",
    "agent_initialized": true,
    "mcp_enabled": true
  }
  ```

### Test Case Areas

- **GET /areas**  
  List all available test case areas
  
  Response:
  ```json
  {
    "total_areas": 5,
    "total_test_cases": 1000,
    "areas": [...]
  }
  ```

- **GET /stats**  
  Get statistics about loaded test cases

- **POST /detect-areas**  
  Detect which areas are relevant to a bug description
  
  Query params:
  - `bug_description` (required)
  - `repro_steps` (optional)

### Analysis

- **POST /analyze**  
  Main endpoint: Analyze bug report and generate CSV
  
  Request body:
  ```json
  {
    "bug_description": "Users cannot post disbursements...",
    "repro_steps": "1. Navigate to...\n2. Enable...",
    "code_changes": "Fixed currency validation logic...",
    "top_k": 20,
    "similarity_threshold": 0.5,
    "output_format": "csv"
  }
  ```
  
  Response:
  ```json
  {
    "success": true,
    "message": "Analysis completed successfully",
    "summary": {
      "total_test_cases_analyzed": 200,
      "similar_tests_found": 20,
      "potential_duplicates_found": 5
    },
    "csv_path": "bug_analysis_20250104_143022.csv",
    "similar_tests": [...]
  }
  ```

- **GET /download/{filename}**  
  Download a generated CSV file
  
  Example: `/download/bug_analysis_20250104_143022.csv`

## Frontend Integration

### Example: React/Next.js

```typescript
// Analyze bug report
const analyzeBug = async (bugData) => {
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      bug_description: bugData.description,
      repro_steps: bugData.steps,
      code_changes: bugData.changes,
      top_k: 20,
      similarity_threshold: 0.5,
      output_format: 'csv'
    })
  });
  
  const result = await response.json();
  return result;
};

// Download CSV
const downloadCSV = (filename) => {
  window.open(`http://localhost:8000/download/${filename}`, '_blank');
};
```

### Example: Vanilla JavaScript

```javascript
async function analyzeBugReport() {
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      bug_description: document.getElementById('bug-desc').value,
      repro_steps: document.getElementById('repro-steps').value,
      code_changes: document.getElementById('code-changes').value,
      top_k: 20,
      similarity_threshold: 0.5,
      output_format: 'csv'
    })
  });
  
  const data = await response.json();
  
  if (data.success) {
    // Show results
    console.log('Analysis complete:', data.summary);
    
    // Provide download link
    if (data.csv_path) {
      const filename = data.csv_path.split('/').pop();
      downloadLink.href = `http://localhost:8000/download/${filename}`;
    }
  }
}
```

## CSV Output Format

The exported CSV contains the following columns:

| Column | Description |
|--------|-------------|
| Test Case ID | Unique identifier |
| Title | Test case title |
| State | Current state (Ready, Closed, etc.) |
| Area | Test case area/category |
| Created Date | When test was created |
| Similarity Score | Similarity to bug (0.0-1.0) |
| Reasoning | Why this test case was selected |
| Duplicate Classification | TRUE DUPLICATES, OVERLAPPING, or DISTINCT |
| Related Test IDs | IDs of related test cases (for duplicates/overlapping) |
| Suggested Update | AI-suggested updates to the test case |

## Configuration

### Environment Variables

Create a `.env` file in the `backend` directory:

```env
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
ANTHROPIC_MODEL=claude-haiku-4-5
```

### CORS Configuration

For production, update the CORS settings in `api.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Analyze bug
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "bug_description": "Test bug",
    "repro_steps": "1. Do this\n2. Do that",
    "code_changes": "Fixed the issue",
    "top_k": 10,
    "similarity_threshold": 0.5,
    "output_format": "csv"
  }'

# Download CSV
curl -O http://localhost:8000/download/bug_analysis_20250104_143022.csv
```

### Automated Testing

```bash
python test_api.py
```

## Production Deployment

### Using Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using Gunicorn

```bash
pip install gunicorn
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Troubleshooting

### API won't start
- Check if port 8000 is already in use
- Verify Python environment is activated
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check `.env` file has valid ANTHROPIC_API_KEY

### CORS errors
- Verify CORS middleware is configured correctly
- Check browser console for specific CORS error
- For development, use `allow_origins=["*"]`

### CSV not generating
- Check disk space and write permissions
- Verify test case CSV files exist in workspace root
- Check API logs for specific error messages

## API Response Codes

- **200**: Success
- **400**: Bad request (invalid parameters)
- **404**: Resource not found
- **422**: Validation error
- **500**: Internal server error
- **503**: Service unavailable (agent not initialized)

## Next Steps

1. ✅ Start the API server
2. ✅ Test with the test client
3. ✅ View the interactive docs at /docs
4. ✅ Integrate with your frontend
5. ✅ Deploy to production

## Support

For issues or questions, check:
- API documentation: http://localhost:8000/docs
- Test client output: `python test_api.py`
- Server logs when running `python api.py`
