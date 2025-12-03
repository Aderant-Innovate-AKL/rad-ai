"""
Demonstration of strict filtering improvements with before/after comparison.

This script shows how the new strict filtering provides better results
compared to the old lenient approach.
"""

import os
import sys

# Ensure we're in the backend directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from agent.agent import TestCaseAgent

def demonstrate_strictness_comparison():
    """Compare different strictness levels on the same bug."""
    
    print("\n" + "="*80)
    print("DEMONSTRATION: Strict Filtering Improvements")
    print("="*80)
    
    # Initialize agent
    print("\nInitializing agent with sentence transformers...")
    agent = TestCaseAgent(use_mcp=True)
    print("✓ Agent ready\n")
    
    # Example bug report
    bug_description = "Disbursement posting fails when currency override is enabled"
    repro_steps = """
    1. Navigate to Expert Administration
    2. Enable 'Allow Currency Override' in Disbursement Options
    3. Create a new disbursement with non-default currency
    4. Fill in all required fields
    5. Attempt to post the disbursement
    6. System throws validation error
    """
    code_changes = "Fixed currency validation logic in posting process to properly handle currency overrides"
    
    print("Bug Report:")
    print(f"  Description: {bug_description}")
    print(f"  Area: Disbursements / Currency\n")
    
    # Compare three strictness levels
    levels = ['lenient', 'moderate', 'strict']
    results_by_level = {}
    
    for level in levels:
        print(f"\n{'-'*80}")
        print(f"Analyzing with '{level.upper()}' strictness...")
        print(f"{'-'*80}")
        
        results = agent.analyze_bug_report(
            bug_description=bug_description,
            repro_steps=repro_steps,
            code_changes=code_changes,
            strictness=level,
            top_k=15,
            apply_area_boost=True
        )
        
        results_by_level[level] = results
        summary = results['summary']
        
        print(f"\nResults:")
        print(f"  • Test cases in database: {summary['total_test_cases_analyzed']}")
        print(f"  • Similar tests found: {summary['similar_tests_found']}")
        print(f"  • High confidence (sent to Claude): {summary['high_confidence_tests_analyzed']}")
        
        # Show threshold configuration
        thresholds = summary['thresholds_used']
        print(f"\n  Thresholds:")
        print(f"    - Minimum similarity: {thresholds['min_similarity']:.2f}")
        print(f"    - Claude analysis: {thresholds['claude_analysis']:.2f}")
        print(f"    - CSV export: {thresholds['csv_export']:.2f}")
        
        # Show top matches
        similar_tests = results['similar_tests']
        if similar_tests:
            print(f"\n  Top 5 Matches:")
            for i, item in enumerate(similar_tests[:5], 1):
                tc = item['test_case']
                score = item['similarity_score']
                area = tc.get('area', 'N/A')
                title = tc['title'][:55] + '...' if len(tc['title']) > 55 else tc['title']
                print(f"    {i}. [{tc['id']}] {title}")
                print(f"       Score: {score:.3f} | Area: {area}")
        else:
            print(f"\n  ⚠ No test cases met the minimum threshold!")
    
    # Comparison summary
    print(f"\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    print(f"\n{'Level':<12} {'Total Found':<15} {'High Confidence':<18} {'Quality':<10}")
    print("-" * 65)
    
    for level in levels:
        summary = results_by_level[level]['summary']
        found = summary['similar_tests_found']
        high_conf = summary['high_confidence_tests_analyzed']
        
        if found > 0:
            top_score = results_by_level[level]['similar_tests'][0]['similarity_score']
            quality = f"{top_score:.3f}"
        else:
            quality = "N/A"
        
        print(f"{level.upper():<12} {found:<15} {high_conf:<18} {quality:<10}")
    
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)
    print("""
1. STRICT mode returns fewer but more relevant results
   → Best for critical bugs where precision is crucial
   → Minimum similarity: 0.80

2. MODERATE mode (default) provides balanced results
   → Good mix of precision and recall
   → Minimum similarity: 0.70
   → Recommended for most use cases

3. LENIENT mode casts a wider net
   → More results, including marginal matches
   → Minimum similarity: 0.55
   → Useful for exploratory analysis or when unsure

4. Area boosting helps prioritize domain-specific tests
   → Tests from matching areas get +0.15 boost
   → Cross-domain tests get -0.05 penalty
   → Reduces false positives significantly
""")
    
    print("="*80 + "\n")

def demonstrate_area_boost_impact():
    """Show the impact of area-based boosting."""
    
    print("\n" + "="*80)
    print("DEMONSTRATION: Area-Based Similarity Boosting")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    bug_description = "Disbursement currency validation error on post"
    repro_steps = "Create disbursement with currency override, attempt to post"
    code_changes = "Fixed validation"
    
    print("\nBug Report (Disbursements domain)")
    print(f"  Description: {bug_description}\n")
    
    # With area boosting
    print("1. WITH Area Boosting:")
    print("   (Disbursement tests get +boost, Billing tests get -penalty)")
    results_with = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        strictness='moderate',
        apply_area_boost=True,
        top_k=5
    )
    
    if results_with['similar_tests']:
        for i, item in enumerate(results_with['similar_tests'][:3], 1):
            tc = item['test_case']
            score = item['similarity_score']
            area = tc.get('area', 'N/A')
            print(f"   {i}. Score: {score:.3f} | Area: {area}")
    
    # Without area boosting
    print("\n2. WITHOUT Area Boosting:")
    print("   (Pure semantic similarity, no area preference)")
    results_without = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        strictness='moderate',
        apply_area_boost=False,
        top_k=5
    )
    
    if results_without['similar_tests']:
        for i, item in enumerate(results_without['similar_tests'][:3], 1):
            tc = item['test_case']
            score = item['similarity_score']
            area = tc.get('area', 'N/A')
            print(f"   {i}. Score: {score:.3f} | Area: {area}")
    
    print("\n✓ Area boosting prioritizes domain-relevant tests")
    print("="*80 + "\n")

if __name__ == "__main__":
    print("\n" + "🎯" * 40)
    print("  STRICT FILTERING DEMONSTRATION")
    print("  Testing the enhanced test case selection")
    print("🎯" * 40)
    
    try:
        # Demo 1: Compare strictness levels
        demonstrate_strictness_comparison()
        
        # Demo 2: Show area boost impact
        demonstrate_area_boost_impact()
        
        print("✓ All demonstrations completed successfully!\n")
        
    except Exception as e:
        print(f"\n✗ Error during demonstration: {str(e)}")
        import traceback
        traceback.print_exc()
