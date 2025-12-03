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
        print("Initializing Test Case Agent...")
        agent = TestCaseAgent()
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
    csv_file: UploadFile = File(..., description="CSV file containing test cases"),
    bug_description: str = Form(..., description="Description of the bug"),
    repro_steps: str = Form(..., description="Steps to reproduce the bug"),
    code_changes: str = Form(..., description="Description of code changes made to fix the bug"),
    top_k: int = Form(15, description="Number of similar test cases to analyze")
):
    """
    Analyze a bug report against test cases.
    
    This endpoint:
    1. Loads test cases from the uploaded CSV
    2. Finds test cases similar to the bug report
    3. Uses Claude AI to analyze relationships and suggest updates
    4. Detects duplicate test cases
    
    Args:
        csv_file: CSV file with test cases (columns: ID, Title, State, Area, Created Date, Description, Steps)
        bug_description: Description of the bug
        repro_steps: Steps to reproduce the bug
        code_changes: Code changes made to fix the bug
        top_k: Number of similar test cases to return
        
    Returns:
        Comprehensive analysis including related tests, suggested updates, and duplicates
    """
    try:
        # Validate file type
        if not csv_file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        
        # Get agent instance
        agent_instance = get_agent()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as tmp_file:
            content = await csv_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        try:
            # Load test cases from CSV
            print(f"Loading test cases from {csv_file.filename}...")
            agent_instance.load_test_cases_from_csv(tmp_path)
            
            # Run analysis
            print("Running bug analysis...")
            results = agent_instance.analyze_bug_report(
                bug_description=bug_description,
                repro_steps=repro_steps,
                code_changes=code_changes,
                top_k=top_k
            )
            
            print("Analysis complete!")
            return JSONResponse(content=results)
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception as e:
                print(f"Warning: Could not delete temporary file: {e}")
    
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


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
