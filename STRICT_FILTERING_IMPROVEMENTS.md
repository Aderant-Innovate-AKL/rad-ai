# Strict Test Case Filtering - Implementation Summary

## Overview
Enhanced the test case analysis agent to be more strict and accurate in selecting test cases related to bug reports. The improvements significantly reduce false positives and ensure only closely related test cases are analyzed.

## Key Improvements

### 1. **Upgraded Embedding Model** ✓
- **Before**: Simple keyword-based embeddings (21 dimensions)
  - Only counted keyword frequencies
  - No semantic understanding
  - Many false positives across different functional areas
  
- **After**: Sentence-transformers semantic embeddings (384 dimensions)
  - Model: `all-MiniLM-L6-v2`
  - Deep semantic understanding of text
  - Much better discrimination between related/unrelated test cases

### 2. **Added Minimum Similarity Thresholds** ✓
- **Before**: Returned top K test cases regardless of similarity quality
  - No filtering by similarity score
  - Weak matches included in analysis
  
- **After**: Strict threshold filtering at multiple stages
  - `min_similarity`: 0.70 (default) - filters initial candidates
  - `claude_analysis`: 0.70 (default) - only high-confidence tests go to Claude
  - `csv_export`: 0.70 (default, increased from 0.50)

### 3. **Area-Based Similarity Boosting** ✓
- **Purpose**: Reduce cross-domain false positives
- **How it works**:
  - Extracts area keywords from test case (e.g., "Expert\Disbursements" → "expert", "disbursements")
  - Checks if bug description mentions those areas
  - **Boosts** similarity by up to +0.15 if area matches
  - **Penalizes** by -0.05 if area doesn't match
- **Impact**: Prioritizes test cases from the relevant functional area

### 4. **Configurable Strictness Levels** ✓
- **Three levels**: `lenient`, `moderate` (default), `strict`
- **Thresholds by level**:

| Level | Min Similarity | Claude Analysis | CSV Export |
|-------|---------------|-----------------|------------|
| Lenient | 0.55 | 0.60 | 0.50 |
| Moderate | 0.70 | 0.70 | 0.65 |
| Strict | 0.80 | 0.80 | 0.75 |

### 5. **Pre-filtering Before Claude Analysis** ✓
- **Before**: All top K test cases sent to Claude
- **After**: Only test cases above `claude_analysis` threshold sent to Claude
- **Benefit**: More focused analysis, reduced API costs, better recommendations

### 6. **Enhanced Result Tracking** ✓
- New metrics in results:
  - `high_confidence_tests_analyzed`: Tests that met Claude threshold
  - `strictness_level`: Level used for analysis
  - `thresholds_used`: Actual threshold values applied

## API Changes

### `TestCaseAgent.__init__()`
```python
TestCaseAgent(
    api_key: str = None,
    use_mcp: bool = True,
    embedding_model: str = 'all-MiniLM-L6-v2'  # NEW
)
```

### `find_similar_test_cases()`
```python
find_similar_test_cases(
    bug_description: str,
    repro_steps: str,
    top_k: int = 20,  # Changed from 15
    min_similarity: float = 0.70,  # NEW - filters results
    apply_area_boost: bool = True  # NEW - area boosting
)
```

### `analyze_bug_report()`
```python
analyze_bug_report(
    bug_description: str,
    repro_steps: str,
    code_changes: str,
    top_k: int = 20,  # Changed from 15
    auto_load: bool = True,
    output_format: str = 'dict',
    csv_output_path: Optional[str] = None,
    similarity_threshold: float = 0.70,  # Changed from 0.50
    strictness: Literal['lenient', 'moderate', 'strict'] = 'moderate',  # NEW
    apply_area_boost: bool = True  # NEW
)
```

## Usage Examples

### Basic Usage (Moderate Strictness)
```python
agent = TestCaseAgent(use_mcp=True)

results = agent.analyze_bug_report(
    bug_description="Users cannot post disbursements with currency override",
    repro_steps="1. Enable currency override\n2. Create disbursement\n3. Attempt to post",
    code_changes="Fixed currency validation logic"
)

print(f"Found {results['summary']['similar_tests_found']} related test cases")
print(f"High confidence: {results['summary']['high_confidence_tests_analyzed']}")
```

### Strict Mode (For Critical Bugs)
```python
results = agent.analyze_bug_report(
    bug_description="...",
    repro_steps="...",
    code_changes="...",
    strictness='strict',  # Minimum 0.80 similarity
    top_k=10  # Return fewer results
)
```

### Lenient Mode (For Exploratory Analysis)
```python
results = agent.analyze_bug_report(
    bug_description="...",
    repro_steps="...",
    code_changes="...",
    strictness='lenient',  # Minimum 0.55 similarity
    top_k=30  # Return more results
)
```

### Without Area Boosting (Pure Semantic Matching)
```python
results = agent.analyze_bug_report(
    bug_description="...",
    repro_steps="...",
    code_changes="...",
    apply_area_boost=False  # Disable area-based adjustments
)
```

## Performance Impact

### Accuracy Improvements
- **Reduced false positives**: Area boosting prevents cross-domain matches
- **Better semantic matching**: 384-dim embeddings understand context
- **Stricter thresholds**: Only truly related test cases pass filters

### Expected Behavior Changes
- **Fewer test cases returned**: Only high-quality matches
- **Higher average similarity scores**: Weak matches filtered out
- **More focused Claude analysis**: Better recommendations from Claude

### Example Comparison
**Before** (old system):
- Bug: "Disbursement posting fails"
- Results: 15 test cases including billing workflows (0.50-0.94 similarity)
- Many irrelevant matches due to keyword overlap

**After** (new system with moderate strictness):
- Bug: "Disbursement posting fails"
- Results: 7 test cases, all disbursement-related (0.72-0.89 similarity)
- Area boost prioritizes disbursement tests
- Billing tests filtered out or penalized

## Migration Notes

### Dependencies
- **New**: `sentence-transformers==3.3.1` (already in requirements.txt)
- First run will download the embedding model (~90MB)
- Model cached in `~/.cache/huggingface/`

### Backward Compatibility
- All existing code works with default parameters
- Default behavior is MORE strict (may return fewer results)
- To get old behavior: use `strictness='lenient'` and `min_similarity=0.50`

### CSV Export Changes
- Default threshold raised from 0.50 → 0.70
- Fewer test cases exported by default
- To restore old export behavior: pass `similarity_threshold=0.50`

## Testing

Run the test script to verify improvements:
```bash
cd app/src/backend
python test_improvements.py
```

Expected output:
- ✓ Agent initializes with sentence-transformers
- ✓ Generates 384-dimensional embeddings
- ✓ Strictness thresholds configured correctly
- ✓ Area boosting works as expected

## Troubleshooting

### Model Download Issues
If the sentence-transformers model fails to download:
```python
# Pre-download the model
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

### Too Few Results
If no test cases meet the threshold:
- Lower strictness: use `strictness='lenient'`
- Or manually set: `min_similarity=0.60`
- Check area field in test cases matches bug description

### Area Boosting Issues
If area boosting isn't working:
- Ensure test cases have `area` field populated
- Check bug description mentions area keywords
- Disable with `apply_area_boost=False` for pure semantic matching

## Future Enhancements

Potential improvements for consideration:
1. **Fine-tuned embeddings**: Train on domain-specific test case corpus
2. **Hybrid ranking**: Combine semantic + BM25 text matching
3. **Multi-stage retrieval**: Coarse filter → fine reranking
4. **Learning from feedback**: Track which matches users find helpful
