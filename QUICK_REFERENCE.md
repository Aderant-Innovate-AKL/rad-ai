# Strict Test Case Selection - Quick Reference

## What Changed?

The test case analysis agent is now **much more strict** in selecting test cases related to bug reports, significantly reducing false positives and ensuring only closely related test cases are analyzed.

## Key Improvements

### 1. **Better Semantic Understanding**
- Upgraded from 21-dimensional keyword embeddings → **384-dimensional semantic embeddings**
- Uses sentence-transformers model for deep understanding
- Understands context, not just keyword matches

### 2. **Stricter Filtering**
- Default minimum similarity: **0.70** (was: no minimum, returned all top 15)
- Only high-confidence matches (≥0.70) sent to Claude for analysis
- CSV export threshold: **0.70** (was: 0.50)

### 3. **Area-Based Boosting**
- Boosts similarity score (+0.15 max) when test area matches bug description
- Penalizes (-0.05) when areas don't match
- Reduces cross-domain false positives (e.g., billing tests for disbursement bugs)

### 4. **Configurable Strictness**
Three levels to choose from:
- **Lenient**: 0.55 minimum (exploratory analysis)
- **Moderate**: 0.70 minimum (default, balanced)
- **Strict**: 0.80 minimum (critical bugs only)

## Quick Start

### Default Usage (Recommended)
```python
from agent.agent import TestCaseAgent

agent = TestCaseAgent(use_mcp=True)

results = agent.analyze_bug_report(
    bug_description="Users cannot post disbursements with currency override",
    repro_steps="1. Enable currency override\n2. Create disbursement\n3. Attempt to post",
    code_changes="Fixed currency validation logic"
)

# Results will contain only closely related test cases
print(f"Found {results['summary']['similar_tests_found']} related test cases")
```

### Use Strict Mode for Critical Bugs
```python
results = agent.analyze_bug_report(
    bug_description="...",
    repro_steps="...",
    code_changes="...",
    strictness='strict'  # Only matches with ≥0.80 similarity
)
```

### Use Lenient Mode for Broad Search
```python
results = agent.analyze_bug_report(
    bug_description="...",
    repro_steps="...",
    code_changes="...",
    strictness='lenient'  # Matches with ≥0.55 similarity
)
```

## Expected Behavior Changes

| Aspect | Before | After |
|--------|--------|-------|
| **Test cases returned** | 15 regardless of quality | 5-10 high-quality matches |
| **Similarity scores** | 0.50-0.95 (many false positives) | 0.70-0.95 (genuine matches) |
| **Cross-area matches** | Common (billing for disbursement bugs) | Rare (area boosting filters them) |
| **CSV exports** | Includes 0.50+ matches | Includes 0.70+ matches |
| **Claude analysis** | All top 15 | Only 0.70+ matches |

## Troubleshooting

### "No test cases found above threshold"
**Cause**: Bug description doesn't match any test cases well enough
**Solutions**:
1. Use lenient mode: `strictness='lenient'`
2. Lower threshold: `min_similarity=0.60`
3. Improve bug description to include more technical details

### "Area boosting not working"
**Cause**: Test cases missing `area` field or bug description doesn't mention area
**Solutions**:
1. Ensure test cases have `area` field populated
2. Include area keywords in bug description (e.g., "disbursement", "billing")
3. Disable area boosting: `apply_area_boost=False`

### "Embedding model download fails"
**Cause**: Network issues or cache problems
**Solution**: Pre-download the model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

## Testing

Verify the improvements work:
```bash
cd app/src/backend
python test_improvements.py
```

Should show:
- ✓ 384-dimensional embeddings
- ✓ Strictness levels configured
- ✓ Area boosting functional

## API Reference

### Strictness Thresholds

| Level | Minimum | Claude | CSV |
|-------|---------|--------|-----|
| Lenient | 0.55 | 0.60 | 0.50 |
| Moderate | 0.70 | 0.70 | 0.65 |
| Strict | 0.80 | 0.80 | 0.75 |

### New Parameters

**`TestCaseAgent.__init__()`**
- `embedding_model`: str = 'all-MiniLM-L6-v2' - Sentence transformer model

**`analyze_bug_report()`**
- `strictness`: 'lenient' | 'moderate' | 'strict' = 'moderate'
- `apply_area_boost`: bool = True - Enable area-based boosting
- `similarity_threshold`: float = 0.70 - CSV export threshold (increased from 0.50)
- `top_k`: int = 20 - Max results (increased from 15)

**`find_similar_test_cases()`**
- `min_similarity`: float = 0.70 - Minimum similarity to include
- `apply_area_boost`: bool = True - Enable area-based boosting
- `top_k`: int = 20 - Max results (increased from 15)

## Summary

The agent is now **significantly more accurate** in identifying related test cases:
- ✓ Better semantic understanding (384-dim embeddings)
- ✓ Stricter filtering (0.70 minimum by default)
- ✓ Area-aware matching (reduces false positives)
- ✓ Configurable strictness levels
- ✓ Pre-filtering before Claude analysis

**Result**: Fewer but higher-quality test case matches, with less noise and better relevance to the bug being analyzed.
