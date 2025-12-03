"""
Quick test script for the Test Case Agent with MCP
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from agent.agent import TestCaseAgent

def main():
    print("="*80)
    print("Testing Test Case Agent with MCP Auto-Detection")
    print("="*80)
    
    # Initialize agent with MCP enabled
    print("\n1. Initializing agent with MCP...")
    try:
        agent = TestCaseAgent(use_mcp=True)
        print("   ✓ Agent initialized successfully with MCP enabled")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    # Example bug report
    print("\n2. Preparing sample bug report...")
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = """
    1. Navigate to Expert Administration
    2. Enable 'Allow Currency Override' in Disbursement Options
    3. Create a new disbursement with a non-default currency
    4. Attempt to post the disbursement
    5. Error occurs: 'Currency validation failed'
    """
    code_changes = "Fixed currency validation logic in posting process to properly handle currency overrides. Updated CDT_DISB validation to check ALLOW_CURR_OVR flag."
    
    print(f"   Bug: {bug_description}")
    
    # Detect relevant areas first (optional - just to show the detection)
    print("\n3. Detecting relevant test case areas...")
    if agent.mcp_server:
        detection = agent.mcp_server.detect_relevant_areas(bug_description, repro_steps)
        print(f"   ✓ Detection complete!")
        print(f"   Top area: {detection['top_area']}")
        print(f"   Recommendation: {detection['recommendation']}")
        for area_info in detection['detected_areas'][:3]:
            print(f"      - {area_info['area_name']}: {area_info['confidence']:.3f} confidence")
    
    # Analyze bug report (will auto-load relevant test cases)
    print("\n4. Analyzing bug report (auto-loading relevant test cases)...")
    try:
        results = agent.analyze_bug_report(
            bug_description=bug_description,
            repro_steps=repro_steps,
            code_changes=code_changes,
            top_k=10,
            auto_load=True  # Enable auto-detection and loading
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
            source_area = tc.get('source_area', 'N/A')
            print(f"   Source Area: {source_area}")
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
        print("\nℹ️  Note: Test cases were automatically detected and loaded based on bug description")
        print("   No manual CSV file specification was needed!")
        
    except Exception as e:
        print(f"   ✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


def test_legacy_mode():
    """Test legacy mode with manual CSV loading (for backward compatibility)"""
    print("\n\n" + "="*80)
    print("Testing Legacy Mode (Manual CSV Loading)")
    print("="*80)
    
    print("\n1. Initializing agent with MCP disabled...")
    try:
        agent = TestCaseAgent(use_mcp=False)
        print("   ✓ Agent initialized in legacy mode")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return
    
    print("\n2. Manually loading test cases from CSV...")
    csv_path = "../../../test_cases_expert_disbursements.csv"
    try:
        test_cases = agent.load_test_cases_from_csv(csv_path)
        print(f"   ✓ Loaded {len(test_cases)} test cases")
    except Exception as e:
        print(f"   ✗ Error loading CSV: {e}")
        return
    
    print("\n3. Running analysis in legacy mode...")
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = "Enable currency override, create disbursement, attempt to post"
    code_changes = "Fixed currency validation logic"
    
    try:
        results = agent.analyze_bug_report(
            bug_description=bug_description,
            repro_steps=repro_steps,
            code_changes=code_changes,
            top_k=5,
            auto_load=False  # Disable auto-load in legacy mode
        )
        print(f"   ✓ Found {results['summary']['similar_tests_found']} similar tests")
        print("\n" + "="*80)
        print("LEGACY MODE TEST COMPLETE!")
        print("="*80)
    except Exception as e:
        print(f"   ✗ Error during analysis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run main MCP test
    main()
    
    # Optionally test legacy mode
    print("\n\nWould you like to test legacy mode? (press Enter to skip)")
    try:
        import sys
        if sys.stdin.isatty():
            response = input("Test legacy mode? (y/N): ").strip().lower()
            if response == 'y':
                test_legacy_mode()
    except:
        pass  # Skip if running in non-interactive mode
