# tests/ui/conftest.py
import os
import sys
import pytest
from unittest.mock import MagicMock

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

@pytest.fixture
def mock_logger():
    """Mock logger for testing UI components."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger

@pytest.fixture
def test_temp_dir(tmpdir):
    """Create a temporary directory for file operations during tests."""
    return tmpdir.mkdir("temp")

@pytest.fixture
def test_output_dir(tmpdir):
    """Create a temporary output directory for test results."""
    return tmpdir.mkdir("outputs")

@pytest.fixture
def test_translation_id():
    """Provide a fixed translation ID for testing."""
    return "test_translation_123456"

@pytest.fixture
def mock_translator_manager():
    """Mock the TranslationManager class."""
    manager = MagicMock()
    manager.start_translation_session = MagicMock()
    manager.translate_line = MagicMock(return_value={
        "text": "To be, or not to be: that is the question.",
        "temp_ids": ["line_1"],
        "references": [{"title": "Hamlet", "act": "3", "scene": "1", "line": "56"}],
        "original_modern_line": "Should I live or die? That's what I'm trying to decide."
    })
    manager.translate_group = MagicMock(return_value=[
        {
            "text": "To be, or not to be: that is the question.",
            "temp_ids": ["line_1"],
            "references": [{"title": "Hamlet", "act": "3", "scene": "1", "line": "56"}],
            "original_modern_line": "Should I live or die? That's what I'm trying to decide."
        }
    ])
    return manager

@pytest.fixture
def mock_scene_saver():
    """Mock the SceneSaver class."""
    saver = MagicMock()
    saver.save_scene = MagicMock()
    return saver