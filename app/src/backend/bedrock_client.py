"""
AWS Bedrock Client for Claude API calls

This module provides a wrapper for calling Claude models via AWS Bedrock
using bearer token authentication (AWS_BEARER_TOKEN_BEDROCK).
"""

import json
import os
import requests
from typing import List, Dict, Optional

# Default model: Claude 3.5 Sonnet on Bedrock (cross-region inference profile)
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")


def get_bedrock_endpoint(region: str, model_id: str) -> str:
    """
    Get the Bedrock runtime endpoint URL.
    
    Args:
        region: AWS region (e.g., 'us-east-1')
        model_id: Model ID to invoke
        
    Returns:
        Full URL for the invoke_model API
    """
    return f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke"


def invoke_claude(
    messages: List[Dict[str, str]],
    max_tokens: int = 4096,
    model_id: Optional[str] = None
) -> str:
    """
    Invoke Claude model on Bedrock using bearer token authentication.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        max_tokens: Maximum tokens in response (default: 4096)
        model_id: Model ID to use (defaults to BEDROCK_MODEL_ID)
        
    Returns:
        Response text from Claude
        
    Raises:
        ValueError: If AWS_BEARER_TOKEN_BEDROCK is not configured
        Exception: If the Bedrock API call fails
    """
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not bearer_token:
        raise ValueError("AWS_BEARER_TOKEN_BEDROCK not configured")
    
    if model_id is None:
        model_id = BEDROCK_MODEL_ID
    
    # Build request
    endpoint = get_bedrock_endpoint(region, model_id)
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages
    }
    
    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=body,
            timeout=120
        )
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("message", response.text)
            except:
                pass
            raise Exception(f"{response.status_code} - {error_detail}")
        
        response_body = response.json()
        return response_body["content"][0]["text"]
        
    except requests.exceptions.Timeout:
        raise Exception("Bedrock API request timed out")
    except requests.exceptions.ConnectionError as e:
        raise Exception(f"Could not connect to Bedrock: {str(e)}")
    except Exception as e:
        if "Bedrock" in str(e):
            raise
        raise Exception(f"Bedrock API error: {str(e)}")


class BedrockClaudeClient:
    """
    A client wrapper that provides an interface similar to anthropic.Anthropic
    but uses AWS Bedrock for the actual API calls.
    
    This makes migration from anthropic SDK easier by providing compatible methods.
    """
    
    def __init__(self):
        """Initialize the Bedrock Claude client."""
        self._model_id = BEDROCK_MODEL_ID
    
    def create_message(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        model: Optional[str] = None
    ) -> str:
        """
        Create a message using Claude via Bedrock.
        
        This method provides a similar interface to anthropic's messages.create()
        but returns just the text content for simplicity.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens in response
            model: Model ID (uses default if not specified)
            
        Returns:
            Response text from Claude
        """
        model_id = model if model else self._model_id
        return invoke_claude(messages, max_tokens, model_id)


# Singleton instance for easy access
_bedrock_client: Optional[BedrockClaudeClient] = None


def get_claude_client() -> BedrockClaudeClient:
    """
    Get a singleton BedrockClaudeClient instance.
    
    Returns:
        BedrockClaudeClient instance
    """
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClaudeClient()
    return _bedrock_client


def check_bedrock_configured() -> bool:
    """
    Check if AWS Bedrock is properly configured.
    
    Returns:
        True if AWS_BEARER_TOKEN_BEDROCK is set, False otherwise
    """
    return bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK"))


# Keep for backwards compatibility
def get_bedrock_client():
    """Legacy function - returns the BedrockClaudeClient instance."""
    return get_claude_client()
