# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **RAG (Retrieval-Augmented Generation) Chatbot System** for querying course materials. It combines semantic search (ChromaDB) with AI generation (Anthropic Claude) to answer questions about educational content.

**Tech Stack:**
- Backend: FastAPI + Python 3.13
- Vector DB: ChromaDB with sentence-transformers embeddings
- AI: Anthropic Claude (Sonnet 4) with tool use
- Frontend: Vanilla JavaScript (no framework)
- Package Manager: uv

## Development Commands

### Running the Application

```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points:
# - Web UI: http://localhost:8000
# - API docs: http://localhost:8000/docs
```

### Environment Setup

```bash
# Install dependencies
uv sync

# Create .env file with:
ANTHROPIC_API_KEY=your_key_here
```

### Working with the Vector Database

The ChromaDB database is stored in `backend/chroma_db/`. To rebuild or clear it:

```python
# In Python REPL or script:
from rag_system import RAGSystem
from config import config

rag = RAGSystem(config)
# Clear and rebuild from docs/ folder:
rag.add_course_folder("../docs", clear_existing=True)
```

## Architecture

### Request Flow: User Query → AI Response

```
Frontend (script.js)
  ↓ POST /api/query
FastAPI (app.py)
  ↓ rag_system.query()
RAGSystem (rag_system.py)
  ├→ SessionManager: Retrieve conversation history
  ↓ ai_generator.generate_response()
AIGenerator (ai_generator.py)
  ↓ Call Claude API with tools
Claude decides to use search_course_content tool
  ↓ tool_manager.execute_tool()
CourseSearchTool (search_tools.py)
  ↓ vector_store.search()
VectorStore (vector_store.py)
  ↓ ChromaDB semantic search
Returns top 5 relevant chunks
  ↑ Formatted results back to Claude
Claude synthesizes final answer (2nd API call)
  ↑ Response + sources
RAGSystem saves to session history
  ↑ Return to FastAPI
Frontend displays answer with sources
```

### Key Architectural Patterns

**1. Tool-Based AI Agent Pattern**
- Claude is given a `search_course_content` tool definition
- Claude autonomously decides when to search
- Tool execution happens via `ToolManager` → `CourseSearchTool` → `VectorStore`
- Second API call synthesizes final answer from search results

**2. Dual Vector Collections**
- `course_catalog`: Course metadata (titles, instructors, links) for fuzzy course name matching
- `course_content`: Chunked text content with embeddings for semantic search

**3. Document Processing Pipeline**
- Sentence-aware chunking (800 chars with 100 char overlap)
- Contextual enhancement: First chunk gets "Course X Lesson N content: ..." prefix
- Metadata preservation: Each chunk tracks `course_title`, `lesson_number`, `chunk_index`

**4. Session-Based Conversations**
- Each user gets a `session_id`
- Conversation history limited to `MAX_HISTORY` exchanges (default: 2)
- History injected into system prompt for context

### Component Responsibilities

**app.py** - FastAPI application layer
- Endpoints: `/api/query`, `/api/courses`
- Startup: Auto-loads documents from `../docs/` folder
- Serves static frontend files

**rag_system.py** - Main orchestrator
- Coordinates all components (document processor, vector store, AI generator, session manager)
- `query()`: Main entry point for processing user queries
- `add_course_folder()`: Batch document ingestion with deduplication

**ai_generator.py** - Claude API wrapper
- Handles tool execution flow (initial call → tool execution → synthesis call)
- System prompt emphasizes concise, educational responses
- Temperature: 0, Max tokens: 800

**vector_store.py** - ChromaDB interface
- `search()`: Unified search with optional course/lesson filtering
- `_resolve_course_name()`: Fuzzy course name matching via semantic search on catalog
- Embedding model: `all-MiniLM-L6-v2` (384 dimensions)

**search_tools.py** - Tool definitions and execution
- `CourseSearchTool`: Implements Tool interface for Claude
- `ToolManager`: Registry pattern for multiple tools
- Tracks sources for UI display (`last_sources`)

**document_processor.py** - Course file parsing
- Expected format: Course metadata → Lesson markers → Content
- Regex-based lesson detection: `r'^Lesson\s+(\d+):\s*(.+)$'`
- Sentence-aware chunking preserves semantic boundaries

**session_manager.py** - Conversation state
- In-memory session storage (dict-based)
- Auto-truncates history to prevent context overflow
- Returns formatted history: "User: ...\nAssistant: ..."

### Configuration (backend/config.py)

All settings are centralized in a dataclass:
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2"
- `CHUNK_SIZE`: 800 chars
- `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 search results
- `MAX_HISTORY`: 2 conversation exchanges
- `CHROMA_PATH`: "./chroma_db"

## Document Format Requirements

Course files in `docs/` must follow this structure:

```
Course Title: [Title]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Lesson Title]
Lesson Link: [URL]
[Lesson content...]

Lesson 1: [Next Lesson]
Lesson Link: [URL]
[More content...]
```

The parser is flexible:
- Lines 1-3: Course metadata (regex-based extraction)
- `Lesson N:` markers: Lesson boundaries
- Optional `Lesson Link:` on next line after lesson marker
- All content between markers becomes lesson text

## Key Implementation Details

### Why Two Claude API Calls?
1. **First call**: Claude decides to use `search_course_content` tool (stop_reason="tool_use")
2. Tool execution happens in backend
3. **Second call**: Claude synthesizes answer from search results (tools removed from request)

This pattern enables agentic behavior where Claude controls when to search.

### ChromaDB Filter Syntax
```python
# Course only:
{"course_title": "Building Towards Computer Use..."}

# Lesson only:
{"lesson_number": 5}

# Both (AND):
{"$and": [
    {"course_title": "..."},
    {"lesson_number": 5}
]}
```

### Session History Format
Stored as `Message` dataclasses, returned as formatted string:
```
User: What is computer use?
Assistant: Computer use is Claude's ability...
User: What is prompt caching?
```

### Frontend-Backend Contract

**Request:**
```json
POST /api/query
{
  "query": "What is prompt caching?",
  "session_id": "session_1"  // optional, created if null
}
```

**Response:**
```json
{
  "answer": "Prompt caching is a feature...",
  "sources": ["Building Towards Computer Use - Lesson 5"],
  "session_id": "session_1"
}
```

## Extending the System

### Adding a New Tool

1. Create tool class inheriting from `Tool` in `search_tools.py`:
```python
class MyNewTool(Tool):
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "my_tool",
            "description": "What the tool does",
            "input_schema": {...}
        }

    def execute(self, **kwargs) -> str:
        # Tool logic here
        return "Tool result"
```

2. Register in `rag_system.py`:
```python
self.my_tool = MyNewTool()
self.tool_manager.register_tool(self.my_tool)
```

### Modifying Search Behavior

Search logic is in `vector_store.py`:
- Change `MAX_RESULTS` in config to return more/fewer chunks
- Modify `_build_filter()` to add new filter types
- Adjust similarity threshold by examining `distances` in results

### Adjusting AI Responses

System prompt is in `ai_generator.py` (line 8-30):
- Current emphasis: Brief, concise, educational
- Tool usage policy: One search per query maximum
- Response protocol: No meta-commentary about search process

## Troubleshooting

**ChromaDB warnings about resource_tracker:**
Suppressed in `app.py` line 1-2. These are harmless multiprocessing warnings.

**Documents not loading:**
Check `startup_event()` in `app.py`. Path is `../docs` relative to backend directory.

**Vector search returns no results:**
Course name matching uses semantic search. Try partial names (e.g., "computer use" instead of full title).

**Session history not working:**
Sessions are in-memory only. Server restart clears all sessions.
- always use uv to run the serverdo not use pip directly
- make sure to use uv to manage all dependencies
- use uv to run all python files