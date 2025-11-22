import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import os

from config import config
from rag_system import RAGSystem

# Initialize FastAPI app
app = FastAPI(title="Course Materials RAG System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem(config)

# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[Dict[str, Optional[str]]]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]

# API Endpoints

@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Process a query and return response with sources"""
    try:
        # Create session if not provided
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()

        # Process query using RAG system
        answer, sources = rag_system.query(request.query, session_id)

        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )
    except Exception as e:
        # Log error details for debugging
        error_msg = str(e)
        print(f"Error processing query: {error_msg}")

        # Import traceback for detailed error logging
        import traceback
        print(traceback.format_exc())

        # Provide helpful error messages for common issues
        if "API key" in error_msg or "authentication" in error_msg.lower():
            detail = "Authentication error: Please check your Anthropic API key in the .env file"
        elif "vector store" in error_msg.lower() or "chroma" in error_msg.lower():
            detail = "Database error: Unable to search course content"
        elif "rate limit" in error_msg.lower():
            detail = "Rate limit exceeded: Please try again in a moment"
        elif "No text content found" in error_msg or "list index out of range" in error_msg:
            detail = "Response processing error: The AI returned an unexpected response format. Please try rephrasing your question."
        else:
            detail = f"An error occurred while processing your query: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)

@app.get("/api/courses", response_model=CourseStats)
async def get_course_stats():
    """Get course analytics and statistics"""
    try:
        analytics = rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Validate configuration and load initial documents on startup"""
    # Validate Anthropic API key
    if not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "":
        print("=" * 70)
        print("WARNING: ANTHROPIC_API_KEY not set!")
        print("Please create a .env file with your API key:")
        print("  ANTHROPIC_API_KEY=your_key_here")
        print("The application will start but queries will fail.")
        print("=" * 70)
    else:
        print(f"✓ Anthropic API key configured (starts with: {config.ANTHROPIC_API_KEY[:10]}...)")

    # Validate other critical settings
    if config.MAX_RESULTS == 0:
        print("WARNING: MAX_RESULTS is set to 0. No search results will be returned!")
    else:
        print(f"✓ MAX_RESULTS configured: {config.MAX_RESULTS}")

    # Load initial documents
    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Loading initial documents...")
        try:
            courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=False)
            print(f"✓ Loaded {courses} courses with {chunks} chunks")
        except Exception as e:
            print(f"Error loading documents: {e}")
    else:
        print(f"WARNING: Documents folder '{docs_path}' not found")

# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response
    
    
# Serve static files for the frontend
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")