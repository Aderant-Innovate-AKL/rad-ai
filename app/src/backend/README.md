# Test Case Analysis API - Backend

AI-powered test case analysis system using Anthropic Claude for analyzing bug reports and identifying related test cases.

## Features

- **Bug Report Analysis**: Analyzes bug descriptions and code changes to find related test cases
- **Semantic Search**: Uses sentence transformers to find semantically similar test cases
- **AI-Powered Insights**: Claude provides detailed analysis of test case relevance and suggestions
- **Duplicate Detection**: Identifies duplicate or overlapping test cases
- **Test Update Suggestions**: Recommends changes to existing test cases based on bug fixes

## Setup

### 1. Install Dependencies

```bash
cd app/src/backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the backend directory:

```bash
cp .env.example .env
```

Add your Anthropic API key to `.env`:

```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 3. Run the Server

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- OpenAPI schema: http://localhost:8000/openapi.json

## API Endpoints

### POST `/analyze-bug`

Analyze a bug report against test cases.

**Request:**
- `csv_file` (file): CSV file containing test cases
- `bug_description` (string): Description of the bug
- `repro_steps` (string): Steps to reproduce the bug
- `code_changes` (string): Code changes made to fix the bug
- `top_k` (integer, optional): Number of similar test cases to return (default: 15)

**Response:**
```json
{
  "similar_tests": [...],
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

### POST `/detect-duplicates`

Detect duplicate test cases in a CSV file.

**Request:**
- `csv_file` (file): CSV file containing test cases
- `similarity_threshold` (float, optional): Similarity threshold 0-1 (default: 0.85)

**Response:**
```json
{
  "duplicate_groups": [...],
  "total_duplicates_found": 5
}
```

### GET `/health`

Health check endpoint.

## Testing

### Using cURL

```bash
# Analyze a bug report
curl -X POST "http://localhost:8000/analyze-bug" \
  -F "csv_file=@../../test_cases_expert_disbursements.csv" \
  -F "bug_description=Users cannot post disbursements when currency override is enabled" \
  -F "repro_steps=1. Enable currency override\n2. Create disbursement\n3. Click Post" \
  -F "code_changes=Fixed currency validation logic in posting process"

# Detect duplicates
curl -X POST "http://localhost:8000/detect-duplicates" \
  -F "csv_file=@../../test_cases_expert_disbursements.csv" \
  -F "similarity_threshold=0.85"
```

### Using Python

```python
import requests

# Analyze bug
with open('test_cases.csv', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/analyze-bug',
        files={'csv_file': f},
        data={
            'bug_description': 'Bug description here',
            'repro_steps': 'Steps to reproduce',
            'code_changes': 'Code changes made',
            'top_k': 15
        }
    )
    print(response.json())
```

## CSV Format

The CSV file should have the following columns:

- `ID`: Test case ID
- `Title`: Test case title
- `State`: Test case state (e.g., Active, Closed)
- `Area`: Area path or module
- `Created Date`: Creation date
- `Description`: Detailed description
- `Steps`: Test steps (can include expected results)

Example:
```csv
ID,Title,State,Area,Created Date,Description,Steps
12345,Test Currency Override,Active,Disbursements,2024-01-01,Test description here,Step 1: Do this || Step 2: Do that
```

## Architecture

```
backend/
├── agent/
│   └── agent.py          # Core TestCaseAgent class
├── main.py               # FastAPI application
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not in git)
└── .env.example         # Example environment configuration
```

## Models Used

- **LLM**: Anthropic Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- **Embeddings**: all-MiniLM-L6-v2 (via sentence-transformers)

## Performance Notes

- First request will be slower due to model loading (~5-10 seconds)
- Embeddings are cached for improved performance
- Large CSV files (>1000 test cases) may take longer to process
- Consider adjusting `top_k` parameter to balance thoroughness vs. speed

## Troubleshooting

### "Anthropic API key not provided"
Make sure your `.env` file exists and contains a valid `ANTHROPIC_API_KEY`.

### "Module not found" errors
Install all dependencies: `pip install -r requirements.txt`

### Slow first request
This is normal - the embedding model needs to load. Subsequent requests will be faster.

### Out of memory errors
Reduce the `top_k` parameter or process fewer test cases at once.
