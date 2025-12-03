import unittest
import os
import requests
from dotenv import load_dotenv


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
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/7", timeout=30)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 7)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #7: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
    
    def test_fetch_pr_14(self):
        """Test fetching PR #14."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/14", timeout=30)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 14)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #14: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
    
    def test_fetch_pr_21(self):
        """Test fetching PR #21."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/21", timeout=30)
        self.assertEqual(response.status_code, 200, f"Expected 200, got {response.status_code}: {response.text}")
        
        data = response.json()
        self.assertEqual(data["pr_number"], 21)
        self.assertIn("title", data)
        self.assertIn("files_changed", data)
        self.assertIsInstance(data["files_changed"], list)
        
        # Print PR info for verification
        print(f"\nPR #21: {data['title']}")
        print(f"  State: {data['state']}")
        print(f"  Files changed: {data['total_files']}")
        for f in data["files_changed"]:
            print(f"    - {f['filename']} ({f['status']})")
    
    def test_fetch_pr_not_found(self):
        """Test fetching a non-existent PR returns 404."""
        response = requests.get(f"{self.BASE_URL}/fetch-pr-info/999999", timeout=30)
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
