"""
GUKS Embedding Engine for Semantic Search

Enables fast semantic similarity search across GUKS patterns using
sentence transformers and FAISS vector index.

Why: Keyword search misses similar patterns with different wording.
Example: "null pointer" vs "undefined is not a function" (same root cause)

Performance Target: <100ms queries for real-time IDE integration
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
import faiss
from pathlib import Path
import json
import pickle
from datetime import datetime


class GUKSEmbeddingEngine:
    """
    Semantic search for GUKS patterns using embeddings

    Architecture:
      - Sentence transformer: all-MiniLM-L6-v2 (384-dim, fast)
      - Vector index: FAISS (approximate nearest neighbors)
      - Similarity metric: Cosine similarity (via inner product)

    Performance:
      - Query: <100ms for 10k patterns
      - Index build: ~1s for 1k patterns
      - Memory: ~1.5MB per 1k patterns
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None
    ):
        """
        Initialize embedding engine

        Args:
            model_name: SentenceTransformer model (default: all-MiniLM-L6-v2)
            cache_dir: Directory to cache index (default: ~/.grokflow/guks/embeddings)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

        self.cache_dir = Path(cache_dir or "~/.grokflow/guks/embeddings").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.index: Optional[faiss.Index] = None
        self.patterns: List[Dict] = []
        self.dimension = 384  # all-MiniLM-L6-v2 dimension

    def build_index(self, guks_patterns: List[Dict]) -> None:
        """
        Build FAISS index from GUKS knowledge base

        Args:
            guks_patterns: List of GUKS patterns with 'error', 'fix', 'context'

        Example pattern:
            {
                'error': 'TypeError: Cannot read property "name" of undefined',
                'fix': 'Added null check: if (user) { user.name }',
                'file': 'api.js',
                'project': 'user-service',
                'timestamp': '2025-12-09T10:30:00'
            }
        """
        if not guks_patterns:
            print("Warning: No patterns to index")
            return

        # Extract text for embedding
        texts = []
        for p in guks_patterns:
            # Combine error, fix, and context for rich semantic matching
            text_parts = [
                p.get('error', ''),
                p.get('fix', ''),
                p.get('context', {}).get('description', ''),
                p.get('file', ''),  # File type helps with similarity
            ]
            text = ' '.join(filter(None, text_parts))
            texts.append(text)

        # Generate embeddings
        print(f"Generating embeddings for {len(texts)} patterns...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=len(texts) > 100,
            batch_size=32
        )

        # Build FAISS index
        print("Building FAISS index...")
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine sim)

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Add to index
        self.index.add(embeddings.astype('float32'))

        # Store patterns for retrieval
        self.patterns = guks_patterns

        print(f"✅ Index built: {len(self.patterns)} patterns indexed")

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.5
    ) -> List[Dict]:
        """
        Semantic search for similar GUKS patterns

        Args:
            query: Search query (error message, code snippet, etc.)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of patterns with similarity scores, sorted by relevance

        Example:
            >>> engine.search("TypeError: Cannot read property 'name'")
            [
                {
                    'error': 'TypeError: Cannot read property "email" of undefined',
                    'fix': 'Added null check',
                    'similarity': 0.87,
                    'project': 'auth-service'
                },
                ...
            ]
        """
        if self.index is None or not self.patterns:
            print("Warning: Index not built. Call build_index() first.")
            return []

        # Encode query
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)

        # Search
        scores, indices = self.index.search(
            query_embedding.astype('float32'),
            min(top_k, len(self.patterns))
        )

        # Build results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score >= min_similarity:
                pattern = self.patterns[idx].copy()
                pattern['similarity'] = float(score)
                results.append(pattern)

        return results

    def save_index(self, name: str = "default") -> None:
        """
        Save index to disk for fast loading

        Args:
            name: Index name (default: "default")
        """
        if self.index is None:
            print("Warning: No index to save")
            return

        index_dir = self.cache_dir / name
        index_dir.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        index_path = index_dir / "index.faiss"
        faiss.write_index(self.index, str(index_path))

        # Save patterns
        patterns_path = index_dir / "patterns.pkl"
        with open(patterns_path, 'wb') as f:
            pickle.dump(self.patterns, f)

        # Save metadata
        metadata = {
            'model_name': self.model_name,
            'num_patterns': len(self.patterns),
            'dimension': self.dimension,
            'created_at': datetime.now().isoformat()
        }
        metadata_path = index_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Index saved to {index_dir}")

    def load_index(self, name: str = "default") -> bool:
        """
        Load index from disk

        Args:
            name: Index name to load

        Returns:
            True if successful, False otherwise
        """
        index_dir = self.cache_dir / name

        if not index_dir.exists():
            print(f"Warning: Index '{name}' not found at {index_dir}")
            return False

        # Load FAISS index
        index_path = index_dir / "index.faiss"
        self.index = faiss.read_index(str(index_path))

        # Load patterns
        patterns_path = index_dir / "patterns.pkl"
        with open(patterns_path, 'rb') as f:
            self.patterns = pickle.load(f)

        # Load metadata
        metadata_path = index_dir / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        print(f"✅ Index loaded: {metadata['num_patterns']} patterns")
        return True

    def get_stats(self) -> Dict:
        """Get index statistics"""
        if self.index is None:
            return {'status': 'not_initialized'}

        return {
            'status': 'ready',
            'num_patterns': len(self.patterns),
            'dimension': self.dimension,
            'model': self.model_name,
            'index_type': 'FAISS IndexFlatIP (cosine similarity)'
        }


class EnhancedGUKS:
    """
    Enhanced GUKS with semantic search capabilities

    Combines:
      - Keyword search (existing GUKS)
      - Semantic search (embedding engine)
      - Context filtering (project, file type, etc.)

    Query strategy:
      1. Semantic search for top candidates
      2. Keyword boost for exact matches
      3. Context filter for relevance
      4. Merge and deduplicate
    """

    def __init__(self, data_dir: str = "~/.grokflow/guks"):
        """
        Initialize enhanced GUKS

        Args:
            data_dir: GUKS data directory
        """
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize embedding engine
        self.embedding_engine = GUKSEmbeddingEngine()

        # Load existing GUKS patterns
        self.patterns = self.load_patterns()

        # Build embedding index
        if self.patterns:
            # Try to load cached index first
            if not self.embedding_engine.load_index():
                # Build new index
                self.embedding_engine.build_index(self.patterns)
                self.embedding_engine.save_index()
        else:
            print("No GUKS patterns found. Index will be built when patterns are added.")

    def load_patterns(self) -> List[Dict]:
        """
        Load GUKS patterns from storage

        Returns:
            List of GUKS patterns
        """
        # TODO: Integration with existing GUKS storage
        # For now, create sample patterns for testing

        patterns_file = self.data_dir / "patterns.json"
        if patterns_file.exists():
            with open(patterns_file, 'r') as f:
                return json.load(f)
        else:
            # Create sample patterns for testing
            sample_patterns = [
                {
                    'error': 'TypeError: Cannot read property "name" of undefined',
                    'fix': 'Added null check: if (user) { user.name }',
                    'file': 'api.js',
                    'project': 'user-service',
                    'timestamp': '2025-11-15T10:30:00'
                },
                {
                    'error': 'NullPointerException in getUserProfile',
                    'fix': 'Added early return if user is null',
                    'file': 'UserController.java',
                    'project': 'auth-service',
                    'timestamp': '2025-11-20T14:20:00'
                },
                {
                    'error': 'UnhandledPromiseRejection in API call',
                    'fix': 'Added try-catch around async function',
                    'file': 'api.ts',
                    'project': 'frontend',
                    'timestamp': '2025-12-01T09:15:00'
                }
            ]
            # Save samples
            with open(patterns_file, 'w') as f:
                json.dump(sample_patterns, f, indent=2)
            return sample_patterns

    def query(
        self,
        code: str,
        error: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Enhanced query with semantic search

        Args:
            code: Code snippet or query text
            error: Error message (optional)
            context: Additional context (file_type, project, etc.)

        Returns:
            List of relevant patterns sorted by relevance
        """
        # Build query text
        query_text = f"{error or ''} {code}".strip()

        # Semantic search
        semantic_results = self.embedding_engine.search(
            query_text,
            top_k=10,
            min_similarity=0.5
        )

        # Keyword search (simple for now)
        keyword_results = self._keyword_search(code, error)

        # Merge results
        all_results = self._merge_results(semantic_results, keyword_results)

        # Filter by context
        if context:
            all_results = self._filter_by_context(all_results, context)

        return all_results[:5]  # Top 5

    def _keyword_search(
        self,
        code: str,
        error: Optional[str]
    ) -> List[Dict]:
        """
        Simple keyword search (fallback)

        TODO: Replace with existing GUKS keyword search
        """
        results = []
        query_words = set((error or '').lower().split() + code.lower().split())

        for pattern in self.patterns:
            pattern_words = set(
                pattern.get('error', '').lower().split() +
                pattern.get('fix', '').lower().split()
            )

            # Calculate keyword overlap
            overlap = len(query_words & pattern_words)
            if overlap > 0:
                pattern_copy = pattern.copy()
                pattern_copy['keyword_score'] = overlap / len(query_words)
                results.append(pattern_copy)

        return sorted(results, key=lambda x: x['keyword_score'], reverse=True)

    def _merge_results(
        self,
        semantic: List[Dict],
        keyword: List[Dict]
    ) -> List[Dict]:
        """
        Merge and deduplicate semantic + keyword results

        Strategy:
          - Semantic results get 70% weight
          - Keyword results get 30% weight
          - Deduplicate by pattern ID
        """
        merged = {}

        # Add semantic results
        for i, result in enumerate(semantic):
            pattern_id = result.get('file', '') + result.get('error', '')
            if pattern_id not in merged:
                result['score'] = result.get('similarity', 0) * 0.7
                merged[pattern_id] = result

        # Boost with keyword results
        for i, result in enumerate(keyword):
            pattern_id = result.get('file', '') + result.get('error', '')
            if pattern_id in merged:
                # Boost existing
                merged[pattern_id]['score'] += result.get('keyword_score', 0) * 0.3
            else:
                # Add new
                result['score'] = result.get('keyword_score', 0) * 0.3
                merged[pattern_id] = result

        # Sort by combined score
        return sorted(merged.values(), key=lambda x: x.get('score', 0), reverse=True)

    def _filter_by_context(
        self,
        results: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """
        Filter results by context (file_type, project, etc.)

        Boosts patterns from:
          - Same project (+0.2)
          - Same file type (+0.1)
        """
        filtered = []

        for result in results:
            # Apply boosts
            if context.get('project') == result.get('project'):
                result['score'] = result.get('score', 0) + 0.2

            file_ext = context.get('file_type', '')
            if file_ext and file_ext in result.get('file', ''):
                result['score'] = result.get('score', 0) + 0.1

            filtered.append(result)

        return sorted(filtered, key=lambda x: x.get('score', 0), reverse=True)

    def record_fix(self, pattern: Dict) -> None:
        """
        Record a new fix in GUKS

        Args:
            pattern: Pattern dict with error, fix, context
        """
        # Add timestamp
        pattern['timestamp'] = datetime.now().isoformat()

        # Add to patterns
        self.patterns.append(pattern)

        # Save to disk
        patterns_file = self.data_dir / "patterns.json"
        with open(patterns_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)

        # Rebuild index (incremental update in future)
        self.embedding_engine.build_index(self.patterns)
        self.embedding_engine.save_index()

        print(f"✅ Pattern recorded and index updated")


if __name__ == "__main__":
    # Test the embedding engine
    print("Testing GUKS Embedding Engine...\n")

    # Initialize
    guks = EnhancedGUKS()

    # Test query
    print("Query: 'TypeError in user.profile.name'\n")
    results = guks.query(
        code="user.profile.name",
        error="TypeError: Cannot read property"
    )

    print(f"Found {len(results)} similar patterns:\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['error']}")
        print(f"   Fix: {r['fix']}")
        print(f"   Project: {r['project']}")
        print(f"   Similarity: {r.get('similarity', r.get('score', 0)):.2%}\n")

    # Get stats
    stats = guks.embedding_engine.get_stats()
    print(f"Index stats: {stats}")
