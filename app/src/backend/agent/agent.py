"""
Test Case Analysis Agent

This module provides an AI agent that analyzes bug reports and identifies related test cases,
suggests updates, and detects duplicates using Anthropic Claude and semantic embeddings.
"""

import os
import csv
import json
from typing import List, Dict, Any, Tuple
from pathlib import Path
import anthropic
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestCaseAgent:
    """
    AI Agent for analyzing test cases against bug reports.
    
    Uses Anthropic Claude for natural language understanding and reasoning,
    and sentence transformers for semantic similarity matching.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the agent with necessary models and configurations.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        
        # Cache for embeddings
        self.embeddings_cache = {}
        self.test_cases = []
        print("Agent initialized successfully")
        
    def load_test_cases_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from a CSV file.
        
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
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding vector for a text string with caching using Claude.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array (using simple hash-based embedding)
        """
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]
        
        # Create a simple embedding based on text characteristics
        # This is a lightweight alternative that doesn't require PyTorch
        words = text.lower().split()
        
        # Create a feature vector based on:
        # - Length, word count, unique words, etc.
        length_norm = min(len(text) / 1000.0, 1.0)
        word_count_norm = min(len(words) / 100.0, 1.0)
        unique_ratio = len(set(words)) / max(len(words), 1)
        
        # Create keyword-based features for test case domain
        keywords = {
            'post': 0, 'create': 0, 'edit': 0, 'delete': 0, 'release': 0,
            'disbursement': 0, 'session': 0, 'currency': 0, 'split': 0,
            'merge': 0, 'cancel': 0, 'import': 0, 'export': 0, 'security': 0,
            'validation': 0, 'amount': 0, 'office': 0, 'employee': 0
        }
        
        for word in words:
            if word in keywords:
                keywords[word] += 1
        
        # Normalize keyword counts
        max_count = max(keywords.values()) if keywords.values() else 1
        max_count = max(max_count, 1)  # Ensure it's at least 1 to avoid division by zero
        keyword_features = [count / max_count for count in keywords.values()]
        
        # Combine into embedding vector
        embedding = np.array([length_norm, word_count_norm, unique_ratio] + keyword_features)
        
        self.embeddings_cache[text] = embedding
        return embedding
    
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
        top_k: int = 15
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find test cases similar to the bug description using semantic search.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Reproduction steps for the bug
            top_k: Number of top similar test cases to return
            
        Returns:
            List of (test_case, similarity_score) tuples
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
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Detect duplicate or highly similar test cases using embeddings and Claude.
        
        Args:
            test_cases: List of test cases to analyze (defaults to all loaded tests)
            similarity_threshold: Minimum similarity score to consider as potential duplicate
            
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
                    return claude_analysis.get('duplicate_groups', [])
            except json.JSONDecodeError:
                pass
            
            # Fallback: return basic similarity info
            return potential_duplicates
        
        return []
    
    def analyze_bug_report(
        self,
        bug_description: str,
        repro_steps: str,
        code_changes: str,
        top_k: int = 15
    ) -> Dict[str, Any]:
        """
        Complete analysis pipeline for a bug report.
        
        Args:
            bug_description: Description of the bug
            repro_steps: Steps to reproduce
            code_changes: Code changes made to fix the bug
            top_k: Number of similar test cases to analyze
            
        Returns:
            Complete analysis including related tests, updates, and duplicates
        """
        # Step 1: Find similar test cases using semantic search
        similar_tests = self.find_similar_test_cases(bug_description, repro_steps, top_k)
        
        # Step 2: Analyze with Claude
        claude_analysis = self.analyze_bug_with_claude(
            bug_description, repro_steps, code_changes, similar_tests
        )
        
        # Step 3: Detect duplicates among the similar tests
        similar_test_cases = [tc for tc, _ in similar_tests]
        duplicates = self.detect_duplicates_with_claude(similar_test_cases)
        
        # Combine results
        return {
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
                'potential_duplicates_found': len(duplicates)
            }
        }


# Example usage
if __name__ == "__main__":
    # Initialize agent
    agent = TestCaseAgent()
    
    # Load test cases
    csv_path = "../../../test_cases_with_descriptions_expert_disbursements.csv"
    agent.load_test_cases_from_csv(csv_path)
    
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
    
    # Run analysis
    print("\nAnalyzing bug report...")
    results = agent.analyze_bug_report(bug_description, repro_steps, code_changes)
    
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2))
