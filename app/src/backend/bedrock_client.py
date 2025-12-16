"""
AWS Bedrock Client Helper

Provides a configured Bedrock client for invoking Claude models
using bearer token authentication.
"""

import os
import json
import boto3
from botocore.config import Config
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


# Default model: Claude 3.5 Sonnet on Bedrock (cross-region inference profile)
BEDROCK_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"


class BedrockBearerAuth:
    """Custom auth class that uses bearer token instead of SigV4."""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
    
    def add_auth(self, request):
        """Add bearer token to request headers."""
        request.headers['Authorization'] = f'Bearer {self.bearer_token}'


def get_bedrock_client():
    """
    Create Bedrock runtime client with bearer token authentication.
    
    Returns:
        tuple: (boto3 bedrock-runtime client, bearer_token)
        
    Raises:
        ValueError: If AWS_BEARER_TOKEN_BEDROCK is not configured
    """
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not bearer_token:
        raise ValueError("AWS_BEARER_TOKEN_BEDROCK not configured in .env file")
    
    # Create client with minimal config (we'll override auth)
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            retries={"max_attempts": 3, "mode": "standard"}
        )
    )
    
    return client, bearer_token


def invoke_claude(messages: list, max_tokens: int = 2048, model_id: str = None) -> str:
    """
    Invoke Claude model on AWS Bedrock.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        max_tokens: Maximum tokens in response (default: 2048)
        model_id: Optional model ID override (default: Claude 3.5 Sonnet)
        
    Returns:
        str: The text response from Claude
        
    Raises:
        ValueError: If bearer token is not configured
        Exception: If Bedrock API call fails
    """
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    if not bearer_token:
        raise ValueError("AWS_BEARER_TOKEN_BEDROCK not configured in .env file")
    
    model = model_id or BEDROCK_MODEL_ID
    
    # Prepare the request body for Claude on Bedrock
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages
    })
    
    # Create the Bedrock runtime client
    client = boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(
            retries={"max_attempts": 3, "mode": "standard"}
        )
    )
    
    # For bearer token auth, we need to make a direct HTTP request
    # using the requests library with proper signing
    import requests
    
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model}/invoke"
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    response = requests.post(
        endpoint,
        headers=headers,
        data=body,
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Bedrock API error: {response.status_code} - {response.text}")
    
    response_body = response.json()
    return response_body["content"][0]["text"]


def invoke_claude_with_client(client, bearer_token: str, messages: list, 
                               max_tokens: int = 2048, model_id: str = None) -> str:
    """
    Invoke Claude model using a pre-configured client.
    
    This is an alternative method that accepts an existing client,
    useful when you want to reuse the client across multiple calls.
    
    Args:
        client: boto3 bedrock-runtime client (unused, kept for API compatibility)
        bearer_token: The bearer token for authentication
        messages: List of message dicts with 'role' and 'content' keys
        max_tokens: Maximum tokens in response (default: 2048)
        model_id: Optional model ID override (default: Claude 3.5 Sonnet)
        
    Returns:
        str: The text response from Claude
    """
    import requests
    
    region = os.getenv("AWS_REGION", "us-east-1")
    model = model_id or BEDROCK_MODEL_ID
    
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages
    })
    
    endpoint = f"https://bedrock-runtime.{region}.amazonaws.com/model/{model}/invoke"
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    response = requests.post(
        endpoint,
        headers=headers,
        data=body,
        timeout=120
    )
    
    if response.status_code != 200:
        raise Exception(f"Bedrock API error: {response.status_code} - {response.text}")
    
    response_body = response.json()
    return response_body["content"][0]["text"]

