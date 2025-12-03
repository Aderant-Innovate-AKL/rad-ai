"""
Example: Using the MCP-based Test Case Agent

This script demonstrates how to use the agent with automatic CSV file detection
based on bug descriptions. The agent uses the MCP server to intelligently select
which test case files to load.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent))

from agent.agent import TestCaseAgent


def example_1_auto_detection():
    """Example 1: Automatic test case detection (recommended approach)"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Automatic Test Case Detection")
    print("="*80)
    
    # Initialize agent with MCP enabled
    agent = TestCaseAgent(use_mcp=True)
    
    # Example bug report about disbursements
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = """
    1. Navigate to Expert Administration
    2. Enable 'Allow Currency Override' in Disbursement Options
    3. Create a new disbursement
    4. Attempt to post the disbursement
    5. Error occurs during posting
    """
    code_changes = "Fixed currency validation logic in posting process to properly handle currency overrides"
    
    print("\nBug Description:", bug_description)
    print("\nAnalyzing...")
    
    # Run analysis - agent will automatically detect it's a disbursement bug
    # and load only the Expert Disbursements test cases
    results = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        top_k=10
    )
    
    print("\n--- Results Summary ---")
    print(f"Total test cases analyzed: {results['summary']['total_test_cases_analyzed']}")
    print(f"Similar tests found: {results['summary']['similar_tests_found']}")
    print(f"Potential duplicates: {results['summary']['potential_duplicates_found']}")
    
    print("\n--- Top 5 Similar Test Cases ---")
    for i, item in enumerate(results['similar_tests'][:5], 1):
        tc = item['test_case']
        score = item['similarity_score']
        print(f"{i}. [{tc['id']}] {tc['title']}")
        print(f"   Similarity: {score:.3f} | State: {tc['state']}")


def example_2_multi_area_bug():
    """Example 2: Bug that spans multiple areas"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multi-Area Bug Detection")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    # Bug that involves both Billing and Disbursements
    bug_description = "Billing process fails to include disbursements in invoice generation"
    repro_steps = """
    1. Create and post several disbursements for a matter
    2. Navigate to Billing
    3. Generate a prebill for the matter
    4. Disbursements are missing from the invoice
    """
    code_changes = "Fixed integration between disbursement and billing modules"
    
    print("\nBug Description:", bug_description)
    print("\nAnalyzing...")
    
    results = agent.analyze_bug_report(
        bug_description=bug_description,
        repro_steps=repro_steps,
        code_changes=code_changes,
        top_k=15
    )
    
    print("\n--- Results Summary ---")
    print(f"Total test cases analyzed: {results['summary']['total_test_cases_analyzed']}")
    print(f"Similar tests found: {results['summary']['similar_tests_found']}")


def example_3_manual_area_detection():
    """Example 3: Manual area detection before analysis"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Manual Area Detection")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    bug_description = "Security permissions not properly enforced for collection activities"
    repro_steps = "User without collection permissions can access payor workspace"
    
    print("\nBug Description:", bug_description)
    
    # First, detect which areas are relevant
    if agent.mcp_server:
        detection = agent.mcp_server.detect_relevant_areas(bug_description, repro_steps)
        
        print("\n--- Area Detection Results ---")
        for area_info in detection['detected_areas']:
            print(f"Area: {area_info['area_name']}")
            print(f"  Confidence: {area_info['confidence']:.3f}")
            print(f"  Matched keywords: {area_info['matched_keywords']}/{area_info['total_keywords']}")
        
        print(f"\nRecommendation: {detection['recommendation']}")
        
        # Now load test cases based on detection
        load_result = agent.detect_and_load_test_cases(bug_description, repro_steps)
        print(f"\nLoaded {load_result['test_cases_count']} test cases from {len(load_result['areas_loaded'])} area(s)")
        print(f"Areas loaded: {', '.join(load_result['areas_loaded'])}")


def example_4_list_available_areas():
    """Example 4: List all available areas"""
    print("\n" + "="*80)
    print("EXAMPLE 4: List Available Areas")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    if agent.mcp_server:
        areas_info = agent.mcp_server.list_areas()
        
        print(f"\nTotal Areas: {areas_info['total_areas']}")
        print(f"Total Test Cases: {areas_info['total_test_cases']}")
        
        print("\n--- Available Areas ---")
        for area in areas_info['areas']:
            print(f"\n{area['name']} ({area['test_case_count']} test cases)")
            print(f"  Description: {area['description'][:100]}...")
            print(f"  Sample keywords: {', '.join(area['keywords'][:5])}")


def example_5_keyword_search():
    """Example 5: Search test cases by keywords"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Keyword Search")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    if agent.mcp_server:
        # Search for test cases related to currency and posting
        keywords = ['currency', 'post', 'override']
        print(f"\nSearching for keywords: {', '.join(keywords)}")
        
        results = agent.mcp_server.search_by_keywords(keywords, limit=10)
        
        print(f"\nFound {results['count']} matching test cases (showing top 10)")
        print(f"Total matches in database: {results['total_matches']}")
        
        print("\n--- Top Matches ---")
        for i, tc in enumerate(results['test_cases'][:5], 1):
            print(f"{i}. [{tc['id']}] {tc['title']}")
            print(f"   Relevance: {tc['relevance_score']:.3f} | Area: {tc['source_area']}")


def example_6_statistics():
    """Example 6: Get test case statistics"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Test Case Statistics")
    print("="*80)
    
    agent = TestCaseAgent(use_mcp=True)
    
    if agent.mcp_server:
        stats = agent.mcp_server.get_statistics()
        
        print(f"\nTotal Test Cases: {stats['total_test_cases']}")
        
        print("\n--- By Area ---")
        for area_name, area_stats in stats['areas'].items():
            print(f"\n{area_name}: {area_stats['total']} test cases")
            print("  States:", ', '.join(f"{state}: {count}" for state, count in area_stats['states'].items()))


def main():
    """Run all examples"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "MCP Test Case Agent - Examples" + " "*27 + "║")
    print("╚" + "="*78 + "╝")
    
    examples = [
        ("Auto Detection", example_1_auto_detection),
        ("Multi-Area Bug", example_2_multi_area_bug),
        ("Manual Detection", example_3_manual_area_detection),
        ("List Areas", example_4_list_available_areas),
        ("Keyword Search", example_5_keyword_search),
        ("Statistics", example_6_statistics)
    ]
    
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print("  0. Run all examples")
    
    try:
        choice = input("\nSelect example (0-6): ").strip()
        
        if choice == "0":
            for name, func in examples:
                try:
                    func()
                    input("\nPress Enter to continue to next example...")
                except Exception as e:
                    print(f"\nError in {name}: {e}")
                    import traceback
                    traceback.print_exc()
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            examples[int(choice) - 1][1]()
        else:
            print("Invalid choice. Running Example 1 by default.")
            example_1_auto_detection()
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
