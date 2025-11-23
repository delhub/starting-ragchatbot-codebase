"""
Pytest configuration and fixtures for RAG chatbot tests.
"""

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# Define SearchResults locally to avoid importing chromadb
@dataclass
class SearchResults:
    """Mock SearchResults class"""

    documents: List[str]
    metadata: List[Dict[str, Any]]
    distances: List[float]
    error: Optional[str] = None

    def is_empty(self) -> bool:
        return len(self.documents) == 0


# Import Config (should not have heavy dependencies)
try:
    from config import Config
except ImportError:
    # Fallback if config has issues
    @dataclass
    class Config:
        pass


@dataclass
class MockConfig(Config):
    """Test configuration with corrected MAX_RESULTS"""

    MAX_RESULTS: int = 5
    ANTHROPIC_API_KEY: str = "test-api-key-12345"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_HISTORY: int = 2
    MAX_TOOL_ROUNDS: int = 2
    CHROMA_PATH: str = "./test_chroma_db"


@pytest.fixture
def test_config():
    """Provide test configuration"""
    return MockConfig()


@pytest.fixture
def sample_course_data():
    """Sample course content for testing"""
    return {
        "documents": [
            "Prompt caching is a powerful feature that allows you to cache frequently used context...",
            "Computer use enables Claude to interact with computer interfaces through screenshots...",
            "The Model Context Protocol (MCP) provides a standardized way to connect AI models...",
        ],
        "metadata": [
            {
                "course_title": "Building Towards Computer Use with Claude",
                "lesson_number": 5,
                "chunk_index": 0,
                "instructor": "Dr. Jane Smith",
            },
            {
                "course_title": "Building Towards Computer Use with Claude",
                "lesson_number": 3,
                "chunk_index": 1,
                "instructor": "Dr. Jane Smith",
            },
            {
                "course_title": "Introduction to MCP",
                "lesson_number": 1,
                "chunk_index": 0,
                "instructor": "Prof. John Doe",
            },
        ],
        "distances": [0.15, 0.23, 0.35],
    }


@pytest.fixture
def mock_vector_store(sample_course_data):
    """Mock VectorStore with realistic search behavior"""
    mock_store = Mock()

    # Configure search method to return SearchResults
    def mock_search(
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
    ) -> SearchResults:
        # Simulate empty results for specific queries
        if "nonexistent" in query.lower():
            return SearchResults(documents=[], metadata=[], distances=[], error=None)

        # Simulate error condition
        if "error" in query.lower():
            return SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                error="Vector store connection error",
            )

        # Filter results based on parameters
        docs = sample_course_data["documents"].copy()
        meta = sample_course_data["metadata"].copy()
        dist = sample_course_data["distances"].copy()

        # Apply course filter
        if course_name:
            filtered = [
                (d, m, di)
                for d, m, di in zip(docs, meta, dist)
                if course_name.lower() in m.get("course_title", "").lower()
            ]
            if filtered:
                docs, meta, dist = zip(*filtered)
            else:
                docs, meta, dist = [], [], []

        # Apply lesson filter
        if lesson_number is not None:
            filtered = [
                (d, m, di)
                for d, m, di in zip(docs, meta, dist)
                if m.get("lesson_number") == lesson_number
            ]
            if filtered:
                docs, meta, dist = zip(*filtered)
            else:
                docs, meta, dist = [], [], []

        return SearchResults(
            documents=list(docs), metadata=list(meta), distances=list(dist), error=None
        )

    mock_store.search = Mock(side_effect=mock_search)

    # Mock link retrieval methods
    mock_store.get_course_link = Mock(return_value="https://example.com/course/123")
    mock_store.get_lesson_link = Mock(
        return_value="https://example.com/course/123/lesson/5"
    )

    # Mock course outline
    mock_store.get_course_outline = Mock(
        return_value={
            "course_title": "Building Towards Computer Use with Claude",
            "course_link": "https://example.com/course/123",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Introduction"},
                {"lesson_number": 2, "lesson_title": "Getting Started"},
                {"lesson_number": 3, "lesson_title": "Computer Use Basics"},
            ],
        }
    )

    return mock_store


@pytest.fixture
def mock_anthropic_response_no_tool():
    """Mock Anthropic API response without tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    # Mock text content
    mock_content = Mock()
    mock_content.text = "This is a direct response without using any tools."
    mock_content.type = "text"

    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture
def mock_anthropic_response_with_tool():
    """Mock Anthropic API response WITH tool use"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    # Mock tool use content block
    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "search_course_content"
    mock_tool_use.id = "tool_12345"
    mock_tool_use.input = {
        "query": "What is prompt caching?",
        "course_name": None,
        "lesson_number": None,
    }

    mock_response.content = [mock_tool_use]
    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock Anthropic API final response after tool execution"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    mock_content = Mock()
    mock_content.text = "Prompt caching is a powerful feature that allows you to cache frequently used context, reducing latency and costs for repeated queries."
    mock_content.type = "text"

    mock_response.content = [mock_content]
    return mock_response


@pytest.fixture
def mock_anthropic_client(
    mock_anthropic_response_no_tool,
    mock_anthropic_response_with_tool,
    mock_anthropic_final_response,
):
    """Mock Anthropic client with realistic message creation"""
    mock_client = Mock()

    # Track call count to return different responses
    call_count = 0

    def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1

        # First call with tools -> tool use
        if "tools" in kwargs and call_count == 1:
            return mock_anthropic_response_with_tool
        # Second call without tools -> final response
        else:
            return mock_anthropic_final_response

    mock_client.messages.create = Mock(side_effect=mock_create)
    return mock_client


@pytest.fixture
def mock_tool_manager(mock_vector_store):
    """Mock ToolManager with registered tools"""
    from search_tools import CourseSearchTool, ToolManager

    tool_manager = ToolManager()
    search_tool = CourseSearchTool(mock_vector_store)
    tool_manager.register_tool(search_tool)

    return tool_manager


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager"""
    mock_manager = Mock()
    mock_manager.get_history = Mock(return_value=None)
    mock_manager.update_session = Mock()
    return mock_manager


@pytest.fixture
def reset_call_counts():
    """Reset any global state between tests"""
    yield
    # Cleanup after test


def create_mock_tool_use(tool_name: str, tool_input: dict, tool_id: str = None):
    """
    Helper function to create mock tool_use content blocks for testing.

    Args:
        tool_name: Name of the tool
        tool_input: Input parameters for the tool
        tool_id: Optional tool ID (generated if not provided)

    Returns:
        Mock object representing a tool_use content block
    """
    mock_tool = Mock()
    mock_tool.type = "tool_use"
    mock_tool.name = tool_name
    mock_tool.input = tool_input
    mock_tool.id = tool_id or f"tool_{tool_name}_{id(mock_tool)}"
    return mock_tool


# ============================================================================
# API Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_rag_system():
    """Mock RAG system for API testing"""
    mock_rag = Mock()

    # Mock query method
    mock_rag.query = Mock(return_value=(
        "This is a test response about prompt caching.",
        [
            {
                "text": "Building Towards Computer Use - Lesson 5",
                "course_link": "https://example.com/course",
                "lesson_link": "https://example.com/lesson"
            }
        ]
    ))

    # Mock session manager
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session = Mock(return_value="test_session_123")

    # Mock get_course_analytics
    mock_rag.get_course_analytics = Mock(return_value={
        "total_courses": 2,
        "course_titles": [
            "Building Towards Computer Use with Claude",
            "Introduction to MCP"
        ]
    })

    return mock_rag


@pytest.fixture
def test_client(mock_rag_system):
    """Create TestClient with mocked RAG system"""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional, Dict

    # Create a test app without static file mounting
    test_app = FastAPI(title="Test Course Materials RAG System")

    # Define request/response models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Optional[str]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Define API endpoints inline
    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/")
    async def root():
        return {"message": "RAG Chatbot API"}

    return TestClient(test_app)


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is prompt caching?",
        "session_id": None
    }


@pytest.fixture
def sample_query_request_with_session():
    """Sample query request with session ID"""
    return {
        "query": "Tell me more about computer use",
        "session_id": "existing_session_123"
    }
