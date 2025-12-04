"""
Test Case Analysis Agent

This module provides an AI agent that analyzes bug reports and identifies related test cases,
suggests updates, and detects duplicates using Anthropic Claude and semantic embeddings.
"""

import os
import csv
import json
from typing import List, Dict, Any, Tuple, Optional, Literal
from pathlib import Path
import anthropic
import numpy as np
from dotenv import load_dotenv
import sys
from sentence_transformers import SentenceTransformer

# Add MCP server to path
sys.path.append(str(Path(__file__).parent.parent))

from mcp.test_case_server import get_server, handle_tool_call

# Load environment variables
load_dotenv()


class TestCaseAgent:
    """
    AI Agent for analyzing test cases against bug reports.
    
    Uses Anthropic Claude for natural language understanding and reasoning,
    and sentence transformers for semantic similarity matching.
    """
    
    def __init__(self, api_key: str = None, use_mcp: bool = True, embedding_model: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the agent with necessary models and configurations.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            use_mcp: Whether to use MCP server for test case access (default: True)
            embedding_model: Name of sentence-transformers model to use (default: 'all-MiniLM-L6-v2')
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        
        # MCP integration
        self.use_mcp = use_mcp
        self.mcp_server = get_server() if use_mcp else None
        
        # Initialize sentence transformer for better embeddings
        print(f"Loading embedding model: {embedding_model}...")
        self.embedding_model = SentenceTransformer(embedding_model)
        
        # Cache for embeddings
        self.embeddings_cache = {}
        self.test_cases = []
        
        print(f"Agent initialized successfully (MCP: {'enabled' if use_mcp else 'disabled'})")
        
    def load_test_cases_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from a CSV file.
        
        NOTE: This method is kept for backward compatibility.
        When MCP is enabled, use detect_and_load_test_cases() instead.
        
        Args:
            csv_path: Path to the CSV file containing test cases
            
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
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
        
        self.test_cases = test_cases
        print(f"Loaded {len(test_cases)} test cases")
        return test_cases
    
    def detect_and_load_test_cases(
        self,
        bug_description: str,
        repro_steps: str = "",
        force_all: bool = False
    ) -> Dict[str, Any]:
        """
        Detect relevant areas and load test cases automatically using MCP server.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Reproduction steps for the bug
            force_all: If True, load all test cases regardless of detection
            
        Returns:
            Dictionary with detection results and loaded test cases
        """
        if not self.use_mcp or not self.mcp_server:
            raise RuntimeError("MCP is not enabled. Use load_test_cases_from_csv() instead.")
        
        # Detect relevant areas
        detection_result = self.mcp_server.detect_relevant_areas(bug_description, repro_steps)
        
        # Determine which areas to load
        if force_all or not detection_result['detected_areas']:
            # Load all test cases
            print("Loading all test cases...")
            from agent.area_config import get_all_areas
            areas_to_load = get_all_areas()
        else:
            # Load from top detected areas (require reasonable confidence)
            detected = detection_result['detected_areas']
            
            # Only use top area if it has at least moderate confidence (2+ keyword matches)
            if detected[0]['confidence'] >= 0.30 and detected[0]['matched_keywords'] >= 2:
                areas_to_load = [detected[0]['area_name']]
                
                # Add second area if it also has good confidence
                if len(detected) > 1 and detected[1]['confidence'] >= 0.35 and detected[1]['matched_keywords'] >= 3:
                    areas_to_load.append(detected[1]['area_name'])
            else:
                # Confidence too low, load all areas
                print(f"Low confidence detection (confidence: {detected[0]['confidence']:.3f}, matches: {detected[0]['matched_keywords']}), loading all test cases...")
                from agent.area_config import get_all_areas
                areas_to_load = get_all_areas()
        
        print(f"Loading test cases from: {', '.join(areas_to_load)}")
        
        # Load test cases from selected areas
        search_result = self.mcp_server.search_by_area(areas_to_load)
        self.test_cases = search_result['test_cases']
        
        return {
            'detection': detection_result,
            'areas_loaded': areas_to_load,
            'test_cases_count': len(self.test_cases),
            'recommendation': detection_result['recommendation']
        }
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a text string with caching using sentence transformers.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array (384-dimensional semantic embedding)
        """
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # Use sentence transformer for semantic embeddings
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        
        self.embeddings_cache[text] = embedding
        return embedding
    
    def _calculate_area_similarity_boost(self, test_case: Dict[str, Any], bug_text: str) -> float:
        """
        Calculate a boost/penalty based on area alignment between test case and bug.
        
        Args:
            test_case: Test case dictionary with 'area' field
            bug_text: Combined bug description and repro steps
            
        Returns:
            Boost value to add to similarity score (can be positive or negative)
        """
        test_area = test_case.get('area', '').lower()
        bug_text_lower = bug_text.lower()
        
        if not test_area:
            return 0.0
        
        # Extract area keywords (e.g., "Expert\Disbursements" -> ["expert", "disbursements"])
        area_keywords = [kw.strip() for kw in test_area.replace('\\', ' ').replace('/', ' ').split()]
        
        # Check if bug text mentions any area keywords
        matches = sum(1 for kw in area_keywords if kw and kw in bug_text_lower)
        
        if matches > 0:
            # Boost if area is mentioned in bug description
            return min(0.15, matches * 0.08)  # Cap at +0.15 boost
        else:
            # Small penalty if area not mentioned (might be cross-domain false positive)
            return -0.05
    
    def _get_strictness_thresholds(self, strictness: str) -> Dict[str, float]:
        """
        Get similarity thresholds based on strictness level.
        
        Args:
            strictness: 'lenient', 'moderate', or 'strict'
            
        Returns:
            Dictionary with threshold values
        """
        thresholds = {
            'lenient': {
                'min_similarity': 0.35,
                'csv_export': 0.40,
                'claude_analysis': 0.45
            },
            'moderate': {
                'min_similarity': 0.50,
                'csv_export': 0.50,
                'claude_analysis': 0.55
            },
            'strict': {
                'min_similarity': 0.65,
                'csv_export': 0.60,
                'claude_analysis': 0.70
            }
        }
        
        return thresholds.get(strictness, thresholds['lenient'])
    
    def compute_test_case_embeddings(self) -> Dict[str, np.ndarray]:
        """
        Compute embeddings for all test cases.
        
        Returns:
            Dictionary mapping test case IDs to their embeddings
        """
        embeddings = {}
        
        for tc in self.test_cases:
            # Combine title, description, and steps for comprehensive embedding
            combined_text = f"{tc['title']} {tc['description']} {tc['steps']}"
            embeddings[tc['id']] = self.get_embedding(combined_text)
        
        return embeddings
    
    def find_similar_test_cases(
        self,
        bug_description: str,
        repro_steps: str,
        top_k: int = 20,
        min_similarity: float = 0.35,
        apply_area_boost: bool = True
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find test cases similar to the bug description using semantic search.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Reproduction steps for the bug
            top_k: Number of top similar test cases to return (default: 20)
            min_similarity: Minimum similarity threshold (default: 0.35)
            apply_area_boost: Whether to apply area-based similarity boosting (default: True)
            
        Returns:
            List of (test_case, similarity_score) tuples, filtered by min_similarity
        """
        # Combine bug info
        bug_text = f"{bug_description} {repro_steps}"
        bug_embedding = self.get_embedding(bug_text)
        
        # Compute test case embeddings
        tc_embeddings = self.compute_test_case_embeddings()
        
        # Calculate similarities using cosine similarity
        similarities = []
        for tc in self.test_cases:
            tc_embedding = tc_embeddings[tc['id']]
            
            # Cosine similarity
            dot_product = np.dot(bug_embedding, tc_embedding)
            norm_bug = np.linalg.norm(bug_embedding)
            norm_tc = np.linalg.norm(tc_embedding)
            
            if norm_bug > 0 and norm_tc > 0:
                similarity = dot_product / (norm_bug * norm_tc)
            else:
                similarity = 0.0
            
            # Apply area-based boost/penalty
            if apply_area_boost:
                area_boost = self._calculate_area_similarity_boost(tc, bug_text)
                similarity = min(1.0, similarity + area_boost)  # Cap at 1.0
            
            # Only include if above minimum threshold
            if similarity >= min_similarity:
                similarities.append((tc, float(similarity)))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def analyze_bug_with_claude(
        self,
        bug_description: str,
        repro_steps: str,
        code_changes: str,
        similar_tests: List[Tuple[Dict[str, Any], float]]
    ) -> Dict[str, Any]:
        """
        Use Claude to analyze the bug and provide detailed insights.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Steps to reproduce the bug
            code_changes: Description of code changes made to fix the bug
            similar_tests: List of similar test cases with scores
            
        Returns:
            Dictionary containing analysis results
        """
        # Prepare test cases summary for Claude
        test_cases_summary = []
        for tc, score in similar_tests:
            test_cases_summary.append({
                'id': tc['id'],
                'title': tc['title'],
                'description': tc['description'][:200] + '...' if len(tc['description']) > 200 else tc['description'],
                'steps': tc['steps'][:300] + '...' if len(tc['steps']) > 300 else tc['steps'],
                'similarity_score': score
            })
        
        prompt = f"""You are an expert QA analyst. Analyze this bug report and the related test cases.

BUG REPORT:
Description: {bug_description}

Reproduction Steps: {repro_steps}

Code Changes Made: {code_changes}

POTENTIALLY RELATED TEST CASES:
{json.dumps(test_cases_summary, indent=2)}

Please analyze and provide:

1. RELATED_TESTS: Which test cases are most relevant to this bug? For each, explain WHY it's related and assign a confidence score (0-100).

2. SUGGESTED_UPDATES: What changes should be made to existing test cases due to this bug fix? Be specific about which test cases need updates and what should change in their steps or expected results.

3. NEW_TEST_CASES: Are there any gaps in test coverage? Suggest new test cases that should be created to catch this type of bug in the future.

4. DUPLICATE_DETECTION: Do any of these test cases appear to test the same functionality? Identify potential duplicates or overlapping test scenarios.

Provide your response in JSON format with these exact keys: related_tests, suggested_updates, new_test_cases, duplicate_tests."""
        
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response_text = message.content[0].text
        
        # Try to parse JSON response
        try:
            # Find JSON in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                analysis = json.loads(json_str)
            else:
                # Fallback: create structured response from text
                analysis = {
                    "related_tests": [],
                    "suggested_updates": [],
                    "new_test_cases": [],
                    "duplicate_tests": [],
                    "raw_response": response_text
                }
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw response
            analysis = {
                "related_tests": [],
                "suggested_updates": [],
                "new_test_cases": [],
                "duplicate_tests": [],
                "raw_response": response_text
            }
        
        return analysis
    
    def detect_duplicates_with_claude(
        self,
        test_cases: List[Dict[str, Any]] = None,
        similarity_threshold: float = 0.90
    ) -> List[Dict[str, Any]]:
        """
        Detect duplicate or highly similar test cases using embeddings and Claude.
        
        Args:
            test_cases: List of test cases to analyze (defaults to all loaded tests)
            similarity_threshold: Minimum similarity score to consider as potential duplicate (default: 0.90)
            
        Returns:
            List of duplicate groups with analysis
        """
        if test_cases is None:
            test_cases = self.test_cases
        
        if len(test_cases) < 2:
            return []
        
        # Compute embeddings for all test cases
        tc_embeddings = {}
        for tc in test_cases:
            combined_text = f"{tc['title']} {tc['description']} {tc['steps']}"
            tc_embeddings[tc['id']] = self.get_embedding(combined_text)
        
        # Find potential duplicates based on similarity
        potential_duplicates = []
        test_ids = list(tc_embeddings.keys())
        
        for i in range(len(test_ids)):
            for j in range(i + 1, len(test_ids)):
                id1, id2 = test_ids[i], test_ids[j]
                
                # Cosine similarity
                emb1, emb2 = tc_embeddings[id1], tc_embeddings[id2]
                dot_product = np.dot(emb1, emb2)
                norm1 = np.linalg.norm(emb1)
                norm2 = np.linalg.norm(emb2)
                
                if norm1 > 0 and norm2 > 0:
                    similarity = dot_product / (norm1 * norm2)
                else:
                    similarity = 0.0
                
                if similarity >= similarity_threshold:
                    tc1 = next(tc for tc in test_cases if tc['id'] == id1)
                    tc2 = next(tc for tc in test_cases if tc['id'] == id2)
                    potential_duplicates.append({
                        'test_case_1': tc1,
                        'test_case_2': tc2,
                        'similarity_score': float(similarity)
                    })
        
        # If we found potential duplicates, ask Claude to analyze them
        if potential_duplicates:
            # Limit to top 20 most similar pairs to avoid token limits
            potential_duplicates.sort(key=lambda x: x['similarity_score'], reverse=True)
            potential_duplicates = potential_duplicates[:20]
            
            prompt = f"""You are a QA expert. Analyze these pairs of test cases that appear similar based on semantic analysis.

For each pair, determine:
1. Are they TRUE DUPLICATES (testing exact same functionality)?
2. Are they OVERLAPPING (testing similar but slightly different scenarios)?
3. Are they DISTINCT (different despite high similarity score)?

Provide recommendations for consolidation or keeping them separate.

POTENTIAL DUPLICATE PAIRS:
{json.dumps([{
    'pair_id': idx + 1,
    'test_1_id': pair['test_case_1']['id'],
    'test_1_title': pair['test_case_1']['title'],
    'test_1_steps': pair['test_case_1']['steps'][:200] + '...' if len(pair['test_case_1']['steps']) > 200 else pair['test_case_1']['steps'],
    'test_2_id': pair['test_case_2']['id'],
    'test_2_title': pair['test_case_2']['title'],
    'test_2_steps': pair['test_case_2']['steps'][:200] + '...' if len(pair['test_case_2']['steps']) > 200 else pair['test_case_2']['steps'],
    'similarity_score': pair['similarity_score']
} for idx, pair in enumerate(potential_duplicates)], indent=2)}

Respond in JSON format with: duplicate_groups (array of objects with pair_id, classification, reasoning, recommendation)."""
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            
            try:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    claude_analysis = json.loads(json_str)
                    duplicate_groups = claude_analysis.get('duplicate_groups', [])
                    
                    # Enrich the duplicate groups with actual test case IDs
                    enriched_groups = []
                    for group in duplicate_groups:
                        pair_id = group.get('pair_id')
                        if pair_id and pair_id <= len(potential_duplicates):
                            # Get the actual pair data
                            pair = potential_duplicates[pair_id - 1]  # pair_id is 1-indexed
                            enriched_group = {
                                'pair_id': pair_id,
                                'classification': group.get('classification', 'UNKNOWN'),
                                'reasoning': group.get('reasoning', ''),
                                'recommendation': group.get('recommendation', ''),
                                'test_case_1_id': pair['test_case_1']['id'],
                                'test_case_2_id': pair['test_case_2']['id'],
                                'similarity_score': pair['similarity_score']
                            }
                            enriched_groups.append(enriched_group)
                    
                    return enriched_groups if enriched_groups else duplicate_groups
            except json.JSONDecodeError:
                pass
            
            # Fallback: return basic similarity info
            return potential_duplicates
        
        return []
    
    def export_results_to_csv(
        self,
        results: Dict[str, Any],
        output_path: str,
        similarity_threshold: float = 0.70
    ) -> str:
        """
        Export analysis results to CSV format.
        
        Args:
            results: Results from analyze_bug_report()
            output_path: Path where CSV file should be saved
            similarity_threshold: Minimum similarity score to include
            
        Returns:
            Path to the created CSV file
        """
        csv_rows = []
        
        # Build a lookup for duplicate relationships
        duplicate_map = {}  # test_case_id -> {'related': list, 'classifications': list}
        duplicate_analysis = results.get('duplicate_analysis', [])
        
        for dup in duplicate_analysis:
            if isinstance(dup, dict):
                # Check if this has enriched data with test case IDs
                if 'test_case_1_id' in dup and 'test_case_2_id' in dup:
                    tc1_id = str(dup['test_case_1_id'])
                    tc2_id = str(dup['test_case_2_id'])
                    classification = dup.get('classification', 'UNKNOWN')
                    
                    # Initialize entries if they don't exist
                    if tc1_id not in duplicate_map:
                        duplicate_map[tc1_id] = {'related': [], 'classifications': []}
                    if tc2_id not in duplicate_map:
                        duplicate_map[tc2_id] = {'related': [], 'classifications': []}
                    
                    # Add relationship if not already present
                    if tc2_id not in duplicate_map[tc1_id]['related']:
                        duplicate_map[tc1_id]['related'].append(tc2_id)
                        duplicate_map[tc1_id]['classifications'].append(classification)
                    if tc1_id not in duplicate_map[tc2_id]['related']:
                        duplicate_map[tc2_id]['related'].append(tc1_id)
                        duplicate_map[tc2_id]['classifications'].append(classification)
                        
                elif 'test_case_1' in dup and 'test_case_2' in dup:
                    # This is raw similarity data (fallback response from detect_duplicates)
                    tc1_id = str(dup['test_case_1']['id'])
                    tc2_id = str(dup['test_case_2']['id'])
                    classification = 'HIGH SIMILARITY'
                    
                    if tc1_id not in duplicate_map:
                        duplicate_map[tc1_id] = {'related': [], 'classifications': []}
                    if tc2_id not in duplicate_map:
                        duplicate_map[tc2_id] = {'related': [], 'classifications': []}
                    
                    if tc2_id not in duplicate_map[tc1_id]['related']:
                        duplicate_map[tc1_id]['related'].append(tc2_id)
                        duplicate_map[tc1_id]['classifications'].append(classification)
                    if tc1_id not in duplicate_map[tc2_id]['related']:
                        duplicate_map[tc2_id]['related'].append(tc1_id)
                        duplicate_map[tc2_id]['classifications'].append(classification)
        
        # Build lookup for Claude's analysis
        claude_analysis = results.get('claude_analysis', {})
        related_tests_lookup = {}
        suggested_updates_lookup = {}
        
        for rt in claude_analysis.get('related_tests', []):
            if isinstance(rt, dict):
                # Handle various possible key names for test case ID
                tc_id = rt.get('id') or rt.get('test_id') or rt.get('test_case_id')
                if tc_id:
                    related_tests_lookup[str(tc_id)] = {
                        'confidence': rt.get('confidence', rt.get('confidence_score', '')),
                        'reason': rt.get('reason', rt.get('reasoning', rt.get('explanation', '')))
                    }
        
        for su in claude_analysis.get('suggested_updates', []):
            if isinstance(su, dict):
                tc_id = su.get('test_case_id') or su.get('test_id') or su.get('id')
                if tc_id:
                    suggested_updates_lookup[str(tc_id)] = su.get('suggested_change', su.get('update', su.get('change', '')))
        
        # Process each similar test case
        for item in results.get('similar_tests', []):
            test_case = item['test_case']
            similarity_score = item['similarity_score']
            
            # Only include test cases above threshold
            if similarity_score < similarity_threshold:
                continue
            
            tc_id = str(test_case['id'])
            
            # Get duplicate information - show related IDs for TRUE DUPLICATES and OVERLAPPING
            related_ids = ''
            duplicate_classification = 'DISTINCT'  # Default to DISTINCT if not analyzed
            if tc_id in duplicate_map:
                classifications = duplicate_map[tc_id]['classifications']
                # Combine unique classifications
                unique_classifications = list(set(classifications))
                duplicate_classification = ', '.join(unique_classifications) if unique_classifications else 'DISTINCT'
                
                # Include related IDs if any classification is OVERLAPPING or TRUE DUPLICATES
                show_related = any('OVERLAPPING' in c.upper() or 'TRUE DUPLICATE' in c.upper() 
                                  for c in classifications)
                if show_related:
                    related_ids = ', '.join(duplicate_map[tc_id]['related'])
            
            # Get Claude analysis
            claude_reason = ''
            if tc_id in related_tests_lookup:
                claude_reason = related_tests_lookup[tc_id]['reason']
            
            suggested_update = suggested_updates_lookup.get(tc_id, '')
            
            # Build reasoning: combine similarity-based reason with Claude's analysis
            reasoning_parts = []
            
            # Add similarity-based reasoning
            if similarity_score >= 0.6:
                reasoning_parts.append(f"High semantic similarity ({similarity_score:.3f})")
            elif similarity_score >= 0.45:
                reasoning_parts.append(f"Moderate semantic similarity ({similarity_score:.3f})")
            else:
                reasoning_parts.append(f"Related by semantic analysis ({similarity_score:.3f})")
            
            # Add Claude's reasoning if available
            if claude_reason:
                reasoning_parts.append(claude_reason)
            
            combined_reasoning = '; '.join(reasoning_parts)
            
            # Create CSV row
            csv_rows.append({
                'Test Case ID': tc_id,
                'Title': test_case.get('title', ''),
                'State': test_case.get('state', ''),
                'Area': test_case.get('area', ''),
                'Created Date': test_case.get('created_date', ''),
                'Similarity Score': f"{similarity_score:.4f}",
                'Reasoning': combined_reasoning,
                'Duplicate Classification': duplicate_classification,
                'Related Test IDs': related_ids,
                'Suggested Update': suggested_update
            })
        
        # Write to CSV
        if csv_rows:
            fieldnames = [
                'Test Case ID', 'Title', 'State', 'Area', 'Created Date',
                'Similarity Score', 'Reasoning', 'Duplicate Classification', 
                'Related Test IDs', 'Suggested Update'
            ]
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
            
            print(f"\n✓ Exported {len(csv_rows)} test cases to: {output_path}")
            return output_path
        else:
            print(f"\n⚠ No test cases above similarity threshold ({similarity_threshold})")
            return None
    
    def analyze_bug_report(
        self,
        bug_description: str,
        repro_steps: str,
        code_changes: str,
        top_k: int = 20,
        auto_load: bool = True,
        output_format: str = 'dict',
        csv_output_path: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        strictness: Literal['lenient', 'moderate', 'strict'] = 'moderate',
        apply_area_boost: bool = True
    ) -> Dict[str, Any]:
        """
        Complete analysis pipeline for a bug report.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Steps to reproduce
            code_changes: Code changes made to fix the bug
            top_k: Number of similar test cases to analyze (default: 20)
            auto_load: If True and MCP is enabled, automatically detect and load test cases
            output_format: Output format - 'dict' or 'csv' (default: 'dict')
            csv_output_path: Path for CSV output (auto-generated if None and format='csv')
            similarity_threshold: Minimum similarity score for CSV export (default: None, uses strictness setting)
            strictness: Filtering strictness level - 'lenient', 'moderate', or 'strict' (default: 'moderate')
            apply_area_boost: Whether to apply area-based similarity boosting (default: True)
            
        Returns:
            Complete analysis including related tests, updates, and duplicates.
            If output_format='csv', also includes 'csv_path' key with path to exported file.
        """
        # Auto-load test cases if MCP is enabled and no test cases are loaded
        if auto_load and self.use_mcp and len(self.test_cases) == 0:
            print("\nAuto-detecting relevant test cases...")
            load_result = self.detect_and_load_test_cases(bug_description, repro_steps)
            print(f"✓ Loaded {load_result['test_cases_count']} test cases from {len(load_result['areas_loaded'])} area(s)")
            print(f"  Recommendation: {load_result['recommendation']}\n")
        
        if len(self.test_cases) == 0:
            return {
                'error': 'No test cases loaded. Use detect_and_load_test_cases() or load_test_cases_from_csv() first.',
                'similar_tests': [],
                'claude_analysis': {},
                'duplicate_analysis': [],
                'summary': {
                    'total_test_cases_analyzed': 0,
                    'similar_tests_found': 0,
                    'potential_duplicates_found': 0
                }
            }
        
        # Get thresholds based on strictness level
        thresholds = self._get_strictness_thresholds(strictness)
        min_similarity = thresholds['min_similarity']
        claude_threshold = thresholds['claude_analysis']
        
        # Use strictness-based threshold for CSV export if not explicitly provided
        if similarity_threshold is None:
            similarity_threshold = thresholds['min_similarity']
        
        print(f"\nUsing '{strictness}' strictness level:")
        print(f"  - Minimum similarity: {min_similarity:.2f}")
        print(f"  - Claude analysis threshold: {claude_threshold:.2f}")
        print(f"  - CSV export threshold: {similarity_threshold:.2f}")
        print(f"  - Area boosting: {'enabled' if apply_area_boost else 'disabled'}\n")
        
        # Step 1: Find similar test cases using semantic search with strict filtering
        similar_tests = self.find_similar_test_cases(
            bug_description, 
            repro_steps, 
            top_k,
            min_similarity=min_similarity,
            apply_area_boost=apply_area_boost
        )
        
        # Step 2: Apply additional filtering before Claude analysis
        high_confidence_tests = [(tc, score) for tc, score in similar_tests if score >= claude_threshold]
        
        if not high_confidence_tests:
            print(f"⚠ Warning: No test cases above Claude analysis threshold ({claude_threshold:.2f})")
            if similar_tests:
                print(f"  Found {len(similar_tests)} test cases above minimum threshold ({min_similarity:.2f})")
                print(f"  Highest similarity: {similar_tests[0][1]:.3f}")
                # Use the similar tests anyway but warn user
                high_confidence_tests = similar_tests[:min(5, len(similar_tests))]  # Use top 5 at most
        
        # Step 3: Analyze with Claude using filtered test cases
        claude_analysis = self.analyze_bug_with_claude(
            bug_description, repro_steps, code_changes, high_confidence_tests
        )
        
        # Step 4: Detect duplicates among the similar tests
        similar_test_cases = [tc for tc, _ in similar_tests]
        duplicates = self.detect_duplicates_with_claude(similar_test_cases)
        
        # Combine results
        results = {
            'similar_tests': [
                {
                    'test_case': tc,
                    'similarity_score': score
                }
                for tc, score in similar_tests
            ],
            'claude_analysis': claude_analysis,
            'duplicate_analysis': duplicates,
            'summary': {
                'total_test_cases_analyzed': len(self.test_cases),
                'similar_tests_found': len(similar_tests),
                'high_confidence_tests_analyzed': len(high_confidence_tests),
                'potential_duplicates_found': len(duplicates),
                'strictness_level': strictness,
                'thresholds_used': thresholds
            }
        }
        
        # Export to CSV if requested
        if output_format == 'csv':
            if csv_output_path is None:
                # Auto-generate filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_output_path = f"bug_analysis_results_{timestamp}.csv"
            
            csv_path = self.export_results_to_csv(results, csv_output_path, similarity_threshold)
            results['csv_path'] = csv_path
        
        return results


# Example usage
if __name__ == "__main__":
    # Initialize agent with MCP enabled
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
    
    # Run analysis - test cases will be automatically detected and loaded
    print("\nAnalyzing bug report with automatic test case detection...")
    results = agent.analyze_bug_report(bug_description, repro_steps, code_changes)
    
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2))
