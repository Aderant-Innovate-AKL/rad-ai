"""
MCP Server for Test Case Access

This module provides an MCP server that exposes test case data from CSV files
to AI agents through standardized tools. The server allows dynamic querying
and filtering of test cases based on various criteria.
"""

import csv
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agent.area_config import (
    CSV_FILE_PATHS,
    AREA_KEYWORDS,
    AREA_DESCRIPTIONS,
    AREA_PATH_PATTERNS,
    get_all_areas,
    get_csv_path
)


class TestCaseServer:
    """
    MCP Server for accessing test case data from CSV files.
    
    This server provides tools that can be called by AI agents to:
    - List available app families/areas
    - Search test cases by area
    - Search test cases by keywords
    - Get specific test cases by ID
    - Detect relevant areas based on bug descriptions
    """
    
    def __init__(self):
        """Initialize the test case server."""
        self.test_cases_cache = {}
        self._load_all_test_cases()
    
    def _load_all_test_cases(self):
        """Load all test cases from CSV files into memory cache."""
        for area_name, csv_path in CSV_FILE_PATHS.items():
            try:
                test_cases = self._load_csv(csv_path)
                self.test_cases_cache[area_name] = test_cases
                print(f"Loaded {len(test_cases)} test cases from {area_name}")
            except Exception as e:
                print(f"Error loading {area_name}: {e}")
                self.test_cases_cache[area_name] = []
    
    def _load_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from a CSV file.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    test_cases.append({
                        'id': row.get('ID', ''),
                        'title': row.get('Title', ''),
                        'state': row.get('State', ''),
                        'area': row.get('Area', ''),
                        'created_date': row.get('Created Date', ''),
                        'description': row.get('Description', ''),
                        'steps': row.get('Steps', '')
                    })
        except Exception as e:
            print(f"Error reading CSV {csv_path}: {e}")
        
        return test_cases
    
    def list_areas(self) -> Dict[str, Any]:
        """
        List all available app families/areas.
        
        Returns:
            Dictionary containing area information
        """
        areas = []
        for area_name in get_all_areas():
            test_count = len(self.test_cases_cache.get(area_name, []))
            areas.append({
                'name': area_name,
                'description': AREA_DESCRIPTIONS.get(area_name, '').strip(),
                'test_case_count': test_count,
                'keywords': AREA_KEYWORDS.get(area_name, [])[:10]  # First 10 keywords
            })
        
        return {
            'areas': areas,
            'total_areas': len(areas),
            'total_test_cases': sum(a['test_case_count'] for a in areas)
        }
    
    def search_by_area(
        self,
        area_names: List[str],
        limit: Optional[int] = None,
        state_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search test cases by area name(s).
        
        Args:
            area_names: List of area names to search
            limit: Maximum number of test cases to return per area
            state_filter: Filter by test case state (e.g., 'Ready', 'Design')
            
        Returns:
            Dictionary containing matching test cases
        """
        results = []
        
        for area_name in area_names:
            if area_name not in self.test_cases_cache:
                continue
            
            test_cases = self.test_cases_cache[area_name]
            
            # Apply state filter if provided
            if state_filter:
                test_cases = [tc for tc in test_cases if tc['state'] == state_filter]
            
            # Apply limit if provided
            if limit:
                test_cases = test_cases[:limit]
            
            results.extend([{**tc, 'source_area': area_name} for tc in test_cases])
        
        return {
            'test_cases': results,
            'count': len(results),
            'areas_searched': area_names
        }
    
    def search_by_keywords(
        self,
        keywords: List[str],
        areas: Optional[List[str]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search test cases by keywords in title, description, or steps.
        
        Args:
            keywords: List of keywords to search for
            areas: Optional list of areas to limit search to
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing matching test cases with relevance scores
        """
        areas_to_search = areas if areas else list(self.test_cases_cache.keys())
        results = []
        
        for area_name in areas_to_search:
            if area_name not in self.test_cases_cache:
                continue
            
            test_cases = self.test_cases_cache[area_name]
            
            for tc in test_cases:
                # Combine searchable text
                searchable_text = f"{tc['title']} {tc['description']} {tc['steps']}".lower()
                
                # Count keyword matches
                matches = sum(1 for keyword in keywords if keyword.lower() in searchable_text)
                
                if matches > 0:
                    relevance_score = matches / len(keywords)
                    results.append({
                        **tc,
                        'source_area': area_name,
                        'relevance_score': relevance_score,
                        'matched_keywords': matches
                    })
        
        # Sort by relevance score
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return {
            'test_cases': results[:limit],
            'count': len(results[:limit]),
            'total_matches': len(results),
            'keywords_searched': keywords
        }
    
    def get_by_id(self, test_case_id: str) -> Dict[str, Any]:
        """
        Get a specific test case by ID.
        
        Args:
            test_case_id: The test case ID to retrieve
            
        Returns:
            Dictionary containing the test case or error message
        """
        for area_name, test_cases in self.test_cases_cache.items():
            for tc in test_cases:
                if tc['id'] == test_case_id:
                    return {
                        'test_case': {**tc, 'source_area': area_name},
                        'found': True
                    }
        
        return {
            'test_case': None,
            'found': False,
            'error': f"Test case {test_case_id} not found"
        }
    
    def detect_relevant_areas(
        self,
        bug_description: str,
        repro_steps: str = ""
    ) -> Dict[str, Any]:
        """
        Detect which app family/area a bug belongs to based on keywords.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Reproduction steps
            
        Returns:
            Dictionary with detected areas and confidence scores
        """
        combined_text = f"{bug_description} {repro_steps}".lower()
        
        area_scores = {}
        
        for area_name, keywords in AREA_KEYWORDS.items():
            # Count how many keywords from this area appear in the text
            matches = sum(1 for keyword in keywords if keyword.lower() in combined_text)
            
            # Require at least 2 keyword matches to consider an area relevant
            if matches >= 2:
                # Use absolute match count with diminishing returns for confidence
                # This gives more weight to multiple strong matches
                confidence = min(1.0, (matches * 0.15) + (matches * matches * 0.02))
                area_scores[area_name] = {
                    'confidence': round(confidence, 3),
                    'matched_keywords': matches,
                    'total_keywords': len(keywords)
                }
        
        # Sort by confidence (and by match count as tiebreaker)
        sorted_areas = sorted(
            area_scores.items(),
            key=lambda x: (x[1]['confidence'], x[1]['matched_keywords']),
            reverse=True
        )
        
        return {
            'detected_areas': [
                {
                    'area_name': area,
                    **scores
                }
                for area, scores in sorted_areas
            ],
            'top_area': sorted_areas[0][0] if sorted_areas else None,
            'recommendation': self._get_area_recommendation(sorted_areas)
        }
    
    def _get_area_recommendation(self, sorted_areas: List) -> str:
        """
        Provide a recommendation based on detected areas.
        
        Args:
            sorted_areas: List of (area_name, scores) tuples sorted by confidence
            
        Returns:
            Recommendation string
        """
        if not sorted_areas:
            return "No clear area detected. Consider loading all test cases."
        
        top_area, top_scores = sorted_areas[0]
        
        # High confidence: 3+ keyword matches (confidence >= 0.50)
        if top_scores['confidence'] >= 0.50 and top_scores['matched_keywords'] >= 3:
            if len(sorted_areas) > 1:
                second_area, second_scores = sorted_areas[1]
                if second_scores['confidence'] >= 0.35:
                    return f"Load test cases from {top_area} and {second_area} (multi-area bug)"
            return f"Load test cases from {top_area} (high confidence: {top_scores['matched_keywords']} keyword matches)"
        # Moderate confidence: 2 keyword matches (confidence >= 0.30)
        elif top_scores['confidence'] >= 0.30:
            return f"Load test cases from {top_area} (moderate confidence: {top_scores['matched_keywords']} keyword matches)"
        else:
            return f"Low confidence ({top_scores['matched_keywords']} keyword matches). Consider loading all test cases."
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics about test cases.
        
        Returns:
            Dictionary containing statistics
        """
        stats = {
            'total_test_cases': 0,
            'areas': {}
        }
        
        for area_name, test_cases in self.test_cases_cache.items():
            states = {}
            for tc in test_cases:
                state = tc['state']
                states[state] = states.get(state, 0) + 1
            
            stats['areas'][area_name] = {
                'total': len(test_cases),
                'states': states
            }
            stats['total_test_cases'] += len(test_cases)
        
        return stats


# Create server instance for use by the agent
_server_instance = None


def get_server() -> TestCaseServer:
    """Get or create the test case server instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = TestCaseServer()
    return _server_instance


# Tool definitions for MCP protocol
MCP_TOOLS = [
    {
        "name": "list_areas",
        "description": "List all available app families/areas with their descriptions and test case counts",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_by_area",
        "description": "Search test cases by one or more area names",
        "inputSchema": {
            "type": "object",
            "properties": {
                "area_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of area names to search (e.g., ['Expert Disbursements', 'Billing'])"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of test cases to return per area (optional)"
                },
                "state_filter": {
                    "type": "string",
                    "description": "Filter by test case state (e.g., 'Ready', 'Design') (optional)"
                }
            },
            "required": ["area_names"]
        }
    },
    {
        "name": "search_by_keywords",
        "description": "Search test cases by keywords in title, description, or steps",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of keywords to search for"
                },
                "areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of areas to limit search to"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50)"
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "get_by_id",
        "description": "Get a specific test case by its ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "test_case_id": {
                    "type": "string",
                    "description": "The test case ID to retrieve"
                }
            },
            "required": ["test_case_id"]
        }
    },
    {
        "name": "detect_relevant_areas",
        "description": "Detect which app family/area a bug belongs to based on its description",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bug_description": {
                    "type": "string",
                    "description": "Description of the bug"
                },
                "repro_steps": {
                    "type": "string",
                    "description": "Reproduction steps for the bug (optional)"
                }
            },
            "required": ["bug_description"]
        }
    },
    {
        "name": "get_statistics",
        "description": "Get overall statistics about test cases across all areas",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]


def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a tool call from the MCP client.
    
    Args:
        tool_name: Name of the tool to call
        arguments: Arguments for the tool
        
    Returns:
        Result of the tool call
    """
    server = get_server()
    
    if tool_name == "list_areas":
        return server.list_areas()
    elif tool_name == "search_by_area":
        return server.search_by_area(**arguments)
    elif tool_name == "search_by_keywords":
        return server.search_by_keywords(**arguments)
    elif tool_name == "get_by_id":
        return server.get_by_id(**arguments)
    elif tool_name == "detect_relevant_areas":
        return server.detect_relevant_areas(**arguments)
    elif tool_name == "get_statistics":
        return server.get_statistics()
    else:
        return {"error": f"Unknown tool: {tool_name}"}


if __name__ == "__main__":
    # Test the server
    server = get_server()
    
    print("\n=== Test Case Server Initialized ===\n")
    
    # Test 1: List areas
    print("1. Listing all areas:")
    areas_result = server.list_areas()
    print(json.dumps(areas_result, indent=2))
    
    # Test 2: Detect area from bug description
    print("\n2. Detecting area for sample bug:")
    bug_desc = "Users cannot post disbursements when currency override is enabled"
    repro = "Navigate to Expert Administration, enable currency override, create disbursement, attempt to post"
    detection_result = server.detect_relevant_areas(bug_desc, repro)
    print(json.dumps(detection_result, indent=2))
    
    # Test 3: Search by detected area
    if detection_result['top_area']:
        print(f"\n3. Searching test cases in {detection_result['top_area']}:")
        search_result = server.search_by_area([detection_result['top_area']], limit=5)
        print(f"Found {search_result['count']} test cases (showing first 5)")
        for tc in search_result['test_cases'][:3]:
            print(f"  - [{tc['id']}] {tc['title']}")
    
    # Test 4: Keyword search
    print("\n4. Searching by keywords:")
    keyword_result = server.search_by_keywords(['post', 'currency', 'disbursement'], limit=10)
    print(f"Found {keyword_result['count']} matching test cases")
    for tc in keyword_result['test_cases'][:3]:
        print(f"  - [{tc['id']}] {tc['title']} (relevance: {tc['relevance_score']:.2f})")
    
    # Test 5: Statistics
    print("\n5. Overall statistics:")
    stats = server.get_statistics()
    print(json.dumps(stats, indent=2))
