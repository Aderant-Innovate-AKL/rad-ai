"""
FastAPI backend for Test Case Analysis Agent
Provides REST API endpoints for bug analysis, CSV export, TFS/GitHub integration, and PR summarization
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback
import tempfile
import requests
import base64
import re
import json
from dotenv import load_dotenv
from bedrock_client import get_claude_client, check_bedrock_configured, invoke_claude, get_bedrock_client

# Load environment variables
load_dotenv()

# Add agent to path
sys.path.append(str(Path(__file__).parent))

from agent.agent import TestCaseAgent

# TFS Configuration (loaded from .env file)
TFS_BASE_URL = os.getenv("TFS_BASE_URL", "")  # e.g., https://tfs.aderant.com/tfs
TFS_COLLECTION = os.getenv("TFS_COLLECTION", "")  # e.g., ADERANT
TFS_PROJECT = os.getenv("TFS_PROJECT", "")  # e.g., ExpertSuite
TFS_PAT = os.getenv("TFS_PAT", "")  # Personal Access Token

# GitHub Configuration (loaded from .env file)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Personal Access Token
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "")  # Organization or username
GITHUB_REPO = os.getenv("GITHUB_REPO", "")  # Repository name

# Initialize FastAPI app
app = FastAPI(
    title="Test Case Analysis API",
    description="AI-powered test case analysis and bug report matching with TFS/GitHub integration",
    version="2.0.0"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent: Optional[TestCaseAgent] = None


def get_agent() -> TestCaseAgent:
    """Get or initialize the test case agent."""
    global agent
    if agent is None:
        print("Initializing Test Case Agent with MCP enabled...")
        agent = TestCaseAgent(use_mcp=True)
    return agent


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


def extract_bug_id_from_text(text: str) -> Optional[str]:
    """Extract bug ID from text (looks for #number pattern).
    
    The bug ID is expected to be prefixed with # in the PR description.
    Examples: #12345, #789, Bug #12345, Fixes #12345
    
    Returns the first bug ID found, or None if no bug ID is found.
    """
    if not text:
        return None
    
    # Pattern to match bug IDs with # prefix
    # Looks for # followed by digits (at least 1 digit)
    # Avoids matching things like "#1" in commit hashes by requiring at least 3 digits for bug IDs
    pattern = r'#(\d{3,})'
    
    matches = re.findall(pattern, text)
    if matches:
        return matches[0]  # Return the first bug ID found
    
    return None


def extract_html_text(html_content: str) -> str:
    """Extract plain text from HTML content."""
    if not html_content:
        return ""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '\n', html_content)
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Clean up whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text.strip()


# Pydantic models for API requests/responses
class BugReportRequest(BaseModel):
    bug_description: str = Field(..., description="Description of the bug")
    repro_steps: str = Field(..., description="Steps to reproduce the bug")
    code_changes: str = Field(..., description="Code changes made to fix the bug")
    top_k: int = Field(default=15, ge=1, le=50, description="Number of similar test cases to analyze")
    similarity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum similarity score")
    output_format: str = Field(default="csv", description="Output format: 'dict' or 'csv'")


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    summary: Optional[Dict[str, Any]] = None
    csv_path: Optional[str] = None
    similar_tests: Optional[List[Dict[str, Any]]] = None


class HealthResponse(BaseModel):
    status: str
    agent_initialized: bool
    mcp_enabled: bool


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
    summary: str = Field(description="AI-generated summary of the PR changes")
    bug_id: Optional[str] = Field(None, description="Bug ID extracted from PR description (if found)")
    bug_info: Optional[BugInfoResponse] = Field(None, description="Bug information fetched from TFS (if bug_id found)")


class PRSummaryResponse(BaseModel):
    """Response model for AI-generated PR summary."""
    pr_number: int = Field(description="The PR number")
    title: str = Field(description="PR title")
    summary: str = Field(description="AI-generated summary of the changes")
    files_changed: list[str] = Field(description="List of changed file names")
    total_files: int = Field(description="Total number of files changed")


class ParsedBugContext(BaseModel):
    """Response model for parsed bug context."""
    bug_description: str = Field(description="Extracted bug description")
    repro_steps: str = Field(description="Extracted reproduction steps")
    code_changes: str = Field(description="Extracted/summarized code changes from PR")
    confidence: str = Field(description="Confidence level of extraction: high, medium, low")
    notes: str = Field(default="", description="Additional notes about the parsing")


@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent
    try:
        agent = TestCaseAgent(use_mcp=True)
        print("✓ Agent initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize agent: {e}")
        traceback.print_exc()


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Test Case Analysis API - Unified Version",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        agent_instance = get_agent()
        return HealthResponse(
            status="healthy",
            agent_initialized=True,
            mcp_enabled=agent_instance.use_mcp if agent_instance else False
        )
    except Exception:
        return HealthResponse(
            status="unhealthy",
            agent_initialized=False,
            mcp_enabled=False
        )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_bug_report(request: BugReportRequest):
    """
    Analyze a bug report and find related test cases (JSON-based endpoint)
    
    Returns similar test cases, Claude analysis, and exports to CSV
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        # Generate unique filename for CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"bug_analysis_{timestamp}.csv"
        csv_path = os.path.join(os.getcwd(), csv_filename)
        
        # Run analysis
        results = agent.analyze_bug_report(
            bug_description=request.bug_description,
            repro_steps=request.repro_steps,
            code_changes=request.code_changes,
            top_k=request.top_k,
            auto_load=True,
            output_format=request.output_format,
            csv_output_path=csv_path if request.output_format == 'csv' else None,
            similarity_threshold=request.similarity_threshold
        )
        
        # Check for errors
        if 'error' in results:
            raise HTTPException(status_code=400, detail=results['error'])
        
        # Prepare response
        return AnalysisResponse(
            success=True,
            message="Analysis completed successfully",
            summary=results.get('summary'),
            csv_path=results.get('csv_path'),
            similar_tests=results.get('similar_tests', [])[:10]  # Return top 10 for preview
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/parse-bug-context", response_model=ParsedBugContext)
async def parse_bug_context(
    bug_info: str = Form(..., description="Raw bug information (title, description, repro steps)"),
    pr_info: str = Form("", description="Raw PR information (title, summary, file changes)")
):
    """
    Use Claude AI to intelligently parse and extract structured information from bug reports and PR changes.
    
    This endpoint acts as a preprocessing step before /analyze-bug, using LLM intelligence to:
    - Extract clear bug descriptions from verbose bug reports
    - Identify and format reproduction steps
    - Summarize code changes from PR information
    - Handle various input formats and structures
    
    Args:
        bug_info: Raw bug information (can include title, description, repro steps in any format)
        pr_info: Raw PR information (can include title, summary, file changes)
        
    Returns:
        Structured bug context ready for analysis
    """
    if not check_bedrock_configured():
        raise HTTPException(
            status_code=500,
            detail="AWS_BEARER_TOKEN_BEDROCK not configured in .env file"
        )
    
    print("\n" + "="*80)
    print("[AI] /parse-bug-context - Using Claude (Bedrock) to extract structured information")
    print("="*80)
    
    try:
        client = get_claude_client()
        
        prompt = f"""You are an expert QA analyst. Extract structured information from the following bug report and PR information.

BUG INFORMATION:
{bug_info}

PR/CODE CHANGES INFORMATION:
{pr_info if pr_info else "No PR information provided"}

Your task:
1. Extract a clear, concise BUG DESCRIPTION (2-4 sentences describing what the bug is)
2. Extract REPRODUCTION STEPS (numbered list of steps to reproduce the bug)
3. Extract or summarize CODE CHANGES (what was changed to fix the bug, based on PR info)

IMPORTANT:
- If reproduction steps are not clearly stated, write "Reproduction steps not provided"
- If code changes/PR info is missing, write "Code changes not provided"
- Focus on clarity and conciseness
- Remove any metadata like "BUG ID:", "TITLE:", etc. - just extract the content

Provide your response in JSON format with these exact keys:
{{
  "bug_description": "Clear description of the bug",
  "repro_steps": "Numbered reproduction steps or 'Reproduction steps not provided'",
  "code_changes": "Summary of code changes or 'Code changes not provided'",
  "confidence": "high/medium/low",
  "notes": "Any additional notes about the extraction"
}}"""
        
        response_text = client.create_message(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
        )
        
        # Parse JSON response
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                
                print(f"✓ Successfully parsed bug context")
                print(f"  Confidence: {parsed_data.get('confidence', 'unknown')}")
                print(f"  Bug Description: {parsed_data.get('bug_description', '')[:100]}...")
                print("="*80 + "\n")
                
                return ParsedBugContext(
                    bug_description=parsed_data.get('bug_description', ''),
                    repro_steps=parsed_data.get('repro_steps', ''),
                    code_changes=parsed_data.get('code_changes', ''),
                    confidence=parsed_data.get('confidence', 'medium'),
                    notes=parsed_data.get('notes', '')
                )
            else:
                raise ValueError("No JSON found in response")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"⚠ Warning: Could not parse JSON response: {e}")
            # Fallback: return raw content with low confidence
            return ParsedBugContext(
                bug_description=bug_info[:500] if bug_info else "Could not extract bug description",
                repro_steps="Reproduction steps not provided",
                code_changes=pr_info[:500] if pr_info else "Code changes not provided",
                confidence="low",
                notes=f"Failed to parse LLM response: {str(e)}"
            )
    
    except Exception as e:
        error_msg = str(e)
        if "Bedrock" in error_msg:
            print(f"[FAIL] Bedrock API error: {error_msg}")
            raise HTTPException(status_code=500, detail=f"AI API error: {error_msg}")
        print(f"[FAIL] Error parsing bug context: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Failed to parse bug context: {error_msg}")


@app.post("/analyze-bug")
async def analyze_bug(
    bug_description: str = Form(..., description="Description of the bug"),
    repro_steps: str = Form(..., description="Steps to reproduce the bug"),
    code_changes: str = Form(..., description="Description of code changes made to fix the bug"),
    top_k: int = Form(15, description="Number of similar test cases to analyze"),
    csv_file: Optional[UploadFile] = File(None, description="Optional CSV file - if not provided, will auto-detect relevant test cases")
):
    """
    Analyze a bug report against test cases (Form-based endpoint for file uploads)
    
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
    # Print API inputs for debugging
    print("\n" + "="*80)
    print("📥 /analyze-bug API REQUEST INPUTS")
    print("="*80)
    print(f"Bug Description: {bug_description[:200]}{'...' if len(bug_description) > 200 else ''}")
    print(f"Repro Steps: {repro_steps[:200]}{'...' if len(repro_steps) > 200 else ''}")
    print(f"Code Changes: {code_changes[:200]}{'...' if len(code_changes) > 200 else ''}")
    print(f"Top K: {top_k}")
    print(f"CSV File: {csv_file.filename if csv_file else 'None (auto-detection mode)'}")
    print("="*80 + "\n")
    
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
                
                # Generate unique filename for CSV export
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = f"bug_analysis_{timestamp}.csv"
                csv_path = os.path.join(os.getcwd(), csv_filename)
                
                # Run analysis with auto_load=False since we manually loaded
                print("Running bug analysis...")
                results = agent_instance.analyze_bug_report(
                    bug_description=bug_description,
                    repro_steps=repro_steps,
                    code_changes=code_changes,
                    top_k=top_k,
                    auto_load=False,
                    output_format='csv',
                    csv_output_path=csv_path
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
            
            # Generate unique filename for CSV export
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            csv_filename = f"bug_analysis_{timestamp}.csv"
            csv_path = os.path.join(os.getcwd(), csv_filename)
            
            results = agent_instance.analyze_bug_report(
                bug_description=bug_description,
                repro_steps=repro_steps,
                code_changes=code_changes,
                top_k=top_k,
                auto_load=True,
                output_format='csv',
                csv_output_path=csv_path
            )
        
        print("Analysis complete!")
        
        # Add CSV download information to the response
        if 'csv_path' in results:
            results['csv_filename'] = os.path.basename(results['csv_path'])
            results['download_url'] = f"/download/{results['csv_filename']}"
        
        return JSONResponse(content=results)
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/download/{filename}")
async def download_csv(filename: str):
    """
    Download a generated CSV file
    
    Args:
        filename: Name of the CSV file to download
    """
    file_path = os.path.join(os.getcwd(), filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if not filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files can be downloaded")
    
    return FileResponse(
        path=file_path,
        media_type='text/csv',
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/stats")
async def get_statistics():
    """Get statistics about loaded test cases"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not agent.mcp_server:
        raise HTTPException(status_code=400, detail="MCP server not available")
    
    try:
        stats = agent.mcp_server.get_statistics()
        return JSONResponse(content=stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@app.get("/areas")
async def list_areas():
    """List all available test case areas"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not agent.mcp_server:
        raise HTTPException(status_code=400, detail="MCP server not available")
    
    try:
        areas_info = agent.mcp_server.list_areas()
        return JSONResponse(content=areas_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list areas: {str(e)}")


@app.post("/detect-areas")
async def detect_relevant_areas(bug_description: str, repro_steps: str = ""):
    """
    Detect which test case areas are relevant to a bug description
    
    Args:
        bug_description: Description of the bug
        repro_steps: Optional reproduction steps
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    if not agent.mcp_server:
        raise HTTPException(status_code=400, detail="MCP server not available")
    
    try:
        detection = agent.mcp_server.detect_relevant_areas(bug_description, repro_steps)
        return JSONResponse(content=detection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect areas: {str(e)}")


@app.post("/detect-area")
async def detect_area(
    bug_description: str = Form(..., description="Description of the bug"),
    repro_steps: str = Form("", description="Steps to reproduce the bug (optional)")
):
    """
    Detect which area(s) a bug belongs to based on its description (Form-based endpoint)
    
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
    Fetch Pull Request information from GitHub including changed files and AI-generated summary.
    
    Args:
        pr_number: The PR number to fetch
        
    Returns:
        PR information including title, state, list of changed files, and AI summary
    """
    if not GITHUB_OWNER or not GITHUB_REPO:
        raise HTTPException(
            status_code=500,
            detail="GitHub configuration missing. Please set GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO in .env file"
        )
    
    if not check_bedrock_configured():
        raise HTTPException(
            status_code=500,
            detail="AWS_BEARER_TOKEN_BEDROCK not configured in .env file"
        )
    
    try:
        # GitHub REST API endpoint for PR details
        pr_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}"
        files_url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/pulls/{pr_number}/files"
        
        print(f"GitHub Config - Owner: {GITHUB_OWNER}, Repo: {GITHUB_REPO}")
        print(f"Fetching PR info from: {pr_url}")
        
        headers = get_github_headers()
        
        # Fetch PR details
        pr_response = requests.get(pr_url, headers=headers, timeout=30)
        
        if pr_response.status_code == 404:
            error_detail = f"PR #{pr_number} not found in {GITHUB_OWNER}/{GITHUB_REPO}"
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
        
        # Build file changes list
        file_changes = []
        total_additions = 0
        total_deletions = 0
        
        # Build file changes summary for AI
        file_summaries = []
        for file in files_data:
            filename = file.get("filename", "")
            status = file.get("status", "")
            additions = file.get("additions", 0)
            deletions = file.get("deletions", 0)
            changes = file.get("changes", 0)
            patch = file.get("patch", "")
            
            file_changes.append(FileChange(
                filename=filename,
                status=status,
                additions=additions,
                deletions=deletions,
                changes=changes
            ))
            total_additions += additions
            total_deletions += deletions
            
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
        
        # Generate AI summary of changes
        print("Generating AI summary of PR changes...")
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

        # Call Claude API via Bedrock
        client = get_claude_client()
        
        summary = client.create_message(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
        )
        print("[OK] AI summary generated successfully")
        
        # Extract bug ID from PR description
        bug_id = extract_bug_id_from_text(pr_body)
        bug_info = None
        
        if bug_id:
            print(f"[OK] Found bug ID #{bug_id} in PR description")
            # Try to fetch bug info from TFS
            try:
                if TFS_BASE_URL and TFS_COLLECTION and TFS_PROJECT and TFS_PAT:
                    url = f"{TFS_BASE_URL}/{TFS_COLLECTION}/{TFS_PROJECT}/_apis/wit/workitems/{bug_id}?api-version=4.1&$expand=all"
                    headers = get_tfs_headers()
                    bug_response = requests.get(url, headers=headers, timeout=30)
                    
                    if bug_response.status_code == 200:
                        work_item = bug_response.json()
                        fields = work_item.get("fields", {})
                        
                        title = fields.get("System.Title", "No title")
                        description_html = fields.get("System.Description", "") or fields.get("Microsoft.VSTS.TCM.ReproSteps", "") or ""
                        repro_steps_html = fields.get("Microsoft.VSTS.TCM.ReproSteps", "") or ""
                        
                        description = extract_html_text(description_html)
                        repro_steps = extract_html_text(repro_steps_html)
                        
                        bug_info = BugInfoResponse(
                            bug_id=bug_id,
                            title=title,
                            description=description,
                            repro_steps=repro_steps
                        )
                        print(f"[OK] Fetched bug info for #{bug_id}")
                    else:
                        print(f"[WARN] Could not fetch bug info for #{bug_id}: HTTP {bug_response.status_code}")
                else:
                    print("[WARN] TFS not configured, skipping bug info fetch")
            except Exception as e:
                print(f"[WARN] Error fetching bug info for #{bug_id}: {str(e)}")
        else:
            print("[INFO] No bug ID found in PR description")
        
        return PRInfoResponse(
            pr_number=pr_number,
            title=pr_title,
            state=pr_data.get("state", ""),
            files_changed=file_changes,
            total_files=len(file_changes),
            total_additions=total_additions,
            total_deletions=total_deletions,
            summary=summary,
            bug_id=bug_id,
            bug_info=bug_info
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
    
    if not check_bedrock_configured():
        raise HTTPException(
            status_code=500,
            detail="AWS_BEARER_TOKEN_BEDROCK not configured in .env file"
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
        
        # Build file changes summary for AI
        file_summaries = []
        file_names = []
        for file in files_data:
            filename = file.get("filename", "")
            file_names.append(filename)
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

        # Call Claude API via Bedrock
        client = get_claude_client()
        
        summary = client.create_message(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error summarizing PR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to summarize PR: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    print("\n" + "="*80)
    print("Starting Unified Test Case Analysis API Server")
    print("="*80)
    print("\n📊 Available Endpoints:")
    print("  • Bug Analysis: /analyze, /analyze-bug")
    print("  • TFS Integration: /fetch-bug-info/{bug_id}")
    print("  • GitHub PR: /fetch-pr-info/{pr_number}, /summarize-pr/{pr_number}")
    print("  • Test Cases: /areas, /detect-area, /detect-areas, /detect-duplicates")
    print("  • Utilities: /download/{filename}, /stats, /health")
    print("\n🌐 Access Points:")
    print("  • API Documentation: http://localhost:8000/docs")
    print("  • Interactive API: http://localhost:8000/redoc")
    print("  • Health Check: http://localhost:8000/health")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
