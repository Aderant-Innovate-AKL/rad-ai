"""
FastAPI backend for Test Case Analysis Agent
Provides REST API endpoints for bug analysis and CSV export
"""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback

# Add agent to path
sys.path.append(str(Path(__file__).parent))

from agent.agent import TestCaseAgent

# Initialize FastAPI app
app = FastAPI(
    title="Test Case Analysis API",
    description="AI-powered test case analysis and bug report matching",
    version="1.0.0"
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
        "message": "Test Case Analysis API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if agent is not None else "unhealthy",
        agent_initialized=agent is not None,
        mcp_enabled=agent.use_mcp if agent else False
    )


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_bug_report(request: BugReportRequest):
    """
    Analyze a bug report and find related test cases
    
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


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    print("\n" + "="*80)
    print("Starting Test Case Analysis API Server")
    print("="*80)
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
