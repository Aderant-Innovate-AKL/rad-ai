"""
FastAPI application for Test Case Analysis API.

Provides endpoints for analyzing bug reports against test cases,
identifying related tests, suggesting updates, and detecting duplicates.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from agent.agent import TestCaseAgent

# Load environment variables
load_dotenv()

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
