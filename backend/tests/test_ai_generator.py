"""
Unit tests for AIGenerator in ai_generator.py
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_generator import AIGenerator


class TestAIGeneratorInitialization:
    """Test AIGenerator initialization"""

    def test_initialization(self, test_config):
        """Test AIGenerator initializes correctly"""
        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        assert generator.model == test_config.ANTHROPIC_MODEL
        assert generator.base_params["model"] == test_config.ANTHROPIC_MODEL
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 1200

    def test_base_params_structure(self, test_config):
        """Test that base_params has correct structure"""
        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        assert "model" in generator.base_params
        assert "temperature" in generator.base_params
        assert "max_tokens" in generator.base_params


class TestGenerateResponseWithoutTools:
    """Test response generation without tool use"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_simple_response(
        self, mock_anthropic_class, test_config, mock_anthropic_response_no_tool
    ):
        """Test generating a response without tools"""
        # Setup mock client
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        response = generator.generate_response(query="What is 2+2?")

        assert isinstance(response, str)
        assert len(response) > 0
        assert response == "This is a direct response without using any tools."

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_no_history(
        self, mock_anthropic_class, test_config, mock_anthropic_response_no_tool
    ):
        """Test response without conversation history"""
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        response = generator.generate_response(query="Hello", conversation_history=None)

        # Check that API was called correctly
        call_args = mock_client.messages.create.call_args
        assert call_args is not None

        # System prompt should not include conversation history
        system_content = call_args.kwargs["system"]
        assert "Previous conversation:" not in system_content

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_history(
        self, mock_anthropic_class, test_config, mock_anthropic_response_no_tool
    ):
        """Test response with conversation history"""
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        history = "User: What is AI?\nAssistant: AI is artificial intelligence..."

        response = generator.generate_response(
            query="Tell me more", conversation_history=history
        )

        # Check that history was included
        call_args = mock_client.messages.create.call_args
        system_content = call_args.kwargs["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content


class TestGenerateResponseWithTools:
    """Test response generation with tool use"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_tools_no_use(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_no_tool,
        mock_tool_manager,
    ):
        """Test that tools are provided but not used"""
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="What is 2+2?", tools=tools, tool_manager=mock_tool_manager
        )

        # Should return direct response
        assert isinstance(response, str)
        assert response == "This is a direct response without using any tools."

        # Tools should be included in API call
        call_args = mock_client.messages.create.call_args
        assert "tools" in call_args.kwargs
        assert "tool_choice" in call_args.kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_triggers_tool_use(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response,
        mock_tool_manager,
    ):
        """Test that Claude decides to use a tool"""
        mock_client = Mock()

        # First call returns tool use, second call returns final response
        mock_client.messages.create = Mock(
            side_effect=[
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response,
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="What is prompt caching?", tools=tools, tool_manager=mock_tool_manager
        )

        # Should have made TWO API calls
        assert mock_client.messages.create.call_count == 2

        # Should return the final synthesized response
        assert isinstance(response, str)
        assert "Prompt caching" in response

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_choice_auto_when_tools_provided(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_no_tool,
        mock_tool_manager,
    ):
        """Test that tool_choice is set to auto when tools are provided"""
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        generator.generate_response(
            query="Test", tools=tools, tool_manager=mock_tool_manager
        )

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["tool_choice"] == {"type": "auto"}


class TestHandleToolExecution:
    """Test the _handle_tool_execution method"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_flow(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response,
        mock_tool_manager,
    ):
        """Test complete tool execution flow"""
        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response,
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="What is prompt caching?", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        # The mock_tool_manager should have executed the search_course_content tool
        assert isinstance(response, str)

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_results_added_to_messages(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response,
        mock_tool_manager,
    ):
        """Test that tool results are correctly added to message history"""
        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response,
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="What is prompt caching?", tools=tools, tool_manager=mock_tool_manager
        )

        # Second API call should include tool results
        second_call = mock_client.messages.create.call_args_list[1]
        messages = second_call.kwargs["messages"]

        # Should have 3 messages: user query, assistant tool use, user tool result
        assert len(messages) == 3

        # Third message should be tool results
        assert messages[2]["role"] == "user"
        assert isinstance(messages[2]["content"], list)
        assert messages[2]["content"][0]["type"] == "tool_result"

    @patch("ai_generator.anthropic.Anthropic")
    def test_tools_available_until_max_rounds(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_response_with_tool,
        mock_anthropic_final_response,
        mock_tool_manager,
    ):
        """Test that tools remain available until max rounds is reached"""
        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[
                mock_anthropic_response_with_tool,
                mock_anthropic_final_response,
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="What is prompt caching?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Both calls should have tools (within max_rounds)
        first_call = mock_client.messages.create.call_args_list[0]
        assert "tools" in first_call.kwargs

        second_call = mock_client.messages.create.call_args_list[1]
        assert "tools" in second_call.kwargs  # CHANGED: tools now available

    @patch("ai_generator.anthropic.Anthropic")
    def test_multiple_tool_calls_in_response(
        self,
        mock_anthropic_class,
        test_config,
        mock_anthropic_final_response,
        mock_tool_manager,
    ):
        """Test handling of multiple tool calls in single response"""
        # Create response with multiple tool uses
        mock_response = Mock()
        mock_response.stop_reason = "tool_use"

        mock_tool_use_1 = Mock()
        mock_tool_use_1.type = "tool_use"
        mock_tool_use_1.name = "search_course_content"
        mock_tool_use_1.id = "tool_1"
        mock_tool_use_1.input = {"query": "prompt caching"}

        mock_tool_use_2 = Mock()
        mock_tool_use_2.type = "tool_use"
        mock_tool_use_2.name = "search_course_content"
        mock_tool_use_2.id = "tool_2"
        mock_tool_use_2.input = {"query": "computer use"}

        mock_response.content = [mock_tool_use_1, mock_tool_use_2]

        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[mock_response, mock_anthropic_final_response]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()

        response = generator.generate_response(
            query="Tell me about caching and computer use",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Should handle both tool calls
        assert isinstance(response, str)

        # Check that tool results message has both results
        second_call = mock_client.messages.create.call_args_list[1]
        tool_results = second_call.kwargs["messages"][2]["content"]
        assert len(tool_results) == 2


class TestSystemPrompt:
    """Test system prompt construction"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_system_prompt_includes_base_instructions(
        self, mock_anthropic_class, test_config, mock_anthropic_response_no_tool
    ):
        """Test that system prompt contains base instructions"""
        mock_client = Mock()
        mock_client.messages.create = Mock(return_value=mock_anthropic_response_no_tool)
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        generator.generate_response(query="Test")

        call_args = mock_client.messages.create.call_args
        system_content = call_args.kwargs["system"]

        # Should include key parts of system prompt
        assert "course materials" in system_content.lower()
        assert "tool" in system_content.lower()

    def test_system_prompt_static(self, test_config):
        """Test that SYSTEM_PROMPT is a class variable"""
        assert hasattr(AIGenerator, "SYSTEM_PROMPT")
        assert isinstance(AIGenerator.SYSTEM_PROMPT, str)
        assert len(AIGenerator.SYSTEM_PROMPT) > 0


class TestSequentialToolCalling:
    """Test multiple rounds of tool calling"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_sequential_tool_calls(
        self, mock_anthropic_class, test_config, mock_tool_manager
    ):
        """Test that Claude can make 2 sequential tool calls"""
        from conftest import create_mock_tool_use

        # First API call: Claude uses tool for "prompt caching"
        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [
            create_mock_tool_use(
                "search_course_content", {"query": "prompt caching"}, "tool_1"
            )
        ]

        # Second API call: Claude uses tool for "computer use"
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "tool_use"
        mock_response_2.content = [
            create_mock_tool_use(
                "search_course_content", {"query": "computer use"}, "tool_2"
            )
        ]

        # Third API call: Final answer
        mock_response_3 = Mock()
        mock_response_3.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = (
            "Both prompt caching and computer use are powerful features."
        )
        mock_response_3.content = [mock_content]

        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[mock_response_1, mock_response_2, mock_response_3]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()
        response = generator.generate_response(
            query="Compare prompt caching and computer use",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Should make 3 API calls total
        assert mock_client.messages.create.call_count == 3

        # First two calls should have tools
        first_call = mock_client.messages.create.call_args_list[0]
        assert "tools" in first_call.kwargs

        second_call = mock_client.messages.create.call_args_list[1]
        assert "tools" in second_call.kwargs

        # Should return final text
        assert "Both" in response
        assert isinstance(response, str)

    @patch("ai_generator.anthropic.Anthropic")
    def test_max_rounds_limit_enforced(
        self, mock_anthropic_class, test_config, mock_tool_manager
    ):
        """Test that tool execution stops at max_rounds"""
        from conftest import create_mock_tool_use

        # Create responses where Claude wants to use tools 3 times
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [
            create_mock_tool_use(
                "search_course_content", {"query": "test"}, "tool_test"
            )
        ]

        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Final response after max rounds"
        mock_final_response.content = [mock_content]

        mock_client = Mock()
        # Claude tries to use tools 3 times, but we limit to 2
        mock_client.messages.create = Mock(
            side_effect=[
                mock_tool_response,  # Round 1
                mock_tool_response,  # Round 2
                mock_final_response,  # Forced synthesis
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()
        response = generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Should make exactly 3 calls (2 rounds + final synthesis)
        assert mock_client.messages.create.call_count == 3

        # Should return final text
        assert "Final response" in response

    @patch("ai_generator.anthropic.Anthropic")
    def test_early_termination_on_final_response(
        self, mock_anthropic_class, test_config, mock_tool_manager
    ):
        """Test that loop stops early if Claude returns final response"""
        from conftest import create_mock_tool_use

        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [
            create_mock_tool_use("search_course_content", {"query": "test"}, "tool_1")
        ]

        mock_final_response = Mock()
        mock_final_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Final response after one round"
        mock_final_response.content = [mock_content]

        mock_client = Mock()
        # Claude finishes after 1 round
        mock_client.messages.create = Mock(
            side_effect=[
                mock_tool_response,  # Round 1
                mock_final_response,  # Finished early
            ]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()
        response = generator.generate_response(
            query="Test query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,  # Allow 2, but Claude only uses 1
        )

        # Should make only 2 calls (Claude finished early)
        assert mock_client.messages.create.call_count == 2
        assert "Final response after one round" in response

    @patch("ai_generator.anthropic.Anthropic")
    def test_message_history_accumulates_correctly(
        self, mock_anthropic_class, test_config, mock_tool_manager
    ):
        """Test that message history includes all tool uses and results"""
        from conftest import create_mock_tool_use

        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_response_1.content = [
            create_mock_tool_use("search_course_content", {"query": "first"}, "tool_1")
        ]

        mock_response_2 = Mock()
        mock_response_2.stop_reason = "tool_use"
        mock_response_2.content = [
            create_mock_tool_use("search_course_content", {"query": "second"}, "tool_2")
        ]

        mock_final = Mock()
        mock_final.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.type = "text"
        mock_content.text = "Done"
        mock_final.content = [mock_content]

        mock_client = Mock()
        mock_client.messages.create = Mock(
            side_effect=[mock_response_1, mock_response_2, mock_final]
        )
        mock_anthropic_class.return_value = mock_client

        generator = AIGenerator(
            api_key=test_config.ANTHROPIC_API_KEY, model=test_config.ANTHROPIC_MODEL
        )

        tools = mock_tool_manager.get_tool_definitions()
        generator.generate_response(
            query="Test", tools=tools, tool_manager=mock_tool_manager, max_rounds=2
        )

        # Check final API call has correct message structure
        final_call = mock_client.messages.create.call_args_list[2]
        messages = final_call.kwargs["messages"]

        # Should have: [user query, assistant tool_use, user tool_result,
        #               assistant tool_use, user tool_result]
        assert len(messages) == 5
        assert messages[0]["role"] == "user"  # Original query
        assert messages[1]["role"] == "assistant"  # First tool use
        assert messages[2]["role"] == "user"  # First tool result
        assert messages[3]["role"] == "assistant"  # Second tool use
        assert messages[4]["role"] == "user"  # Second tool result
