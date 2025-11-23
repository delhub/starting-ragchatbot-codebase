"""
Integration tests for RAGSystem in rag_system.py
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag_system import RAGSystem


class TestRAGSystemInitialization:
    """Test RAG system initialization"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_initialization_creates_components(
        self, mock_session, mock_doc_proc, mock_vector_store, mock_ai_gen, test_config
    ):
        """Test that all components are initialized"""
        rag = RAGSystem(test_config)

        # Check that all components exist
        assert hasattr(rag, "document_processor")
        assert hasattr(rag, "vector_store")
        assert hasattr(rag, "ai_generator")
        assert hasattr(rag, "session_manager")
        assert hasattr(rag, "tool_manager")
        assert hasattr(rag, "search_tool")
        assert hasattr(rag, "outline_tool")

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_tools_registered(
        self, mock_session, mock_doc_proc, mock_vector_store, mock_ai_gen, test_config
    ):
        """Test that tools are registered with tool manager"""
        rag = RAGSystem(test_config)

        # Tool manager should have tools
        tool_defs = rag.tool_manager.get_tool_definitions()
        assert len(tool_defs) >= 2  # At least search and outline tools

        # Check tool names
        tool_names = [tool["name"] for tool in tool_defs]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names


class TestRAGSystemQuery:
    """Test query processing"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_without_session(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test query without session ID"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="This is the AI response"
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query
        response, sources = rag.query("What is AI?")

        # Should return response
        assert isinstance(response, str)
        assert len(response) > 0

        # Should not try to get history
        mock_session_instance.get_conversation_history.assert_not_called()

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_with_session(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test query with session ID"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="This is the AI response"
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(
            return_value="User: Previous question\nAssistant: Previous answer"
        )
        mock_session_instance.add_exchange = Mock()
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query with session
        response, sources = rag.query("What is AI?", session_id="test_session")

        # Should get history
        mock_session_instance.get_conversation_history.assert_called_once_with(
            "test_session"
        )

        # Should add exchange
        mock_session_instance.add_exchange.assert_called_once()

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_passes_tools_to_ai(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that tools are passed to AI generator"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="AI response")
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query
        response, sources = rag.query("What is prompt caching?")

        # Check that generate_response was called with tools
        mock_ai_instance.generate_response.assert_called_once()
        call_kwargs = mock_ai_instance.generate_response.call_args.kwargs

        assert "tools" in call_kwargs
        assert "tool_manager" in call_kwargs
        assert isinstance(call_kwargs["tools"], list)
        assert len(call_kwargs["tools"]) >= 2

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_retrieves_sources(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that sources are retrieved from tool manager"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="AI response about prompt caching"
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Manually set sources in tool manager (simulating a search)
        rag.tool_manager.tools["search_course_content"].last_sources = [
            {
                "text": "Course A - Lesson 1",
                "course_link": "http://test.com",
                "lesson_link": "http://test.com/1",
            }
        ]

        # Execute query
        response, sources = rag.query("What is prompt caching?")

        # Should return sources
        assert isinstance(sources, list)
        assert len(sources) > 0

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_resets_sources_after_retrieval(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that sources are reset after being retrieved"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="AI response")
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Set sources
        rag.tool_manager.tools["search_course_content"].last_sources = [
            {"text": "Source 1", "course_link": None, "lesson_link": None}
        ]

        # Execute query
        response, sources = rag.query("Test")

        # Sources should be reset after query
        new_sources = rag.tool_manager.get_last_sources()
        assert len(new_sources) == 0

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_formats_prompt_correctly(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that query is formatted correctly for AI"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="AI response")
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query
        user_query = "What is prompt caching?"
        response, sources = rag.query(user_query)

        # Check the prompt passed to AI
        call_kwargs = mock_ai_instance.generate_response.call_args.kwargs
        assert "query" in call_kwargs
        assert user_query in call_kwargs["query"]
        assert "course materials" in call_kwargs["query"]


class TestRAGSystemWithRealToolExecution:
    """Test RAG system with actual tool execution (mocked vector store)"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_executes_search_tool(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_ai_gen_class,
        test_config,
        mock_vector_store,
    ):
        """Test that search tool is actually executed"""
        # Setup AI to trigger tool use
        mock_tool_use_response = Mock()
        mock_tool_use_response.stop_reason = "tool_use"

        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {
            "query": "prompt caching",
            "course_name": None,
            "lesson_number": None,
        }
        mock_tool_use_response.content = [mock_tool_block]

        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_final_content = Mock()
        mock_final_content.text = "Prompt caching is a feature..."
        mock_final_content.type = "text"
        mock_final_response.content = [mock_final_content]

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="Final response about prompt caching"
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_instance.add_exchange = Mock()
        mock_session_class.return_value = mock_session_instance

        # Patch VectorStore to use our mock
        with patch("rag_system.VectorStore", return_value=mock_vector_store):
            rag = RAGSystem(test_config)

            # Execute query
            response, sources = rag.query("What is prompt caching?")

            # Should have called vector store search
            mock_vector_store.search.assert_called()

            # Should have sources
            assert isinstance(sources, list)

    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_content_query_returns_results(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_ai_gen_class,
        test_config,
        mock_vector_store,
    ):
        """Test that content queries return results with sources"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="Prompt caching allows you to cache context..."
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_instance.add_exchange = Mock()
        mock_session_class.return_value = mock_session_instance

        with patch("rag_system.VectorStore", return_value=mock_vector_store):
            rag = RAGSystem(test_config)

            # Manually execute search to populate sources
            rag.search_tool.execute(query="prompt caching")

            # Execute query
            response, sources = rag.query("What is prompt caching?")

            # Should have response and sources
            assert isinstance(response, str)
            assert len(response) > 0
            assert isinstance(sources, list)


class TestRAGSystemErrorHandling:
    """Test error handling in RAG system"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_handles_ai_errors(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that AI errors are propagated"""
        # Setup AI to raise error
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            side_effect=Exception("API Error: Invalid API key")
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query - should raise exception
        with pytest.raises(Exception) as exc_info:
            rag.query("What is AI?")

        assert "API Error" in str(exc_info.value)

    @patch("rag_system.AIGenerator")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_query_handles_vector_store_errors(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_ai_gen_class,
        test_config,
        mock_vector_store,
    ):
        """Test handling of vector store errors"""
        # Setup vector store to return error
        from vector_store import SearchResults

        # Configure mock to return error
        mock_vector_store.search = Mock(
            return_value=SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                error="Vector store connection error",
            )
        )

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(
            return_value="I couldn't search the database"
        )
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_class.return_value = mock_session_instance

        with patch("rag_system.VectorStore", return_value=mock_vector_store):
            rag = RAGSystem(test_config)

            # Execute search manually to trigger error
            result = rag.search_tool.execute(query="test")

            # Should return error message
            assert "error" in result.lower()


class TestRAGSystemConversationHistory:
    """Test conversation history management"""

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_history_passed_to_ai_generator(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that conversation history is passed to AI"""
        # Setup mocks
        test_history = "User: What is AI?\nAssistant: AI is artificial intelligence."

        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="Follow-up response")
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=test_history)
        mock_session_instance.add_exchange = Mock()
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        # Execute query with session
        response, sources = rag.query("Tell me more", session_id="session_123")

        # Check that history was passed
        call_kwargs = mock_ai_instance.generate_response.call_args.kwargs
        assert call_kwargs["conversation_history"] == test_history

    @patch("rag_system.AIGenerator")
    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    @patch("rag_system.SessionManager")
    def test_new_exchange_added_to_history(
        self,
        mock_session_class,
        mock_doc_proc,
        mock_vector_store,
        mock_ai_gen_class,
        test_config,
    ):
        """Test that new exchanges are added to session"""
        # Setup mocks
        mock_ai_instance = Mock()
        mock_ai_instance.generate_response = Mock(return_value="AI response")
        mock_ai_gen_class.return_value = mock_ai_instance

        mock_session_instance = Mock()
        mock_session_instance.get_conversation_history = Mock(return_value=None)
        mock_session_instance.add_exchange = Mock()
        mock_session_class.return_value = mock_session_instance

        rag = RAGSystem(test_config)

        query_text = "What is prompt caching?"
        response, sources = rag.query(query_text, session_id="session_123")

        # Should add exchange with original query (not formatted prompt)
        mock_session_instance.add_exchange.assert_called_once()
        call_args = mock_session_instance.add_exchange.call_args[0]
        assert call_args[0] == "session_123"
        assert call_args[1] == query_text  # Original query
        assert call_args[2] == "AI response"
