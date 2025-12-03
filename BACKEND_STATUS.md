# Test Case Analysis Agent - Backend Implementation

## Overview

The backend has been successfully implemented with the following components:

### ✅ Completed Features

1. **Test Case Agent (`agent/agent.py`)**
   - Loads test cases from CSV files
   - Uses Anthropic Claude for intelligent analysis
   - Semantic search using sentence transformers
   - Identifies related test cases based on bug reports
   - Suggests test case updates
   - Detects duplicate test cases
   - Caches embeddings for performance

2. **FastAPI Server (`main.py`)**
   - RESTful API endpoints
   - CORS enabled for Next.js frontend
   - File upload support for CSV
   - Health check endpoint
   - Comprehensive error handling

3. **API Endpoints**
   - `POST /analyze-bug` - Main analysis endpoint
   - `POST /detect-duplicates` - Find duplicate tests
   - `GET /health` - Health check
   - `GET /` - API info

## Quick Start

### 1. Environment Setup

The `.env` file is already configured with your Anthropic API key in:
```
app/src/backend/.env
```

### 2. Install Dependencies

```bash
cd app/src/backend
pip install -r requirements.txt
```

### 3. Run the Server

```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload --port 8000
```

Server will start at: http://localhost:8000
API docs: http://localhost:8000/docs

### 4. Test the Agent

Run the test script to verify everything works:

```bash
python test_agent.py
```

## Testing the API

### Using cURL

```bash
# Analyze a bug
curl -X POST "http://localhost:8000/analyze-bug" \
  -F "csv_file=@../../../test_cases_with_descriptions_expert_disbursements.csv" \
  -F "bug_description=Users cannot post disbursements when currency override is enabled" \
  -F "repro_steps=1. Enable currency override
2. Create disbursement
3. Click Post
4. Error occurs" \
  -F "code_changes=Fixed currency validation logic" \
  -F "top_k=15"
```

### Using Python

```python
import requests

with open('test_cases.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/analyze-bug',
        files={'csv_file': f},
        data={
            'bug_description': 'Bug description',
            'repro_steps': 'Steps to reproduce',
            'code_changes': 'Code changes',
            'top_k': 15
        }
    )
    result = response.json()
    print(result)
```

## API Response Format

```json
{
  "similar_tests": [
    {
      "test_case": {
        "id": "176648",
        "title": "Test title",
        "description": "Description...",
        "steps": "Step 1:... || Step 2:...",
        ...
      },
      "similarity_score": 0.85
    }
  ],
  "claude_analysis": {
    "related_tests": [...],
    "suggested_updates": [...],
    "new_test_cases": [...],
    "duplicate_tests": [...]
  },
  "duplicate_analysis": [...],
  "summary": {
    "total_test_cases_analyzed": 100,
    "similar_tests_found": 15,
    "potential_duplicates_found": 3
  }
}
```

## Architecture

```
backend/
├── agent/
│   ├── __init__.py
│   └── agent.py              # Core TestCaseAgent class
├── main.py                   # FastAPI application
├── test_agent.py             # Test script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (with API key)
├── .env.example              # Template
└── README.md                 # Documentation
```

## How It Works

1. **CSV Upload**: Client uploads test cases CSV file
2. **Bug Analysis**: Agent receives bug description, repro steps, and code changes
3. **Semantic Search**: Finds similar test cases using embeddings
4. **Claude Analysis**: LLM analyzes relationships and provides insights
5. **Results**: Returns related tests, suggested updates, and duplicates

## Models Used

- **LLM**: Anthropic Claude 3.5 Sonnet (`claude-3-5-sonnet-20241022`)
- **Embeddings**: `all-MiniLM-L6-v2` via sentence-transformers

## Performance Notes

- **First Request**: ~10-30 seconds (model loading)
- **Subsequent Requests**: ~3-10 seconds (embeddings cached)
- **Large CSVs**: Consider adjusting `top_k` parameter

## Next Steps

### Frontend Integration
Now that the backend is ready, you can:

1. **Test the Backend**:
   ```bash
   python test_agent.py
   ```

2. **Start the Server**:
   ```bash
   python main.py
   ```

3. **Build the Frontend**:
   - Create UI in `app/src/app/page.tsx`
   - Add file upload component
   - Add bug report form
   - Display results with review/accept/reject options

### Frontend Development Plan
- [ ] CSV file upload component
- [ ] Bug report input form (description, steps, changes)
- [ ] Results display (related tests, suggestions, duplicates)
- [ ] Review interface (accept/reject suggestions)
- [ ] Export results to updated CSV

## Troubleshooting

### "Anthropic API key not provided"
Check that `.env` file exists in `app/src/backend/` with valid key.

### "Module not found"
Run: `pip install -r requirements.txt`

### Slow performance
- First request loads models (normal)
- Reduce `top_k` parameter
- Check network connection to Anthropic API

### Port already in use
Change port: `uvicorn main:app --port 8001`

## Documentation

- **FastAPI Docs**: http://localhost:8000/docs
- **Anthropic API**: https://docs.anthropic.com/
- **Sentence Transformers**: https://www.sbert.net/

---

**Status**: ✅ Backend implementation complete and ready for testing!
