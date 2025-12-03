"""
Test script to verify strict filtering improvements in the agent.
"""

import os
import sys
from pathlib import Path

# Set working directory and add to path
os.chdir(str(Path(__file__).parent / "app" / "src" / "backend"))
sys.path.insert(0, os.getcwd())

from agent.agent import TestCaseAgent

def test_strictness_levels():
    """Test different strictness levels."""
    print("\n" + "="*80)
    print("Testing Strict Filtering with Different Strictness Levels")
    print("="*80)
    
    # Initialize agent with MCP
    print("\n1. Initializing agent with sentence transformers...")
    agent = TestCaseAgent(use_mcp=True)
    
    # Example bug report
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = """
    1. Navigate to Expert Administration
    2. Enable 'Allow Currency Override' in Disbursement Options
    3. Create a new disbursement
    4. Attempt to post the disbursement
    5. Error occurs during posting
    """
    code_changes = "Fixed currency validation logic in posting process to properly handle currency overrides"
    
    # Test with different strictness levels
    for strictness in ['lenient', 'moderate', 'strict']:
        print(f"\n{'-'*80}")
        print(f"Testing with '{strictness.upper()}' strictness level")
        print(f"{'-'*80}")
        
        results = agent.analyze_bug_report(
            bug_description=bug_description,
            repro_steps=repro_steps,
            code_changes=code_changes,
            strictness=strictness,
            top_k=15,
            output_format='dict'
        )
        
        summary = results.get('summary', {})
        print(f"\nResults Summary:")
        print(f"  - Total test cases in database: {summary.get('total_test_cases_analyzed', 0)}")
        print(f"  - Similar tests found (above min threshold): {summary.get('similar_tests_found', 0)}")
        print(f"  - High confidence tests analyzed by Claude: {summary.get('high_confidence_tests_analyzed', 0)}")
        print(f"  - Potential duplicates found: {summary.get('potential_duplicates_found', 0)}")
        
        thresholds = summary.get('thresholds_used', {})
        print(f"\n  Thresholds Used:")
        print(f"    - Minimum similarity: {thresholds.get('min_similarity', 'N/A')}")
        print(f"    - Claude analysis: {thresholds.get('claude_analysis', 'N/A')}")
        print(f"    - CSV export: {thresholds.get('csv_export', 'N/A')}")
        
        # Show top 5 similar tests
        similar_tests = results.get('similar_tests', [])
        if similar_tests:
            print(f"\n  Top 5 Most Similar Test Cases:")
            for i, item in enumerate(similar_tests[:5], 1):
                tc = item['test_case']
                score = item['similarity_score']
                print(f"    {i}. [{tc['id']}] {tc['title'][:60]}... (Score: {score:.3f})")
        else:
            print(f"\n  No test cases met the similarity threshold!")

def test_area_boost():
    """Test area-based similarity boosting."""
    print("\n" + "="*80)
    print("Testing Area-Based Similarity Boosting")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    bug_description = "Disbursement posting fails with currency override"
    repro_steps = "Enable currency override, create disbursement, attempt to post"
    code_changes = "Fixed validation logic"
    
    # Test with area boosting enabled
    print("\n1. WITH area boosting enabled:")
    results_with_boost = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        strictness='moderate',
        apply_area_boost=True,
        top_k=10
    )
    
    print(f"   Found {len(results_with_boost.get('similar_tests', []))} similar test cases")
    if results_with_boost.get('similar_tests'):
        top_test = results_with_boost['similar_tests'][0]
        print(f"   Top match: [{top_test['test_case']['id']}] Score: {top_test['similarity_score']:.3f}")
    
    # Test with area boosting disabled
    print("\n2. WITHOUT area boosting:")
    results_without_boost = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        strictness='moderate',
        apply_area_boost=False,
        top_k=10
    )
    
    print(f"   Found {len(results_without_boost.get('similar_tests', []))} similar test cases")
    if results_without_boost.get('similar_tests'):
        top_test = results_without_boost['similar_tests'][0]
        print(f"   Top match: [{top_test['test_case']['id']}] Score: {top_test['similarity_score']:.3f}")

if __name__ == "__main__":
    print("\nStarting strict filtering tests...")
    print("This will test the improved embedding model and filtering mechanisms.\n")
    
    try:
        # Test 1: Different strictness levels
        test_strictness_levels()
        
        # Test 2: Area boosting
        test_area_boost()
        
        print("\n" + "="*80)
        print("✓ All tests completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
