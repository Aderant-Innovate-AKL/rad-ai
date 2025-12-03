# MCP-Based Test Case Agent

## Overview

The Test Case Agent now uses a **Model Context Protocol (MCP)** server to intelligently select and load test case CSV files based on bug report descriptions. This eliminates the need for manual CSV file selection and enables automatic area detection.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Bug Report Input                        │
│  - Description: "Cannot post disbursements..."              │
│  - Repro Steps                                              │
│  - Code Changes                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              TestCaseAgent (agent.py)                       │
│  - Receives bug report                                      │
│  - Calls MCP server for area detection                     │
│  - Auto-loads relevant test cases                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         MCP Test Case Server (test_case_server.py)         │
│                                                             │
│  Tools Available:                                           │
│  ├─ detect_relevant_areas()    ← Area detection            │
│  ├─ search_by_area()           ← Load by area              │
│  ├─ search_by_keywords()       ← Keyword search            │
│  ├─ get_by_id()                ← Get specific test         │
│  ├─ list_areas()               ← List all areas            │
│  └─ get_statistics()           ← Get stats                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Area Configuration (area_config.py)              │
│  - CSV_FILE_MAPPING: Area → CSV file mapping               │
│  - AREA_KEYWORDS: Keywords for each area                   │
│  - AREA_DESCRIPTIONS: Detailed descriptions                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CSV Files (Root)                         │
│  ├─ test_cases_expert_disbursements.csv                    │
│  ├─ test_cases_billing.csv                                 │
│  ├─ test_cases_accounts_payable.csv                        │
│  ├─ test_cases_collections.csv                             │
│  └─ test_cases_infrastructure.csv                          │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. **Automatic Area Detection**
The MCP server analyzes bug descriptions and automatically detects which app family/area is relevant:

- **Expert Disbursements**: Expense tracking, disbursement posting, cost codes
- **Billing**: Invoicing, prebilling, WIP management
- **Accounts Payable**: Vendor invoices, payment processing
- **Collections**: Account receivables, payment plans
- **Infrastructure**: Security, customization, system-level features

### 2. **Keyword-Based Classification**
Uses domain-specific keywords to determine area relevance:

```python
AREA_KEYWORDS = {
    "Expert Disbursements": ["disbursement", "disb", "posting", "split", "merge", ...],
    "Billing": ["billing", "prebill", "invoice", "WIP", "markup", ...],
    # ... etc
}
```

### 3. **Confidence Scoring**
Provides confidence scores for area detection to handle ambiguous cases:

```python
{
    "detected_areas": [
        {"area_name": "Expert Disbursements", "confidence": 0.85},
        {"area_name": "Billing", "confidence": 0.15}
    ],
    "recommendation": "Load test cases from Expert Disbursements"
}
```

### 4. **Multi-Area Support**
Automatically loads test cases from multiple areas when bugs span multiple modules:

```python
# Bug affecting both Billing and Disbursements
bug_desc = "Billing process fails to include disbursements in invoice"
# → Loads both billing.csv and expert_disbursements.csv
```

## New Files Created

```
app/src/backend/
├── agent/
│   ├── agent.py                 # Updated with MCP integration
│   └── area_config.py           # NEW: Area/CSV mappings & keywords
├── mcp/
│   ├── __init__.py              # NEW: MCP package init
│   └── test_case_server.py      # NEW: MCP server implementation
├── main.py                      # Updated: Optional CSV upload
├── test_agent.py                # Updated: Uses MCP by default
└── example_mcp_agent.py         # NEW: Example usage scripts
```

## Usage Examples

### Basic Usage (Auto-Detection)

```python
from agent.agent import TestCaseAgent

# Initialize with MCP enabled (default)
agent = TestCaseAgent(use_mcp=True)

# Analyze bug - test cases auto-loaded
results = agent.analyze_bug_report(
    bug_description="Cannot post disbursements with currency override",
    repro_steps="Enable override, create disb, post",
    code_changes="Fixed currency validation",
    auto_load=True  # Auto-detect and load relevant CSVs
)

# Results include only relevant test cases
print(f"Analyzed {results['summary']['total_test_cases_analyzed']} test cases")
```

### Manual Area Detection

```python
agent = TestCaseAgent(use_mcp=True)

# Detect area before loading
detection = agent.mcp_server.detect_relevant_areas(
    bug_description="Users cannot post disbursements",
    repro_steps="..."
)

print(f"Top area: {detection['top_area']}")
print(f"Confidence: {detection['detected_areas'][0]['confidence']}")

# Then load based on detection
load_result = agent.detect_and_load_test_cases(
    bug_description="...",
    repro_steps="..."
)
```

### Legacy Mode (Manual CSV)

```python
# Disable MCP for backward compatibility
agent = TestCaseAgent(use_mcp=False)

# Load CSV manually
agent.load_test_cases_from_csv("path/to/test_cases.csv")

# Analyze as before
results = agent.analyze_bug_report(..., auto_load=False)
```

### Using MCP Tools Directly

```python
agent = TestCaseAgent(use_mcp=True)
server = agent.mcp_server

# List all available areas
areas = server.list_areas()
print(f"Total areas: {areas['total_areas']}")
print(f"Total test cases: {areas['total_test_cases']}")

# Search by keywords
results = server.search_by_keywords(
    keywords=['post', 'currency'],
    areas=['Expert Disbursements'],
    limit=20
)

# Get statistics
stats = server.get_statistics()
print(f"Expert Disbursements: {stats['areas']['Expert Disbursements']['total']} tests")
```

## API Endpoints

### Updated `/analyze-bug` Endpoint

Now supports **two modes**:

#### 1. Auto-Detection Mode (Recommended)
```bash
curl -X POST "http://localhost:8000/analyze-bug" \
  -F "bug_description=Cannot post disbursements" \
  -F "repro_steps=..." \
  -F "code_changes=..."
# No CSV file needed!
```

#### 2. Manual Mode (Backward Compatible)
```bash
curl -X POST "http://localhost:8000/analyze-bug" \
  -F "csv_file=@test_cases.csv" \
  -F "bug_description=..." \
  -F "repro_steps=..." \
  -F "code_changes=..."
```

### New Endpoints

#### `GET /areas`
List all available test case areas:

```bash
curl "http://localhost:8000/areas"
```

Response:
```json
{
  "areas": [
    {
      "name": "Expert Disbursements",
      "description": "...",
      "test_case_count": 706,
      "keywords": ["disbursement", "disb", "posting", ...]
    },
    ...
  ],
  "total_areas": 5,
  "total_test_cases": 3383
}
```

#### `POST /detect-area`
Detect which area a bug belongs to:

```bash
curl -X POST "http://localhost:8000/detect-area" \
  -F "bug_description=Cannot post disbursements" \
  -F "repro_steps=..."
```

Response:
```json
{
  "detected_areas": [
    {
      "area_name": "Expert Disbursements",
      "confidence": 0.85,
      "matched_keywords": 12,
      "total_keywords": 15
    }
  ],
  "top_area": "Expert Disbursements",
  "recommendation": "Load test cases from Expert Disbursements"
}
```

## Configuration

### Area Configuration (`area_config.py`)

Customize area mappings, keywords, and descriptions:

```python
# Add new area
CSV_FILE_MAPPING["Time Entry"] = "test_cases_time_entry.csv"

AREA_KEYWORDS["Time Entry"] = [
    "time entry", "timekeeper", "hours", "billable"
]

AREA_DESCRIPTIONS["Time Entry"] = """
    Time Entry module handles time tracking...
"""
```

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=your_api_key
ANTHROPIC_MODEL=claude-haiku-4-5  # or claude-sonnet-3-5
```

## Testing

### Test the MCP Server
```bash
cd app/src/backend
python mcp/test_case_server.py
```

### Test the Agent
```bash
cd app/src/backend
python test_agent.py
```

### Run Example Scripts
```bash
cd app/src/backend
python example_mcp_agent.py
```

Select from interactive examples:
1. Auto Detection
2. Multi-Area Bug
3. Manual Detection
4. List Areas
5. Keyword Search
6. Statistics

## Performance

### Memory Usage
- **Without MCP**: Loads one CSV (~700 test cases) per analysis
- **With MCP**: Caches all CSVs at startup (~3,383 test cases total)
  - ~15-20 MB memory overhead
  - Faster subsequent analyses (no CSV re-reading)

### Analysis Speed
- **Area Detection**: ~50-100ms (keyword matching)
- **CSV Loading**: ~200-500ms (first load, then cached)
- **Full Analysis**: ~5-10 seconds (Claude API call dominates)

### Optimizations
- CSV data cached in memory after first load
- Embedding cache to avoid recomputation
- Keyword-based pre-filtering before Claude analysis

## Troubleshooting

### "No test cases loaded" Error
```python
# Solution: Enable auto_load
results = agent.analyze_bug_report(..., auto_load=True)
```

### Low Confidence Detection
When confidence is low (<0.3), the system may load all test cases:
```python
# Force loading specific area
load_result = agent.detect_and_load_test_cases(
    bug_description="...",
    force_all=False  # Set to True to load all areas
)
```

### MCP Not Available
```python
# Check if MCP is enabled
if agent.use_mcp and agent.mcp_server:
    print("MCP is available")
else:
    print("Using legacy mode")
```

### CSV Files Not Found
Ensure CSV files are in the project root:
```
rad-ai/
├── test_cases_expert_disbursements.csv
├── test_cases_billing.csv
├── test_cases_accounts_payable.csv
├── test_cases_collections.csv
└── test_cases_infrastructure.csv
```

## Migration Guide

### From Legacy to MCP

**Before (Legacy):**
```python
agent = TestCaseAgent()
agent.load_test_cases_from_csv("test_cases_expert_disbursements.csv")
results = agent.analyze_bug_report(...)
```

**After (MCP):**
```python
agent = TestCaseAgent(use_mcp=True)
results = agent.analyze_bug_report(..., auto_load=True)
# That's it! CSV selection is automatic
```

### API Migration

**Before:**
```javascript
// Required CSV file upload
const formData = new FormData();
formData.append('csv_file', csvFile);  // Required
formData.append('bug_description', description);
```

**After:**
```javascript
// CSV file is now optional
const formData = new FormData();
// formData.append('csv_file', csvFile);  // Optional!
formData.append('bug_description', description);
```

## Benefits

### 1. **Improved User Experience**
- No need to know which CSV to use
- Faster analysis (only relevant test cases loaded)
- Clearer results (focused on relevant area)

### 2. **Better Performance**
- Reduced analysis time (fewer test cases to process)
- Lower token costs (smaller context for Claude)
- Faster similarity search (smaller embedding space)

### 3. **Maintainability**
- Centralized area configuration
- Easy to add new areas/CSV files
- Backward compatible with legacy mode

### 4. **Scalability**
- Handles multi-area bugs gracefully
- Confidence-based fallback to all areas
- Extensible to TFS API integration

## Future Enhancements

### Planned Features
1. **Learning System**: Track which CSVs were actually relevant and improve detection
2. **TFS Integration**: Pull test cases directly from TFS API by area path
3. **User Feedback**: Allow users to override area detection
4. **Hierarchical Areas**: Support sub-areas (e.g., "Billing > Prebill > Markup")
5. **ML-Based Detection**: Train classifier on historical bug-to-area mappings

### Extension Points
```python
# Custom area detector
class CustomAreaDetector:
    def detect(self, bug_description, repro_steps):
        # Your custom logic
        return detected_areas

# Use custom detector
agent.mcp_server.custom_detector = CustomAreaDetector()
```

## Contributing

To add a new test case area:

1. Add CSV file to project root
2. Update `area_config.py`:
   ```python
   CSV_FILE_MAPPING["New Area"] = "test_cases_new_area.csv"
   AREA_KEYWORDS["New Area"] = ["keyword1", "keyword2", ...]
   AREA_DESCRIPTIONS["New Area"] = "Description..."
   ```
3. Test detection:
   ```python
   server = get_server()
   result = server.detect_relevant_areas("bug about new area")
   assert "New Area" in [a['area_name'] for a in result['detected_areas']]
   ```

## Support

For issues or questions:
- Check the examples in `example_mcp_agent.py`
- Review logs in terminal output
- Verify CSV files are present and readable
- Ensure ANTHROPIC_API_KEY is set in `.env`

---

**Last Updated**: December 4, 2025  
**Version**: 1.0.0
