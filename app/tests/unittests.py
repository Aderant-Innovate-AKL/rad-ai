import unittest
import os
import sys
import requests
from dotenv import load_dotenv

# Add backend to path for importing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'backend'))


class TestTFSConfiguration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Load environment variables before running tests."""
        # Load from backend .env file
        env_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend', '.env')
        load_dotenv(env_path)
    
    def test_tfs_base_url_loaded(self):
        """Test that TFS_BASE_URL is loaded from .env file."""
        tfs_base_url = os.getenv("TFS_BASE_URL")
        self.assertIsNotNone(tfs_base_url, "TFS_BASE_URL should not be None")
        self.assertNotEqual(tfs_base_url, "", "TFS_BASE_URL should not be empty")
    
    def test_tfs_collection_loaded(self):
        """Test that TFS_COLLECTION is loaded from .env file."""
        tfs_collection = os.getenv("TFS_COLLECTION")
        self.assertIsNotNone(tfs_collection, "TFS_COLLECTION should not be None")
        self.assertNotEqual(tfs_collection, "", "TFS_COLLECTION should not be empty")
    
    def test_tfs_project_loaded(self):
        """Test that TFS_PROJECT is loaded from .env file."""
        tfs_project = os.getenv("TFS_PROJECT")
        self.assertIsNotNone(tfs_project, "TFS_PROJECT should not be None")
        self.assertNotEqual(tfs_project, "", "TFS_PROJECT should not be empty")
    
    def test_tfs_pat_loaded(self):
        """Test that TFS_PAT is loaded from .env file."""
        tfs_pat = os.getenv("TFS_PAT")
        self.assertIsNotNone(tfs_pat, "TFS_PAT should not be None")
        self.assertNotEqual(tfs_pat, "", "TFS_PAT should not be empty")


class TestGitHubConfiguration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Load environment variables before running tests."""
        env_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'backend', '.env')
        load_dotenv(env_path)
    
    def test_github_token_loaded(self):
        """Test that GITHUB_TOKEN is loaded from .env file."""
        github_token = os.getenv("GITHUB_TOKEN")
        self.assertIsNotNone(github_token, "GITHUB_TOKEN should not be None")
        self.assertNotEqual(github_token, "", "GITHUB_TOKEN should not be empty")
    
    def test_github_owner_loaded(self):
        """Test that GITHUB_OWNER is loaded from .env file."""
        github_owner = os.getenv("GITHUB_OWNER")
        self.assertIsNotNone(github_owner, "GITHUB_OWNER should not be None")
        self.assertNotEqual(github_owner, "", "GITHUB_OWNER should not be empty")
    
    def test_github_repo_loaded(self):
        """Test that GITHUB_REPO is loaded from .env file."""
        github_repo = os.getenv("GITHUB_REPO")
        self.assertIsNotNone(github_repo, "GITHUB_REPO should not be None")
        self.assertNotEqual(github_repo, "", "GITHUB_REPO should not be empty")


class TestFetchPRInfoEndpoint(unittest.TestCase):
    """Test the /fetch-pr-info endpoint with real PR numbers."""
    
    BASE_URL = "http://localhost:8000"
    
    @classmethod
    def setUpClass(cls):
        """Check if the backend server is running."""
        try:
            response = requests.get(f"{cls.BASE_URL}/health", timeout=5)
            cls.server_running = response.status_code == 200
        except requests.exceptions.ConnectionError:
            cls.server_running = False
    
    def setUp(self):
        """Skip tests if server is not running."""
        if not self.server_running:
            self.skipTest("Backend server is not running at localhost:8000")
    
    def test_fetch_pr_7(self):
        """Test fetching PR #7."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/7", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 7)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIn("summary", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #7: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_fetch_pr_14(self):
        """Test fetching PR #14."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/14", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 14)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIn("summary", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #14: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_fetch_pr_21(self):
        """Test fetching PR #21."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/21", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 21)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIn("summary", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #21: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_fetch_pr_not_found(self):
        """Test fetching a non-existent PR returns 404."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/999999", timeout=30)
        self.assertEqual(response.status_code, 404)


class TestBugIdExtraction(unittest.TestCase):
    """Test bug ID extraction from PR descriptions."""
    
    @classmethod
    def setUpClass(cls):
        """Import the extract_bug_id_from_text function from api module."""
        try:
            from api import extract_bug_id_from_text
            # Store as module-level to avoid method binding issues
            global _extract_bug_id_func
            _extract_bug_id_func = extract_bug_id_from_text
            cls.import_success = True
        except ImportError as e:
            cls.import_success = False
            cls.import_error = str(e)
    
    def setUp(self):
        """Skip tests if import failed."""
        if not self.import_success:
            self.skipTest(f"Could not import api module: {self.import_error}")
    
    def test_extract_bug_id_simple(self):
        """Test extracting a simple bug ID like #12345."""
        result = _extract_bug_id_func("#12345")
        self.assertEqual(result, "12345")
    
    def test_extract_bug_id_in_sentence(self):
        """Test extracting bug ID from a sentence."""
        result = _extract_bug_id_func("Fixes bug #98765 in the payment module")
        self.assertEqual(result, "98765")
    
    def test_extract_bug_id_multiple(self):
        """Test that only the first bug ID is returned when multiple exist."""
        result = _extract_bug_id_func("Fixes #11111 and #22222")
        self.assertEqual(result, "11111")
    
    def test_extract_bug_id_at_end(self):
        """Test extracting bug ID at the end of text."""
        result = _extract_bug_id_func("This PR addresses issue #54321")
        self.assertEqual(result, "54321")
    
    def test_extract_bug_id_multiline(self):
        """Test extracting bug ID from multiline text."""
        text = """
        ## Description
        This PR fixes a critical bug.
        
        Related to #67890
        """
        result = _extract_bug_id_func(text)
        self.assertEqual(result, "67890")
    
    def test_extract_bug_id_none_when_empty(self):
        """Test that None is returned for empty string."""
        result = _extract_bug_id_func("")
        self.assertIsNone(result)
    
    def test_extract_bug_id_none_when_none_input(self):
        """Test that None is returned for None input."""
        result = _extract_bug_id_func(None)
        self.assertIsNone(result)
    
    def test_extract_bug_id_none_when_no_match(self):
        """Test that None is returned when no bug ID is found."""
        result = _extract_bug_id_func("This is just a regular description without any bug reference")
        self.assertIsNone(result)
    
    def test_extract_bug_id_ignores_short_numbers(self):
        """Test that short numbers (less than 3 digits) are ignored."""
        result = _extract_bug_id_func("PR #1 is ready")
        self.assertIsNone(result)
    
    def test_extract_bug_id_ignores_two_digit(self):
        """Test that two-digit numbers are ignored (likely PR numbers)."""
        result = _extract_bug_id_func("PR #42 is the answer")
        self.assertIsNone(result)
    
    def test_extract_bug_id_three_digits(self):
        """Test that three-digit numbers are extracted."""
        result = _extract_bug_id_func("Bug #123 needs fixing")
        self.assertEqual(result, "123")


class TestPRInfoBugIdExtraction(unittest.TestCase):
    """Test that /fetch-pr-info endpoint returns bug_id and bug_info fields."""
    
    BASE_URL = "http://localhost:8000"
    
    @classmethod
    def setUpClass(cls):
        """Check if the backend server is running."""
        try:
            response = requests.get(f"{cls.BASE_URL}/health", timeout=5)
            cls.server_running = response.status_code == 200
        except requests.exceptions.ConnectionError:
            cls.server_running = False
    
    def setUp(self):
        """Skip tests if server is not running."""
        if not self.server_running:
            self.skipTest("Backend server is not running at localhost:8000")
    
    def test_pr_response_has_bug_id_field(self):
        """Test that PR response includes bug_id field."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/7", timeout=60)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # bug_id should be present (can be None or a string)
        self.assertIn("bug_id", data)
        
        if data["bug_id"]:
            print(f"\nPR #7 has bug_id: {data['bug_id']}")
        else:
            print(f"\nPR #7 has no bug_id in description")
    
    def test_pr_response_has_bug_info_field(self):
        """Test that PR response includes bug_info field."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/7", timeout=60)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        # bug_info should be present (can be None or an object)
        self.assertIn("bug_info", data)
        
        if data["bug_info"]:
            print(f"\nPR #7 has bug_info:")
            print(f"  Bug ID: {data['bug_info']['bug_id']}")
            print(f"  Title: {data['bug_info']['title']}")
        else:
            print(f"\nPR #7 has no bug_info (bug_id not found or TFS fetch failed)")
    
    def test_bug_info_structure_when_present(self):
        """Test that bug_info has correct structure when present."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/14", timeout=60)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        
        if data["bug_info"]:
            bug_info = data["bug_info"]
            self.assertIn("bug_id", bug_info)
            self.assertIn("title", bug_info)
            self.assertIn("description", bug_info)
            self.assertIn("repro_steps", bug_info)
            print(f"\nPR #14 bug_info structure is valid")
            print(f"  Bug ID: {bug_info['bug_id']}")
            print(f"  Title: {bug_info['title'][:50]}..." if len(bug_info['title']) > 50 else f"  Title: {bug_info['title']}")


class TestSummarizePREndpoint(unittest.TestCase):
    """Test the /summarize-pr endpoint with real PR numbers."""
    
    BASE_URL = "http://localhost:8000"
    
    @classmethod
    def setUpClass(cls):
        """Check if the backend server is running."""
        try:
            response = requests.get(f"{cls.BASE_URL}/health", timeout=5)
            cls.server_running = response.status_code == 200
        except requests.exceptions.ConnectionError:
            cls.server_running = False
    
    def setUp(self):
        """Skip tests if server is not running."""
        if not self.server_running:
            self.skipTest("Backend server is not running at localhost:8000")
    
    def test_summarize_pr_7(self):
        """Test summarizing PR #7."""
        response = requests.get(f"{self.BASE_URL}/summarize-pr/7", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 7)
        self.assertIn("title", data)
        self.assertIn("summary", data)
        self.assertIn("files_changed", data)
        self.assertIn("total_files", data)
        self.assertIsInstance(data["files_changed"], list)
        self.assertIsInstance(data["summary"], str)
        self.assertGreater(len(data["summary"]), 0, "Summary should not be empty")
        
        # Print summary for verification
        print(f"\nPR #7 Summary:")
        print(f"  Title: {data['title']}")
        print(f"  Total files: {data['total_files']}")
        print(f"  Files: {', '.join(data['files_changed'][:5])}{'...' if len(data['files_changed']) > 5 else ''}")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_summarize_pr_14(self):
        """Test summarizing PR #14."""
        response = requests.get(f"{self.BASE_URL}/summarize-pr/14", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 14)
        self.assertIn("title", data)
        self.assertIn("summary", data)
        self.assertIn("files_changed", data)
        self.assertIn("total_files", data)
        self.assertIsInstance(data["files_changed"], list)
        self.assertIsInstance(data["summary"], str)
        self.assertGreater(len(data["summary"]), 0, "Summary should not be empty")
        
        # Print summary for verification
        print(f"\nPR #14 Summary:")
        print(f"  Title: {data['title']}")
        print(f"  Total files: {data['total_files']}")
        print(f"  Files: {', '.join(data['files_changed'][:5])}{'...' if len(data['files_changed']) > 5 else ''}")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_summarize_pr_21(self):
        """Test summarizing PR #21."""
        response = requests.get(f"{self.BASE_URL}/summarize-pr/21", timeout=60)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 21)
        self.assertIn("title", data)
        self.assertIn("summary", data)
        self.assertIn("files_changed", data)
        self.assertIn("total_files", data)
        self.assertIsInstance(data["files_changed"], list)
        self.assertIsInstance(data["summary"], str)
        self.assertGreater(len(data["summary"]), 0, "Summary should not be empty")
        
        # Print summary for verification
        print(f"\nPR #21 Summary:")
        print(f"  Title: {data['title']}")
        print(f"  Total files: {data['total_files']}")
        print(f"  Files: {', '.join(data['files_changed'][:5])}{'...' if len(data['files_changed']) > 5 else ''}")
        print(f"\n  AI Summary:\n{data['summary']}")
    
    def test_summarize_pr_not_found(self):
        """Test summarizing a non-existent PR returns 404."""
        response = requests.get(f"{self.BASE_URL}/summarize-pr/999999", timeout=30)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
