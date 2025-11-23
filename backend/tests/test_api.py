"""
API endpoint tests for FastAPI application

Tests the /api/query, /api/courses, and root endpoints with various scenarios
including successful requests, error handling, and edge cases.
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.mark.api
class TestQueryEndpoint:
    """Test /api/query endpoint"""

    def test_query_without_session_id(self, test_client, sample_query_request):
        """Test query endpoint creates new session when none provided"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Check data types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Session ID should be created
        assert data["session_id"] == "test_session_123"

    def test_query_with_session_id(self, test_client, sample_query_request_with_session):
        """Test query endpoint uses provided session ID"""
        response = test_client.post("/api/query", json=sample_query_request_with_session)

        assert response.status_code == 200
        data = response.json()

        # Should use the provided session ID
        assert data["session_id"] == "existing_session_123"

    def test_query_returns_answer(self, test_client, sample_query_request):
        """Test that query endpoint returns an answer"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Should have non-empty answer
        assert len(data["answer"]) > 0
        assert "prompt caching" in data["answer"].lower()

    def test_query_returns_sources(self, test_client, sample_query_request):
        """Test that query endpoint returns sources"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Should have sources
        assert len(data["sources"]) > 0

        # Check source structure
        source = data["sources"][0]
        assert "text" in source
        assert "course_link" in source
        assert "lesson_link" in source

    def test_query_with_empty_string(self, test_client):
        """Test query with empty string"""
        response = test_client.post("/api/query", json={
            "query": "",
            "session_id": None
        })

        # Should still process (even if query is empty)
        assert response.status_code == 200

    def test_query_with_long_text(self, test_client):
        """Test query with very long text"""
        long_query = "What is prompt caching? " * 100

        response = test_client.post("/api/query", json={
            "query": long_query,
            "session_id": None
        })

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    def test_query_missing_required_field(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post("/api/query", json={
            "session_id": "test_123"
            # Missing "query" field
        })

        # Should return 422 validation error
        assert response.status_code == 422

    def test_query_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 validation error
        assert response.status_code == 422

    def test_query_calls_rag_system(self, test_client, sample_query_request, mock_rag_system):
        """Test that query endpoint calls RAG system"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200

        # Verify RAG system was called
        mock_rag_system.query.assert_called_once()

        # Check call arguments
        call_args = mock_rag_system.query.call_args[0]
        assert call_args[0] == "What is prompt caching?"


@pytest.mark.api
class TestCoursesEndpoint:
    """Test /api/courses endpoint"""

    def test_courses_endpoint_returns_stats(self, test_client):
        """Test courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Check data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_courses_endpoint_returns_correct_count(self, test_client):
        """Test that course count matches titles list"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Count should match number of titles
        assert data["total_courses"] == len(data["course_titles"])
        assert data["total_courses"] == 2

    def test_courses_endpoint_returns_titles(self, test_client):
        """Test that course titles are returned"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Should have course titles
        assert len(data["course_titles"]) > 0
        assert "Building Towards Computer Use with Claude" in data["course_titles"]

    def test_courses_endpoint_calls_rag_system(self, test_client, mock_rag_system):
        """Test that courses endpoint calls RAG system analytics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200

        # Verify RAG system method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_endpoint_with_query_params(self, test_client):
        """Test courses endpoint ignores query parameters"""
        response = test_client.get("/api/courses?filter=test&sort=asc")

        # Should still work (query params ignored)
        assert response.status_code == 200


@pytest.mark.api
class TestRootEndpoint:
    """Test root / endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns message"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Should have a message
        assert "message" in data

    def test_root_endpoint_structure(self, test_client):
        """Test root endpoint returns expected structure"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Check it's a dict with message
        assert isinstance(data, dict)
        assert isinstance(data["message"], str)


@pytest.mark.api
class TestAPIErrorHandling:
    """Test error handling in API endpoints"""

    def test_query_with_rag_system_error(self, test_client, mock_rag_system):
        """Test query endpoint handles RAG system errors"""
        # Configure mock to raise exception
        mock_rag_system.query.side_effect = Exception("RAG system error")

        response = test_client.post("/api/query", json={
            "query": "test query",
            "session_id": None
        })

        # Should return 500 error (handled by FastAPI)
        assert response.status_code == 500

    def test_courses_with_analytics_error(self, test_client, mock_rag_system):
        """Test courses endpoint handles analytics errors"""
        # Configure mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = test_client.get("/api/courses")

        # Should return 500 error
        assert response.status_code == 500

    def test_query_with_invalid_content_type(self, test_client):
        """Test query with wrong content type"""
        response = test_client.post(
            "/api/query",
            data="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Should return 422 validation error
        assert response.status_code == 422


@pytest.mark.api
class TestAPIResponseFormat:
    """Test API response format and data validation"""

    def test_query_response_format(self, test_client, sample_query_request):
        """Test query response matches expected format"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Validate all required fields present
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_query_source_format(self, test_client, sample_query_request):
        """Test that sources have correct structure"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Check each source has required fields
        for source in data["sources"]:
            assert "text" in source
            assert "course_link" in source
            assert "lesson_link" in source

    def test_courses_response_format(self, test_client):
        """Test courses response matches expected format"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Validate required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Validate types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # All titles should be strings
        for title in data["course_titles"]:
            assert isinstance(title, str)


@pytest.mark.api
class TestAPIContentNegotiation:
    """Test API content type handling"""

    def test_query_accepts_json(self, test_client, sample_query_request):
        """Test query endpoint accepts JSON content type"""
        response = test_client.post(
            "/api/query",
            json=sample_query_request,
            headers={"Accept": "application/json"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_courses_returns_json(self, test_client):
        """Test courses endpoint returns JSON"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_root_returns_json(self, test_client):
        """Test root endpoint returns JSON"""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


@pytest.mark.api
class TestSessionManagement:
    """Test session management through API"""

    def test_multiple_queries_same_session(self, test_client, mock_rag_system):
        """Test multiple queries with same session ID"""
        session_id = "persistent_session"

        # First query
        response1 = test_client.post("/api/query", json={
            "query": "What is AI?",
            "session_id": session_id
        })

        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["session_id"] == session_id

        # Second query with same session
        response2 = test_client.post("/api/query", json={
            "query": "Tell me more",
            "session_id": session_id
        })

        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["session_id"] == session_id

        # Should have called RAG system twice
        assert mock_rag_system.query.call_count == 2

    def test_different_sessions_isolated(self, test_client):
        """Test that different sessions are isolated"""
        # Query with session 1
        response1 = test_client.post("/api/query", json={
            "query": "Question 1",
            "session_id": "session_1"
        })

        # Query with session 2
        response2 = test_client.post("/api/query", json={
            "query": "Question 2",
            "session_id": "session_2"
        })

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Should have different session IDs
        assert data1["session_id"] != data2["session_id"]
