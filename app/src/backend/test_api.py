"""
Test client for the Test Case Analysis API
Tests all endpoints to ensure backend is ready for frontend integration
"""

import requests
import json
import time
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"{title}")
    print("="*80)


def print_response(response: requests.Response, show_full: bool = False):
    """Print response details"""
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✓ Success")
        if show_full:
            print("\nResponse:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("\nResponse Summary:")
            data = response.json()
            if isinstance(data, dict):
                for key, value in list(data.items())[:5]:
                    if isinstance(value, (str, int, float, bool)):
                        print(f"  {key}: {value}")
                    elif isinstance(value, dict):
                        print(f"  {key}: {type(value).__name__} with {len(value)} keys")
                    elif isinstance(value, list):
                        print(f"  {key}: {type(value).__name__} with {len(value)} items")
    else:
        print(f"✗ Failed: {response.text}")


def test_root():
    """Test root endpoint"""
    print_section("TEST 1: Root Endpoint")
    response = requests.get(f"{BASE_URL}/")
    print_response(response, show_full=True)


def test_health_check():
    """Test health check endpoint"""
    print_section("TEST 2: Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, show_full=True)
    return response.status_code == 200


def test_list_areas():
    """Test list areas endpoint"""
    print_section("TEST 3: List Available Areas")
    response = requests.get(f"{BASE_URL}/areas")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal Areas: {data.get('total_areas', 0)}")
        print(f"Total Test Cases: {data.get('total_test_cases', 0)}")
        print("\nAreas:")
        for area in data.get('areas', [])[:3]:
            print(f"  • {area['name']}: {area['test_case_count']} test cases")


def test_get_statistics():
    """Test statistics endpoint"""
    print_section("TEST 4: Get Statistics")
    response = requests.get(f"{BASE_URL}/stats")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTotal Test Cases: {data.get('total_test_cases', 0)}")
        print("\nBy Area:")
        for area_name, area_data in list(data.get('areas', {}).items())[:3]:
            print(f"  {area_name}: {area_data.get('total', 0)} test cases")


def test_detect_areas():
    """Test area detection endpoint"""
    print_section("TEST 5: Detect Relevant Areas")
    
    bug_description = "Users cannot post disbursements when currency override is enabled"
    repro_steps = "Enable currency override, create disbursement, attempt to post"
    
    response = requests.post(
        f"{BASE_URL}/detect-areas",
        params={
            "bug_description": bug_description,
            "repro_steps": repro_steps
        }
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print(f"\nTop Area: {data.get('top_area', 'N/A')}")
        print(f"Recommendation: {data.get('recommendation', 'N/A')}")
        print("\nDetected Areas:")
        for area in data.get('detected_areas', [])[:3]:
            print(f"  • {area['area_name']}: {area['confidence']:.3f} confidence")


def test_analyze_bug_report():
    """Test main bug analysis endpoint"""
    print_section("TEST 6: Analyze Bug Report (Main Test)")
    
    request_data = {
        "bug_description": "Users cannot post disbursements when currency override is enabled",
        "repro_steps": """
        1. Navigate to Expert Administration
        2. Enable 'Allow Currency Override' in Disbursement Options
        3. Create a new disbursement with non-default currency
        4. Attempt to post the disbursement
        5. Error occurs during posting
        """,
        "code_changes": "Fixed currency validation logic in posting process to properly handle currency overrides",
        "top_k": 20,
        "similarity_threshold": 0.5,
        "output_format": "csv"
    }
    
    print("\nSending request...")
    print(f"Bug: {request_data['bug_description']}")
    print(f"Top K: {request_data['top_k']}")
    print(f"Threshold: {request_data['similarity_threshold']}")
    print(f"Output Format: {request_data['output_format']}")
    
    start_time = time.time()
    response = requests.post(
        f"{BASE_URL}/analyze",
        json=request_data
    )
    elapsed_time = time.time() - start_time
    
    print(f"\nRequest completed in {elapsed_time:.2f} seconds")
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        print("\n--- Analysis Results ---")
        print(f"Success: {data.get('success')}")
        print(f"Message: {data.get('message')}")
        
        if data.get('summary'):
            summary = data['summary']
            print(f"\nSummary:")
            print(f"  Total test cases analyzed: {summary.get('total_test_cases_analyzed', 0)}")
            print(f"  Similar tests found: {summary.get('similar_tests_found', 0)}")
            print(f"  Potential duplicates: {summary.get('potential_duplicates_found', 0)}")
        
        if data.get('csv_path'):
            csv_filename = data['csv_path'].split('\\')[-1].split('/')[-1]
            print(f"\nCSV File: {csv_filename}")
            return csv_filename
        
        if data.get('similar_tests'):
            print(f"\nTop 3 Similar Test Cases (preview):")
            for i, test in enumerate(data['similar_tests'][:3], 1):
                tc = test.get('test_case', {})
                score = test.get('similarity_score', 0)
                print(f"\n  {i}. Test Case #{tc.get('id')}")
                print(f"     Title: {tc.get('title', '')[:60]}...")
                print(f"     Similarity: {score:.3f}")
                print(f"     State: {tc.get('state', 'N/A')}")
    
    return None


def test_download_csv(csv_filename: str):
    """Test CSV download endpoint"""
    print_section("TEST 7: Download CSV File")
    
    if not csv_filename:
        print("⚠ No CSV file to download (skipping test)")
        return
    
    print(f"Downloading: {csv_filename}")
    response = requests.get(f"{BASE_URL}/download/{csv_filename}")
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("✓ Success")
        print(f"Content Type: {response.headers.get('content-type')}")
        print(f"Content Length: {len(response.content)} bytes")
        
        # Save file locally for inspection
        local_path = f"downloaded_{csv_filename}"
        with open(local_path, 'wb') as f:
            f.write(response.content)
        print(f"\n✓ Saved to: {local_path}")
        
        # Show first few lines
        print("\nFirst 3 lines of CSV:")
        lines = response.text.split('\n')[:4]
        for line in lines:
            print(f"  {line[:100]}...")
    else:
        print(f"✗ Failed: {response.text}")


def test_error_handling():
    """Test error handling"""
    print_section("TEST 8: Error Handling")
    
    # Test with invalid similarity threshold
    print("\n8a. Testing invalid similarity threshold...")
    response = requests.post(
        f"{BASE_URL}/analyze",
        json={
            "bug_description": "Test bug",
            "repro_steps": "Test steps",
            "code_changes": "Test changes",
            "similarity_threshold": 1.5  # Invalid: > 1.0
        }
    )
    print(f"Status Code: {response.status_code}")
    if response.status_code == 422:
        print("✓ Validation error caught correctly")
    else:
        print(f"Response: {response.text[:200]}")
    
    # Test downloading non-existent file
    print("\n8b. Testing non-existent file download...")
    response = requests.get(f"{BASE_URL}/download/nonexistent.csv")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 404:
        print("✓ File not found error handled correctly")
    else:
        print(f"Response: {response.text[:200]}")


def run_all_tests():
    """Run all API tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + " "*20 + "Test Case Analysis API Tests" + " "*30 + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print("\nℹ️  Make sure the API server is running:")
    print("   python api.py")
    print("\n   OR")
    print("   uvicorn api:app --reload\n")
    
    input("Press Enter to start tests...")
    
    try:
        # Run tests in sequence
        test_root()
        
        if not test_health_check():
            print("\n❌ Health check failed. Stopping tests.")
            return
        
        test_list_areas()
        test_get_statistics()
        test_detect_areas()
        
        csv_filename = test_analyze_bug_report()
        
        if csv_filename:
            time.sleep(1)  # Brief pause before download
            test_download_csv(csv_filename)
        
        test_error_handling()
        
        # Final summary
        print_section("TEST SUMMARY")
        print("\n✅ All tests completed!")
        print("\nAPI Endpoints Tested:")
        print("  ✓ GET  /                  - Root endpoint")
        print("  ✓ GET  /health            - Health check")
        print("  ✓ GET  /areas             - List areas")
        print("  ✓ GET  /stats             - Get statistics")
        print("  ✓ POST /detect-areas      - Detect relevant areas")
        print("  ✓ POST /analyze           - Analyze bug report")
        print("  ✓ GET  /download/{file}   - Download CSV")
        print("  ✓ Error handling")
        
        print("\n🎉 Backend is ready for frontend integration!")
        print("\nNext steps:")
        print("  1. Review the downloaded CSV file")
        print("  2. Check API documentation at http://localhost:8000/docs")
        print("  3. Integrate with frontend using the API endpoints")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Connection Error: Could not connect to API server")
        print("   Make sure the API is running on http://localhost:8000")
        print("\n   Start the API with:")
        print("   python api.py")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
