"""
FastAPI application for Test Case Analysis API.

⚠️ DEPRECATED: This file has been merged into api.py
Please use api.py instead, which now contains all endpoints from both api.py and main.py.

This file is kept for reference only.
"""

# All functionality has been moved to api.py
# To run the unified API server, use:
# python api.py
# or
# uvicorn api:app --reload

print("="*80)
print("⚠️  WARNING: main.py is deprecated!")
print("="*80)
print("\nThis file has been merged into api.py")
print("Please run: python api.py")
print("\nOr use: uvicorn api:app --reload --host 0.0.0.0 --port 8000")
print("="*80)

# Original code below for reference only
"""

import os
import tempfile
import requests
import base64
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import anthropic

from agent.agent import TestCaseAgent

# Load environment variables
load_dotenv()

# TFS Configuration (loaded from .env file)
TFS_BASE_URL = os.getenv("TFS_BASE_URL", "")  # e.g., https://tfs.aderant.com/tfs
TFS_COLLECTION = os.getenv("TFS_COLLECTION", "")  # e.g., ADERANT
TFS_PROJECT = os.getenv("TFS_PROJECT", "")  # e.g., ExpertSuite
TFS_PAT = os.getenv("TFS_PAT", "")  # Personal Access Token

# GitHub Configuration (loaded from .env file)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Personal Access Token
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")  # Organization or username
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # Repository name

app = FastAPI(
    title="Test Case Analysis API",
    description="AI-powered test case analysis for bug reports",
    version="1.0.0"
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance (initialized on first request)
agent: Optional[TestCaseAgent] = None


def get_agent() -> TestCaseAgent:
    """Get or initialize the test case agent."""
    global agent
    if agent is None:
        print("Initializing Test Case Agent with MCP enabled...")
        agent = TestCaseAgent(use_mcp=True)
    return agent


# Request/Response Models
class AnalysisResponse(BaseModel):
    """Response model for bug analysis."""
    similar_tests: list = Field(description="Test cases similar to the bug report")
    claude_analysis: dict = Field(description="Claude's detailed analysis")
    duplicate_analysis: list = Field(description="Detected duplicate test cases")
    summary: dict = Field(description="Summary statistics")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    message: str
    agent_loaded: bool


class BugInfoResponse(BaseModel):
    """Response model for bug info fetch."""
    bug_id: str = Field(description="The bug ID")
    title: str = Field(description="Bug title")
    description: str = Field(description="Bug description")
    repro_steps: str = Field(description="Reproduction steps")


class FileChange(BaseModel):
    """Model for a single file change in a PR."""
    filename: str = Field(description="Name/path of the changed file")
    status: str = Field(description="Status: added, modified, removed, renamed")
    additions: int = Field(description="Number of lines added")
    deletions: int = Field(description="Number of lines deleted")
    changes: int = Field(description="Total number of changes")


class PRInfoResponse(BaseModel):
    """Response model for PR info fetch."""
    pr_number: int = Field(description="The PR number")
    title: str = Field(description="PR title")
    state: str = Field(description="PR state: open, closed, or merged")
    files_changed: list[FileChange] = Field(description="List of changed files")
    total_files: int = Field(description="Total number of files changed")
    total_additions: int = Field(description="Total lines added")
    total_deletions: int = Field(description="Total lines deleted")
    summary: str = Field(default="", description="AI-generated summary of the changes")


class PRSummaryResponse(BaseModel):
    """Response model for AI-generated PR summary."""
    pr_number: int = Field(description="The PR number")
    title: str = Field(description="PR title")
    summary: str = Field(description="AI-generated summary of the changes")
    files_changed: list[str] = Field(description="List of changed file names")
    total_files: int = Field(description="Total number of files changed")


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - API information."""
    return {
        "status": "ok",
        "message": "Test Case Analysis API is running",
        "agent_loaded": agent is not None
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        agent_instance = get_agent()
        return {
            "status": "healthy",
            "message": "API is operational",
            "agent_loaded": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Error: {str(e)}",
            "agent_loaded": False
        }


@app.get("/get-test-cases-csv")
async def get_test_cases_csv():
    """
    Serve the test cases CSV file for analysis.
    
    Returns:
        CSV file containing test cases
    """
    from fastapi.responses import FileResponse
    
    # Look for test cases CSV file in common locations
    possible_paths = [
        Path(__file__).parent.parent.parent.parent / "test_cases_with_descriptions_expert_disbursements.csv",
        Path(__file__).parent.parent.parent.parent / "test_cases_expert_disbursements.csv",
        Path(__file__).parent / "test_cases.csv",
    ]
    
    for csv_path in possible_paths:
        if csv_path.exists():
            return FileResponse(
                path=str(csv_path),
                media_type="text/csv",
                filename="test_cases.csv"
            )
    
    raise HTTPException(
        status_code=404,
        detail="Test cases CSV file not found. Please ensure a test cases file exists."
    )


def get_tfs_headers():
    """Get authorization headers for TFS API calls."""
    if not TFS_PAT:
        return {}
    # Azure DevOps uses Basic auth with PAT
    auth_string = base64.b64encode(f":{TFS_PAT}".encode()).decode()
    return {
        "Authorization": f"Basic {auth_string}",
        "Content-Type": "application/json"
    }


def get_github_headers():
    """Get authorization headers for GitHub API calls."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def extract_html_text(html_content: str) -> str:
    """Extract plain text from HTML content."""
    if not html_content:
        return ""
    import re
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '\n', html_content)
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


def generate_pr_summary(pr_title: str, pr_body: str, files_data: list) -> str:
    """
    Generate an AI-powered summary of PR changes using Claude.
    
    Args:
        pr_title: The PR title
        pr_body: The PR description/body
        files_data: List of file change data from GitHub API
        
    Returns:
        AI-generated summary string, or empty string if summarization fails
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        print("Warning: ANTHROPIC_API_KEY not configured, skipping AI summary")
        return ""
    
    try:
        # Build file changes summary for AI
        file_summaries = []
        for file in files_data:
            filename = file.get("filename", "")
            status = file.get("status", "")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            patch = file.get("patch", "")
            
            # Truncate large patches to avoid token limits
            if len(patch) > 2000:
                patch = patch[:2000] + "\n... (truncated)"
            
            file_summaries.append(f"""
File: {filename}
Status: {status}
Changes: +{additions} -{deletions}
Diff:
{patch}
""")
        
        # Prepare prompt for Claude
        changes_text = "\n---\n".join(file_summaries)
        
        prompt = f"""Analyze this Pull Request and provide a clear, concise summary of the changes.

PR Title: {pr_title}
PR Description: {pr_body[:1000] if pr_body else "No description provided"}

Files Changed ({len(files_data)} files):
{changes_text}

Please provide:
1. A brief overall summary of what this PR accomplishes (2-3 sentences)
2. Key changes organized by category (e.g., New Features, Bug Fixes, Refactoring, etc.)
3. Any notable patterns or concerns in the changes

Keep the summary concise but informative."""

        # Call Claude API
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
        
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
        
    except anthropic.APIError as e:
        print(f"AI API error during summarization: {str(e)}")
        return ""
    except Exception as e:
        print(f"Error generating PR summary: {str(e)}")
        return ""


@app.get("/fetch-bug-info/{bug_id}", response_model=BugInfoResponse)
async def fetch_bug_info(bug_id: str):
    """
    Fetch bug information from TFS/Azure DevOps.
    
    Args:
        bug_id: The work item ID of the bug
        
    Returns:
        Bug information including title, description, repro steps, and metadata
    """
    if not TFS_BASE_URL or not TFS_COLLECTION or not TFS_PROJECT:
        raise HTTPException(
            status_code=500, 
            detail="TFS configuration missing. Please set TFS_BASE_URL, TFS_COLLECTION, TFS_PROJECT, and TFS_PAT in .env file"
        )
    
    try:
        # TFS REST API endpoint for work items
        # Format: {TFS_URL}/{COLLECTION}/{PROJECT}/_apis/wit/workitems/{id}
        url = f"{TFS_BASE_URL}/{TFS_COLLECTION}/{TFS_PROJECT}/_apis/wit/workitems/{bug_id}?api-version=4.1&$expand=all"
        
        print(f"Fetching bug info from: {url}")
        
        headers = get_tfs_headers()
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Bug {bug_id} not found")
        
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="TFS authentication failed. Check your PAT token.")
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"TFS API error: {response.text}"
            )
        
        work_item = response.json()
        fields = work_item.get("fields", {})
        
        # Extract only title, description, and repro steps
        title = fields.get("System.Title", "")
        description = extract_html_text(fields.get("System.Description", ""))
        repro_steps = extract_html_text(fields.get("Microsoft.VSTS.TCM.ReproSteps", ""))
        
        return {
            "bug_id": bug_id,
            "title": title,
            "description": description,
            "repro_steps": repro_steps
        }
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="TFS request timed out")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to TFS server")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching bug info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch bug info: {str(e)}")


@app.get("/fetch-pr-info/{pr_number}", response_model=PRInfoResponse)
async def fetch_pr_info(pr_number: int):
    """
    Fetch Pull Request information from GitHub including changed files.
    
    Args:
        pr_number: The PR number to fetch
        
    Returns:
        PR information including title, state, author, and list of changed files
    """
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise HTTPException(
            status_code=500,
            detail="GitHub configuration missing. Please set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO in .env file"
        )
    
    try:
        # GitHub REST API endpoint for PR details
        pr_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}"
        files_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}/files"
        
        print(f"GitHub Config - Owner: {GITHUB_OWNER}, Repo: {GITHUB_REPO}")
        print(f"Fetching PR info from: {pr_url}")
        print(f"Token present: {bool(GITHUB_TOKEN)}")
        
        headers = get_github_headers()
        
        # Fetch PR details
        pr_response = requests.get(pr_url, headers=headers, timeout=30)
        
        print(f"GitHub API response status: {pr_response.status_code}")
        
        if pr_response.status_code == 404:
            # Get more details about why it's 404
            error_detail = f"PR #{pr_number} not found in {GITHUB_OWNER}/{GITHUB_REPO}. "
            error_detail += "Check: 1) PR number exists, 2) Repo name is correct, 3) Token has access to private repos"
            raise HTTPException(status_code=404, detail=error_detail)
        
        if pr_response.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub authentication failed. Check your token.")
        
        if pr_response.status_code == 403:
            raise HTTPException(status_code=403, detail="GitHub API rate limit exceeded or access denied.")
        
        if pr_response.status_code != 200:
            raise HTTPException(
                status_code=pr_response.status_code,
                detail=f"GitHub API error: {pr_response.text}"
            )
        
        pr_data = pr_response.json()
        
        # Fetch changed files
        print(f"Fetching changed files from: {files_url}")
        files_response = requests.get(files_url, headers=headers, timeout=30)
        
        if files_response.status_code != 200:
            raise HTTPException(
                status_code=files_response.status_code,
                detail=f"Failed to fetch PR files: {files_response.text}"
            )
        
        files_data = files_response.json()
        
        # Build file changes list
        file_changes = []
        total_additions = 0
        total_deletions = 0
        
        for file in files_data:
            file_changes.append(FileChange(
                filename=file.get("filename", ""),
                status=file.get("status", ""),
                additions=file.get("additions", 0),
                deletions=file.get("deletions", 0),
                changes=file.get("changes", 0)
            ))
            total_additions += file.get("additions", 0)
            total_deletions += file.get("deletions", 0)
        
        # Generate AI summary of the PR changes
        pr_title = pr_data.get("title", "")
        pr_body = pr_data.get("body", "") or ""
        print("Generating AI summary of PR changes...")
        summary = generate_pr_summary(pr_title, pr_body, files_data)
        
        return PRInfoResponse(
            pr_number=pr_number,
            title=pr_title,
            state=pr_data.get("state", ""),
            files_changed=file_changes,
            total_files=len(file_changes),
            total_additions=total_additions,
            total_deletions=total_deletions,
            summary=summary
        )
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="GitHub request timed out")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to GitHub")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching PR info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch PR info: {str(e)}")


@app.post("/analyze-bug", response_model=AnalysisResponse)
async def analyze_bug(
    bug_description: str = Form(..., description="Description of the bug"),
    repro_steps: str = Form(..., description="Steps to reproduce the bug"),
    code_changes: str = Form(..., description="Description of code changes made to fix the bug"),
    top_k: int = Form(15, description="Number of similar test cases to analyze"),
    csv_file: Optional[UploadFile] = File(None, description="Optional CSV file - if not provided, will auto-detect relevant test cases")
):
    """
    Analyze a bug report against test cases.
    
    This endpoint has two modes:
    1. **Auto-detection mode (recommended)**: Don't upload a CSV. The system will automatically
       detect which test case area(s) are relevant based on the bug description and load only
       those test cases.
    2. **Manual mode**: Upload a specific CSV file to analyze against.
    
    The analysis:
    1. Finds test cases similar to the bug report
    2. Uses Claude AI to analyze relationships and suggest updates
    3. Detects duplicate test cases
    
    Args:
        bug_description: Description of the bug
        repro_steps: Steps to reproduce the bug
        code_changes: Code changes made to fix the bug
        top_k: Number of similar test cases to return
        csv_file: Optional CSV file (columns: ID, Title, State, Area, Created Date, Description, Steps)
        
    Returns:
        Comprehensive analysis including related tests, suggested updates, and duplicates
    """
    try:
        # Get agent instance
        agent_instance = get_agent()
        
        # If CSV file is provided, use manual mode
        if csv_file is not None:
            # Validate file type
            if not csv_file.filename.endswith('.csv'):
                raise HTTPException(status_code=400, detail="File must be a CSV")
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp_file:
                content = await csv_file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Load test cases from CSV
                print(f"Loading test cases from {csv_file.filename}...")
                agent_instance.load_test_cases_from_csv(tmp_path)
                
                # Run analysis with auto_load=False since we manually loaded
                print("Running bug analysis...")
                results = agent_instance.analyze_bug_report(
                    bug_description=bug_description,
                    repro_steps=repro_steps,
                    code_changes=code_changes,
                    top_k=top_k,
                    auto_load=False
                )
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except Exception as e:
                    print(f"Warning: Could not delete temporary file: {e}")
        else:
            # Auto-detection mode - let the agent detect and load relevant test cases
            print("Auto-detection mode: detecting relevant test cases...")
            results = agent_instance.analyze_bug_report(
                bug_description=bug_description,
                repro_steps=repro_steps,
                code_changes=code_changes,
                top_k=top_k,
                auto_load=True
            )
        
        print("Analysis complete!")
        return JSONResponse(content=results)
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/areas")
async def list_areas():
    """
    List all available test case areas/app families.
    
    Returns information about each area including descriptions and test case counts.
    """
    try:
        agent_instance = get_agent()
        if agent_instance.use_mcp and agent_instance.mcp_server:
            areas_info = agent_instance.mcp_server.list_areas()
            return JSONResponse(content=areas_info)
        else:
            raise HTTPException(status_code=501, detail="MCP is not enabled")
    except Exception as e:
        print(f"Error listing areas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list areas: {str(e)}")


@app.post("/detect-area")
async def detect_area(
    bug_description: str = Form(..., description="Description of the bug"),
    repro_steps: str = Form("", description="Steps to reproduce the bug (optional)")
):
    """
    Detect which area(s) a bug belongs to based on its description.
    
    This can be used to preview which test cases would be loaded before running
    a full analysis.
    
    Args:
        bug_description: Description of the bug
        repro_steps: Reproduction steps (optional)
        
    Returns:
        Detected areas with confidence scores and recommendations
    """
    try:
        agent_instance = get_agent()
        if agent_instance.use_mcp and agent_instance.mcp_server:
            detection = agent_instance.mcp_server.detect_relevant_areas(
                bug_description, repro_steps
            )
            return JSONResponse(content=detection)
        else:
            raise HTTPException(status_code=501, detail="MCP is not enabled")
    except Exception as e:
        print(f"Error detecting area: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Area detection failed: {str(e)}")


@app.post("/detect-duplicates")
async def detect_duplicates(
    csv_file: UploadFile = File(..., description="CSV file containing test cases"),
    similarity_threshold: float = Form(0.85, description="Similarity threshold (0-1)")
):
    """
    Detect duplicate test cases in the provided CSV.
    
    Args:
        csv_file: CSV file with test cases
        similarity_threshold: Minimum similarity score to consider as duplicate (0-1)
        
    Returns:
        List of duplicate test case groups with analysis
    """
    try:
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        agent_instance = get_agent()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp_file:
            content = await csv_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Load test cases
            print(f"Loading test cases from {csv_file.filename}...")
            agent_instance.load_test_cases_from_csv(tmp_path)
            
            # Detect duplicates
            print("Detecting duplicates...")
            duplicates = agent_instance.detect_duplicates_with_claude(
                similarity_threshold=similarity_threshold
            )
            
            return JSONResponse(content={
                "duplicate_groups": duplicates,
                "total_duplicates_found": len(duplicates)
            })
            
        finally:
            try:
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {e}")
    
    except Exception as e:
        print(f"Error detecting duplicates: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Duplicate detection failed: {str(e)}")


@app.get("/summarize-pr/{pr_number}", response_model=PRSummaryResponse)
async def summarize_pr_changes(pr_number: int):
    """
    Generate an AI-powered summary of file changes in a Pull Request.
    
    Args:
        pr_number: The PR number to summarize
        
    Returns:
        AI-generated summary of the changes made in the PR
    """
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise HTTPException(
            status_code=500,
            detail="GitHub configuration missing. Please set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO in .env file"
        )
    
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY not configured in .env file"
        )
    
    try:
        # Fetch PR details from GitHub
        pr_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}"
        files_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}/files"
        
        headers = get_github_headers()
        
        # Fetch PR details
        pr_response = requests.get(pr_url, headers=headers, timeout=30)
        
        if pr_response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"PR #{pr_number} not found")
        
        if pr_response.status_code != 200:
            raise HTTPException(
                status_code=pr_response.status_code,
                detail=f"GitHub API error: {pr_response.text}"
            )
        
        pr_data = pr_response.json()
        pr_title = pr_data.get("title", "")
        pr_body = pr_data.get("body", "") or ""
        
        # Fetch changed files with patches
        files_response = requests.get(files_url, headers=headers, timeout=30)
        
        if files_response.status_code != 200:
            raise HTTPException(
                status_code=files_response.status_code,
                detail=f"Failed to fetch PR files: {files_response.text}"
            )
        
        files_data = files_response.json()
        
        # Get file names for response
        file_names = [file.get("filename", "") for file in files_data]
        
        # Generate AI summary using helper function
        summary = generate_pr_summary(pr_title, pr_body, files_data)
        
        if not summary:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate AI summary"
            )
        
        return PRSummaryResponse(
            pr_number=pr_number,
            title=pr_title,
            summary=summary,
            files_changed=file_names,
            total_files=len(files_data)
        )
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="GitHub request timed out")
    except requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="Could not connect to GitHub")
    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"AI API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error summarizing PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize PR: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    print("Starting Test Case Analysis API...")
    print("API will be available at: http://localhost:8000")
    print("API docs available at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
