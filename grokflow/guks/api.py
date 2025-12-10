"""
GUKS REST API for IDE Integration

Provides fast HTTP endpoints for:
  - Pattern querying (<100ms)
  - Fix recording
  - Statistics and analytics
  - Team sync (future)

Run standalone:
    python -m grokflow.guks.api

Or integrate into GrokFlow CLI (starts automatically in background)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uvicorn
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from grokflow.guks.embeddings import EnhancedGUKS

# Initialize FastAPI app
app = FastAPI(
    title="GrokFlow GUKS API",
    description="Universal Knowledge System for cross-project learning",
    version="1.0.0"
)

# Enable CORS for IDE extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global GUKS instance
guks_instance: Optional[EnhancedGUKS] = None


def get_guks() -> EnhancedGUKS:
    """Get or initialize GUKS instance"""
    global guks_instance
    if guks_instance is None:
        guks_instance = EnhancedGUKS()
    return guks_instance


# Request/Response Models

class GUKSQuery(BaseModel):
    """Query request"""
    code: str = Field(..., description="Code snippet or query text")
    error: Optional[str] = Field(None, description="Error message")
    file_type: Optional[str] = Field(None, description="File extension (py, js, ts, etc.)")
    project: Optional[str] = Field(None, description="Project name for context filtering")
    scope: str = Field("local", description="Query scope: local, team, or global")


class GUKSPattern(BaseModel):
    """GUKS pattern"""
    error: str
    fix: str
    file: str
    project: str
    timestamp: str
    similarity: Optional[float] = None
    score: Optional[float] = None


class GUKSRecordRequest(BaseModel):
    """Record fix request"""
    error: str
    fix: str
    file: str
    project: str
    context: Optional[Dict] = None


class GUKSCompletionRequest(BaseModel):
    """Completion request"""
    prefix: str = Field(..., description="Code before cursor")
    suffix: str = Field("", description="Code after cursor")
    file_type: str = Field(..., description="File extension")


# API Endpoints

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "GrokFlow GUKS API",
        "version": "1.0.0"
    }


@app.post("/api/guks/query", response_model=List[GUKSPattern])
async def query_guks(query: GUKSQuery):
    """
    Query GUKS for relevant patterns

    Fast semantic search across all recorded fixes.
    Typical response time: <100ms

    Scope:
      - local: Only patterns from this machine
      - team: Patterns from team members (requires auth) - TODO
      - global: Anonymous patterns from community (opt-in) - TODO
    """
    try:
        guks = get_guks()

        # Build context
        context = {}
        if query.file_type:
            context['file_type'] = query.file_type
        if query.project:
            context['project'] = query.project

        # Query GUKS
        results = guks.query(
            code=query.code,
            error=query.error,
            context=context if context else None
        )

        # TODO: Filter by scope (team/global)
        if query.scope == "team":
            # Future: Query team database
            pass
        elif query.scope == "global":
            # Future: Query global knowledge pool
            pass

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guks/record")
async def record_fix(
    pattern: GUKSRecordRequest,
    background_tasks: BackgroundTasks
):
    """
    Record a successful fix in GUKS

    Runs index rebuild in background for zero latency.
    """
    try:
        guks = get_guks()

        # Build pattern dict
        pattern_dict = {
            'error': pattern.error,
            'fix': pattern.fix,
            'file': pattern.file,
            'project': pattern.project,
            'context': pattern.context or {}
        }

        # Record in background
        background_tasks.add_task(guks.record_fix, pattern_dict)

        return {
            "status": "recorded",
            "message": "Pattern recorded successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guks/stats")
async def get_stats():
    """Get GUKS statistics"""
    try:
        guks = get_guks()
        stats = guks.embedding_engine.get_stats()

        return {
            **stats,
            "total_patterns": len(guks.patterns),
            "projects": len(set(p.get('project', 'unknown') for p in guks.patterns)),
            "oldest_pattern": min(
                (p.get('timestamp', '') for p in guks.patterns),
                default=None
            ),
            "newest_pattern": max(
                (p.get('timestamp', '') for p in guks.patterns),
                default=None
            )
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guks/complete")
async def get_completion(request: GUKSCompletionRequest):
    """
    GUKS-powered code completion

    Returns completion based on team's patterns.
    Fallback to model-based completion if no GUKS patterns found.

    Target latency: <200ms for real-time autocomplete
    """
    try:
        guks = get_guks()

        # Extract context from prefix
        # TODO: Implement GUKSCompletionEngine
        # For now, return empty (fallback to model)

        return {
            "completion": "",
            "source": "none",
            "message": "Completion engine not yet implemented"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/guks/patterns")
async def list_patterns(
    project: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    List GUKS patterns with pagination

    Useful for debugging and analytics
    """
    try:
        guks = get_guks()
        patterns = guks.patterns

        # Filter by project
        if project:
            patterns = [p for p in patterns if p.get('project') == project]

        # Sort by timestamp (newest first)
        patterns = sorted(
            patterns,
            key=lambda p: p.get('timestamp', ''),
            reverse=True
        )

        # Paginate
        total = len(patterns)
        patterns = patterns[offset:offset+limit]

        return {
            "patterns": patterns,
            "total": total,
            "offset": offset,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/guks/analytics/completion-accepted")
async def track_completion_accepted(data: Dict):
    """Track autocomplete acceptance for analytics"""
    # TODO: Implement analytics tracking
    return {"status": "tracked"}


# Startup/Shutdown Events

@app.on_event("startup")
async def startup_event():
    """Initialize GUKS on startup"""
    global guks_instance
    guks_instance = EnhancedGUKS()
    print("✅ GUKS API started")
    print(f"📊 Loaded {len(guks_instance.patterns)} patterns")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 GUKS API shutting down")


# Main entry point

def start_guks_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    log_level: str = "info"
):
    """
    Start GUKS API server

    Args:
        host: Server host (default: localhost only)
        port: Server port (default: 8765)
        log_level: Logging level (default: info)
    """
    print(f"""
╭─────────────────────────────────────────────────────╮
│  GrokFlow GUKS API Server                          │
│                                                     │
│  Endpoint: http://{host}:{port}                │
│  Docs:     http://{host}:{port}/docs           │
│                                                     │
│  Ready for IDE integration                          │
╰─────────────────────────────────────────────────────╯
    """)

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level
    )


if __name__ == "__main__":
    # Run server
    start_guks_server()
