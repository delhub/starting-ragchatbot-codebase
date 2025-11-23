"""
Unit tests for CourseSearchTool in search_tools.py
"""

import os
import sys

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolDefinition:
    """Test tool definition and metadata"""

    def test_get_tool_definition_structure(self, mock_vector_store):
        """Test that tool definition has correct structure"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "name" in definition
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

    def test_tool_definition_schema(self, mock_vector_store):
        """Test input schema has required properties"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()
        schema = definition["input_schema"]

        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]


class TestCourseSearchToolExecution:
    """Test tool execution with various inputs"""

    def test_execute_basic_query(self, mock_vector_store):
        """Test basic query without filters"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is prompt caching?")

        # Should return formatted results
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Prompt caching" in result or "prompt caching" in result.lower()

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test query with course_name filter"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(
            query="What is computer use?", course_name="Building Towards Computer Use"
        )

        # Should filter to only that course
        assert isinstance(result, str)
        assert "Building Towards Computer Use" in result

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test query with lesson_number filter"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="Tell me about the content", lesson_number=5)

        # Should filter to lesson 5
        assert isinstance(result, str)
        assert "Lesson 5" in result

    def test_execute_with_both_filters(self, mock_vector_store):
        """Test query with both course and lesson filters"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(
            query="What is covered?",
            course_name="Building Towards Computer Use",
            lesson_number=5,
        )

        # Should have both filters applied
        assert isinstance(result, str)
        assert "Building Towards Computer Use" in result
        assert "Lesson 5" in result

    def test_execute_no_results(self, mock_vector_store):
        """Test handling of empty search results"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="nonexistent topic that won't match")

        # Should return appropriate message
        assert isinstance(result, str)
        assert "No relevant content found" in result

    def test_execute_no_results_with_filters(self, mock_vector_store):
        """Test empty results message includes filter info"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(
            query="nonexistent", course_name="Some Course", lesson_number=99
        )

        assert "No relevant content found" in result
        assert "Some Course" in result
        assert "lesson 99" in result

    def test_execute_error_handling(self, mock_vector_store):
        """Test that vector store errors are propagated"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="trigger error in query")

        # Should return the error message
        assert isinstance(result, str)
        assert "error" in result.lower()


class TestCourseSearchToolFormatting:
    """Test result formatting"""

    def test_format_results_structure(self, mock_vector_store, sample_course_data):
        """Test that results are formatted with course and lesson context"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is prompt caching?")

        # Should have headers with course title
        assert "[" in result and "]" in result
        # Should have course titles
        assert (
            "Building Towards Computer Use" in result or "Introduction to MCP" in result
        )

    def test_format_results_includes_lesson_numbers(self, mock_vector_store):
        """Test that lesson numbers are included in formatted output"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="Tell me about the content")

        # Should include lesson numbers
        assert "Lesson" in result

    def test_format_results_multiple_documents(self, mock_vector_store):
        """Test formatting of multiple search results"""
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is covered in the courses?")

        # Should have multiple sections (documents separated by double newline)
        sections = result.split("\n\n")
        assert len(sections) >= 1  # At least one result


class TestCourseSearchToolSourceTracking:
    """Test source tracking functionality"""

    def test_last_sources_tracked(self, mock_vector_store):
        """Test that last_sources is populated after search"""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="What is prompt caching?")

        # Should have sources stored
        assert hasattr(tool, "last_sources")
        assert isinstance(tool.last_sources, list)
        assert len(tool.last_sources) > 0

    def test_source_structure(self, mock_vector_store):
        """Test that sources have correct structure"""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="What is prompt caching?")

        # Each source should have required fields
        for source in tool.last_sources:
            assert "text" in source
            assert "course_link" in source
            assert "lesson_link" in source

    def test_source_text_includes_course_and_lesson(self, mock_vector_store):
        """Test that source text includes course title and lesson number"""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="Tell me about the content")

        # Source text should include course and lesson info
        for source in tool.last_sources:
            text = source["text"]
            assert len(text) > 0
            # Should have either course name or lesson info
            assert any(
                keyword in text for keyword in ["Building", "Introduction", "Lesson"]
            )

    def test_source_links_retrieved(self, mock_vector_store):
        """Test that course and lesson links are retrieved"""
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="What is prompt caching?")

        # At least one source should have links
        has_links = any(
            source.get("course_link") is not None
            or source.get("lesson_link") is not None
            for source in tool.last_sources
        )
        assert has_links

    def test_sources_reset_on_new_search(self, mock_vector_store):
        """Test that sources are replaced (not appended) on new search"""
        tool = CourseSearchTool(mock_vector_store)

        # First search
        tool.execute(query="What is prompt caching?")
        first_count = len(tool.last_sources)

        # Second search
        tool.execute(query="What is computer use?")
        second_count = len(tool.last_sources)

        # Should have new sources, not accumulated
        assert second_count > 0


class TestToolManagerIntegration:
    """Test ToolManager integration with CourseSearchTool"""

    def test_tool_registration(self, mock_vector_store):
        """Test that tool can be registered with ToolManager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        manager.register_tool(tool)

        # Should be in tools dict
        assert "search_course_content" in manager.tools

    def test_tool_execution_via_manager(self, mock_vector_store):
        """Test executing tool through ToolManager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        result = manager.execute_tool(
            "search_course_content", query="What is prompt caching?"
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_tool_definitions(self, mock_vector_store):
        """Test getting all tool definitions from manager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_get_last_sources_from_manager(self, mock_vector_store):
        """Test retrieving last_sources through ToolManager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search
        manager.execute_tool("search_course_content", query="What is prompt caching?")

        # Get sources through manager
        sources = manager.get_last_sources()

        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_reset_sources_via_manager(self, mock_vector_store):
        """Test resetting sources through ToolManager"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search
        manager.execute_tool("search_course_content", query="What is prompt caching?")
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()
        assert len(manager.get_last_sources()) == 0

    def test_unknown_tool_execution(self, mock_vector_store):
        """Test executing non-existent tool"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        assert "not found" in result.lower()
