from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Tool Usage:
- **get_course_outline**: Use for questions about course structure, syllabus, lesson lists, or course overview
  - Returns: course title, course link, and complete list of lessons (number and title)
  - When to use: "What's the outline?", "What lessons are included?", "Course structure?", "What's covered?"
- **search_course_content**: Use for questions about specific course content or detailed educational materials
  - Returns: relevant content chunks with context
  - When to use: Questions about specific concepts, topics, or lesson content
- **Multi-tool strategy**: You can make multiple tool calls across sequential rounds
  - Use multiple rounds when initial results need refinement or additional context
  - Useful for comparisons, multi-part questions, or gathering information from different courses/lessons
  - Each round allows you to reason about previous results before making the next tool call
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline/structure questions**: Use get_course_outline, then present the course title, course link, and all lessons
- **Course content questions**: Use search_course_content, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the tool results" or "I searched for"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 1200,  # Increased to handle complex multi-round responses
        }

    def _extract_text_from_response(self, response) -> str:
        """
        Safely extract text content from an Anthropic API response.

        Args:
            response: Anthropic API response object

        Returns:
            Extracted text string

        Raises:
            ValueError: If no text content found in response
        """
        # Check if content exists and is not empty
        if not hasattr(response, "content") or not response.content:
            raise ValueError("Response contains no content blocks")

        # Find first text block in content
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                if hasattr(block, "text"):
                    return block.text

        # No text block found - return informative error
        block_types = [getattr(block, "type", "unknown") for block in response.content]
        raise ValueError(
            f"No text content found in response. "
            f"Stop reason: {response.stop_reason}, "
            f"Content blocks: {block_types}"
        )

    def _build_system_content(self, conversation_history: Optional[str]) -> str:
        """
        Build system prompt with conversation history if provided.

        Args:
            conversation_history: Previous messages for context

        Returns:
            Complete system content string
        """
        if conversation_history:
            return f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
        return self.SYSTEM_PROMPT

    def _execute_tools(self, response, tool_manager) -> List[Dict]:
        """
        Execute all tools from a response containing tool_use blocks.

        Args:
            response: API response containing tool_use content blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dictionaries
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                except Exception as e:
                    tool_result = f"Error executing tool {content_block.name}: {str(e)}"

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result,
                    }
                )
        return tool_results

    def _final_synthesis(self, messages: List, system_content: str) -> str:
        """
        Make final API call without tools for response synthesis.
        If Claude returns empty response (wants more tools but can't use them),
        provides a fallback message.

        Args:
            messages: Complete message history including tool results
            system_content: System prompt content

        Returns:
            Final synthesized response text
        """
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        try:
            final_response = self.client.messages.create(**final_params)
            return self._extract_text_from_response(final_response)
        except ValueError as e:
            # Claude returned empty response or no text content
            # This happens when max_rounds is reached but Claude wants more tool calls
            print(f"Warning: Final synthesis returned no content: {e}")
            print("Falling back to summarizing available tool results")

            # Provide a fallback response based on the query
            return (
                "I've searched through the course materials but need more tool calls "
                "to fully answer your question. Please try asking a more specific question, "
                "or break your question into smaller parts."
            )

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with iterative tool usage support (up to max_rounds).

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum sequential tool calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content
        system_content = self._build_system_content(conversation_history)

        # Initialize messages list
        messages = [{"role": "user", "content": query}]

        # Iterative tool calling loop
        for round_num in range(1, max_rounds + 1):
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Make API call
            response = self.client.messages.create(**api_params)

            # Check if Claude used tools
            if response.stop_reason == "tool_use" and tool_manager:
                # Add Claude's tool use response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and get results
                tool_results = self._execute_tools(response, tool_manager)

                # Add tool results to messages
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                # Continue to next round if under max_rounds
                continue

            # No tool use - return final response
            return self._extract_text_from_response(response)

        # Max rounds reached - make final synthesis call without tools
        return self._final_synthesis(messages, system_content)
