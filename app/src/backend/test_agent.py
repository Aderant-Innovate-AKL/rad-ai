"""
Quick test script for the Test Case Agent
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.agent import TestCaseAgent

def main():
    print("="*80)
    print("Testing Test Case Agent")
    print("="*80)
    
    # Initialize agent
    print("\n1. Initializing agent...")
    try:
        agent = TestCaseAgent()
        print("   ✓ Agent initialized successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Load test cases
    print("\n2. Loading test cases...")
    csv_path = "../../../test_cases_with_descriptions_expert_disbursements.csv"
    try:
        test_cases = agent.load_test_cases_from_csv(csv_path)
        print(f"   ✓ Loaded {len(test_cases)} test cases")
    except Exception as e:
        print(f"   ✗ Error loading CSV: {e}")
        return
    
    # Example bug report
    print("\n3. Analyzing sample bug report...")
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = """
    1. Navigate to Expert Administration
    2. Enable 'Allow Currency Override' in Disbursement Options
    3. Create a new disbursement with a non-default currency
    4. Attempt to post the disbursement
    5. Error occurs: 'Currency validation failed'
    """
    code_changes = "Fixed currency validation logic in posting process to properly handle currency overrides. Updated CDT_DISB validation to check ALLOW_CURR_OVR flag."
    
    try:
        results = agent.analyze_bug_report(
            bug_description=bug_description,
            repro_steps=repro_steps,
            code_changes=code_changes,
            top_k=10
        )
        print("   ✓ Analysis complete!")
        
        # Print summary
        print("\n" + "="*80)
        print("RESULTS SUMMARY")
        print("="*80)
        print(f"Total test cases analyzed: {results['summary']['total_test_cases_analyzed']}")
        print(f"Similar tests found: {results['summary']['similar_tests_found']}")
        print(f"Potential duplicates: {results['summary']['potential_duplicates_found']}")
        
        # Print top similar tests
        print("\n" + "-"*80)
        print("TOP SIMILAR TEST CASES:")
        print("-"*80)
        for i, item in enumerate(results['similar_tests'][:5], 1):
            tc = item['test_case']
            score = item['similarity_score']
            print(f"\n{i}. Test Case #{tc['id']} (Score: {score:.3f})")
            print(f"   Title: {tc['title']}")
            print(f"   State: {tc['state']}")
            if tc['description']:
                desc_preview = tc['description'][:100] + "..." if len(tc['description']) > 100 else tc['description']
                print(f"   Description: {desc_preview}")
        
        # Print Claude's analysis if available
        if 'claude_analysis' in results:
            claude = results['claude_analysis']
            
            if 'related_tests' in claude and claude['related_tests']:
                print("\n" + "-"*80)
                print("CLAUDE'S RELATED TESTS ANALYSIS:")
                print("-"*80)
                for rt in claude['related_tests'][:3]:
                    if isinstance(rt, dict):
                        print(f"\n- Test: {rt.get('test_id', 'N/A')}")
                        print(f"  Reason: {rt.get('reasoning', 'N/A')}")
                        print(f"  Confidence: {rt.get('confidence', 'N/A')}")
            
            if 'suggested_updates' in claude and claude['suggested_updates']:
                print("\n" + "-"*80)
                print("SUGGESTED TEST UPDATES:")
                print("-"*80)
                for su in claude['suggested_updates'][:3]:
                    if isinstance(su, dict):
                        print(f"\n- Test: {su.get('test_id', 'N/A')}")
                        print(f"  Update: {su.get('suggested_change', 'N/A')}")
            
            if 'raw_response' in claude:
                print("\n" + "-"*80)
                print("CLAUDE'S FULL ANALYSIS:")
                print("-"*80)
                print(claude['raw_response'][:500] + "..." if len(claude['raw_response']) > 500 else claude['raw_response'])
        
        print("\n" + "="*80)
        print("TEST COMPLETE!")
        print("="*80)
        
    except Exception as e:
        print(f"   ✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
