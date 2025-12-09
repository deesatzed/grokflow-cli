"""
Pytest configuration and shared fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def temp_file(temp_dir):
    """Create temporary file for tests"""
    file_path = temp_dir / "test_file.txt"
    file_path.write_text("test content")
    return file_path


@pytest.fixture
def mock_session():
    """Mock session data"""
    return {
        'workspace': '/test/workspace',
        'context_files': [],
        'conversation': [],
        'undo_stack': [],
        'image_analyses': [],
        'created_at': '2025-11-14T10:00:00',
        'last_modified': '2025-11-14T10:00:00',
        'version': '2.0'
    }
