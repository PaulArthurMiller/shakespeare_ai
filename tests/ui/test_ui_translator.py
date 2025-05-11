# tests/ui/test_ui_translator.py

import os
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open

from modules.ui.ui_translator import UITranslator, get_ui_translator
from modules.ui.file_helper import extract_act_scene_from_filename

# Constants for testing
TEST_TRANSLATION_ID = "test_translation_123"
TEST_MODERN_LINE = "This is a test line to translate."
TEST_OUTPUT_DIR = "test_outputs/translated_scenes"
TEST_FILEPATH = "tests/data/test_scene.md"


class TestUITranslator:
    """Tests for the UITranslator class."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Create a test logger
        self.test_logger = MagicMock()
        self.test_logger.info = MagicMock()
        self.test_logger.error = MagicMock()
        self.test_logger.warning = MagicMock()
        self.test_logger.debug = MagicMock()
        
        # Mock TranslationManager and SceneSaver
        self.mock_translation_manager = MagicMock()
        self.mock_scene_saver = MagicMock()
        
        # Create a test instance with our mocks
        self.translator = UITranslator(translation_id=TEST_TRANSLATION_ID, logger=self.test_logger)
        self.translator.translation_manager = self.mock_translation_manager
        self.translator.is_initialized = True

    @patch('modules.ui.ui_translator.TranslationManager')
    def test_initialization(self, mock_translation_manager_class):
        """Test that the translator initializes correctly."""
        # Arrange
        mock_translation_manager_instance = MagicMock()
        mock_translation_manager_class.return_value = mock_translation_manager_instance
        translator = UITranslator(translation_id=TEST_TRANSLATION_ID, logger=self.test_logger)
        
        # Act
        result = translator.initialize()
        
        # Assert
        assert result is True
        assert translator.is_initialized is True
        mock_translation_manager_class.assert_called_once()
        mock_translation_manager_instance.start_translation_session.assert_called_once_with(TEST_TRANSLATION_ID)
        self.test_logger.info.assert_called()

    @patch('modules.ui.ui_translator.TranslationManager')
    def test_initialization_error_handling(self, mock_translation_manager):
        """Test error handling during initialization."""
        # Arrange
        mock_translation_manager.side_effect = Exception("Test error")
        translator = UITranslator(logger=self.test_logger)
        
        # Act
        result = translator.initialize()
        
        # Assert
        assert result is False
        assert translator.is_initialized is False
        self.test_logger.error.assert_called()

    def test_set_translation_id(self):
        """Test setting a new translation ID."""
        # Arrange
        self.translator.initialize = MagicMock(return_value=True)
        new_translation_id = "new_test_translation_456"
        
        # Act
        result = self.translator.set_translation_id(new_translation_id)
        
        # Assert
        assert result is True
        assert self.translator.translation_id == new_translation_id
        self.translator.initialize.assert_called_once_with(force_reinit=True)

    def test_translate_line(self):
        """Test translating a single line."""
        # Arrange
        expected_result = {
            "text": "Verily, this be a line for translation.",
            "temp_ids": ["line_1"],
            "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "10"}],
            "original_modern_line": TEST_MODERN_LINE
        }
        self.mock_translation_manager.translate_line.return_value = expected_result
        
        # Act
        result = self.translator.translate_line(TEST_MODERN_LINE, use_hybrid_search=True)
        
        # Assert
        assert result == expected_result
        self.mock_translation_manager.translate_line.assert_called_once_with(
            modern_line=TEST_MODERN_LINE,
            selector_results={},
            use_hybrid_search=True
        )
        self.test_logger.info.assert_called()

    def test_translate_line_error_handling(self):
        """Test error handling during line translation."""
        # Arrange
        self.mock_translation_manager.translate_line.side_effect = Exception("Test error")
        
        # Mock the _log method to check how it's being called
        self.translator._log = MagicMock()
        
        # Act
        result = self.translator.translate_line(TEST_MODERN_LINE)
        
        # Assert
        assert result is None
        # Check that _log was called with an error message
        self.translator._log.assert_called_with("Error translating line: Test error")

    def test_translate_lines(self):
        """Test translating multiple lines."""
        # Arrange
        test_lines = [
            "This is line one.",
            "This is line two.",
            "This is line three."
        ]
        expected_results = [
            {
                "text": "Verily, this be line the first.",
                "temp_ids": ["line_1"],
                "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "10"}],
                "original_modern_line": test_lines[0]
            },
            {
                "text": "Indeed, this be line the second.",
                "temp_ids": ["line_2"],
                "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "11"}],
                "original_modern_line": test_lines[1]
            },
            {
                "text": "Forsooth, this be line the third.",
                "temp_ids": ["line_3"],
                "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "12"}],
                "original_modern_line": test_lines[2]
            }
        ]
        self.mock_translation_manager.translate_group.return_value = expected_results
        
        # Act
        result = self.translator.translate_lines(test_lines, use_hybrid_search=True)
        
        # Assert
        assert result == expected_results
        self.mock_translation_manager.translate_group.assert_called_once_with(
            modern_lines=test_lines,
            use_hybrid_search=True
        )
        self.test_logger.info.assert_called()

    def test_translate_lines_empty_input(self):
        """Test translating an empty list of lines."""
        # Mock the _log method
        self.translator._log = MagicMock()
        
        # Act
        result = self.translator.translate_lines([])
        
        # Assert
        assert result == []
        # Check that _log was called with an error message
        self.translator._log.assert_called_with("Error: Empty list of lines provided for translation")

    @patch('modules.ui.ui_translator.parse_markdown_scene')
    @patch('modules.ui.ui_translator.extract_act_scene_from_filename')
    @patch('modules.ui.ui_translator.ensure_directory')
    @patch('modules.ui.ui_translator.get_session_info')
    @patch('modules.ui.ui_translator.update_scene_info')
    @patch('modules.ui.ui_translator.SceneSaver')
    @patch('modules.ui.ui_translator.os.path.exists', return_value=True)
    def test_translate_file(
        self, mock_exists, mock_scene_saver, mock_update_scene_info, 
        mock_get_session_info, mock_ensure_dir, mock_extract, mock_parse
    ):
        """Test translating a file."""
        # Arrange
        mock_extract.return_value = ("1", "1")
        mock_parse.return_value = ["Line 1", "Line 2"]
        mock_get_session_info.return_value = {"output_dir": TEST_OUTPUT_DIR}
        
        # Create mock scene saver instance
        mock_saver_instance = MagicMock()
        mock_scene_saver.return_value = mock_saver_instance
        
        # Setup translation manager mock
        translated_lines = [
            {
                "text": "Verily, this be line the first.",
                "temp_ids": ["line_1"],
                "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "10"}],
                "original_modern_line": "Line 1"
            },
            {
                "text": "Indeed, this be line the second.",
                "temp_ids": ["line_2"],
                "references": [{"title": "Test Play", "act": "1", "scene": "1", "line": "11"}],
                "original_modern_line": "Line 2"
            }
        ]
        self.translator.translate_lines = MagicMock(return_value=translated_lines)
        
        # Act
        success, output_dir, line_count = self.translator.translate_file(
            filepath=TEST_FILEPATH,
            output_dir=TEST_OUTPUT_DIR
        )
        
        # Assert
        assert success is True
        assert output_dir == TEST_OUTPUT_DIR
        assert line_count == 2
        
        mock_extract.assert_called_once_with(TEST_FILEPATH)
        mock_parse.assert_called_once_with(TEST_FILEPATH)
        mock_ensure_dir.assert_called_once_with(TEST_OUTPUT_DIR)
        self.translator.translate_lines.assert_called_once()
        mock_scene_saver.assert_called_once()
        mock_saver_instance.save_scene.assert_called_once()
        mock_update_scene_info.assert_called_once()

    @patch('modules.ui.ui_translator.is_scene_translated', return_value=True)
    @patch('modules.ui.ui_translator.get_session_info')
    @patch('modules.ui.ui_translator.extract_act_scene_from_filename')
    @patch('modules.ui.ui_translator.os.path.exists', return_value=True)
    @patch('modules.ui.ui_translator.load_translated_scene')
    def test_translate_file_already_translated(
        self, mock_load_translated, mock_exists, mock_extract, 
        mock_get_session_info, mock_is_translated
    ):
        """Test handling a file that's already been translated."""
        # Arrange
        mock_extract.return_value = ("1", "1")
        mock_get_session_info.return_value = {"output_dir": TEST_OUTPUT_DIR}
        mock_load_translated.return_value = (["line1", "line2"], ["original1", "original2"])
        
        # Explicitly mock the translate_lines method
        self.translator.translate_lines = MagicMock()
        
        # Act
        success, output_dir, line_count = self.translator.translate_file(
            filepath=TEST_FILEPATH,
            force_retranslate=False
        )
        
        # Assert
        assert success is True
        mock_is_translated.assert_called_once()
        self.translator.translate_lines.assert_not_called()

    @patch('modules.ui.ui_translator.ensure_directory')
    @patch('builtins.open', new_callable=mock_open)
    def test_translate_uploaded_file(self, mock_file_open, mock_ensure_dir):
        """Test translating an uploaded file from Streamlit."""
        # Arrange
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "test_uploaded.md"
        mock_uploaded_file.getbuffer.return_value = b"Test content"
        
        self.translator.translate_file = MagicMock(return_value=(True, TEST_OUTPUT_DIR, 2))
        
        # Act
        success, output_dir, line_count = self.translator.translate_uploaded_file(
            uploaded_file=mock_uploaded_file,
            temp_dir="temp",
            output_dir=TEST_OUTPUT_DIR
        )
        
        # Assert
        assert success is True
        assert output_dir == TEST_OUTPUT_DIR
        assert line_count == 2
        
        mock_ensure_dir.assert_called_once()
        mock_file_open.assert_called_once()
        mock_uploaded_file.getbuffer.assert_called_once()
        self.translator.translate_file.assert_called_once()

    def test_get_translation_status_active(self):
        """Test getting status for an active translation session."""
        # Arrange
        with patch('modules.ui.ui_translator.get_session_info') as mock_get_info:
            mock_get_info.return_value = {
                "translation_id": TEST_TRANSLATION_ID,
                "scenes_translated": [{"act": "1", "scene": "1"}, {"act": "1", "scene": "2"}],
                "output_dir": TEST_OUTPUT_DIR,
                "created_at": "2025-01-01T12:00:00",
                "last_updated": "2025-01-01T13:00:00"
            }
            
            # Act
            status = self.translator.get_translation_status()
            
            # Assert
            assert status["initialized"] is True
            assert status["translation_id"] == TEST_TRANSLATION_ID
            assert status["scene_count"] == 2
            assert status["output_dir"] == TEST_OUTPUT_DIR
            assert status["created_at"] == "2025-01-01T12:00:00"
            assert status["last_updated"] == "2025-01-01T13:00:00"

    def test_get_translation_status_inactive(self):
        """Test getting status with no active translation session."""
        # Arrange
        translator = UITranslator(logger=self.test_logger)  # No translation ID
        
        # Act
        status = translator.get_translation_status()
        
        # Assert
        assert status["initialized"] is False
        assert status["translation_id"] is None
        assert status["scene_count"] == 0
        assert "message" in status


class TestUITranslatorSingleton:
    """Tests for the UITranslator singleton pattern."""

    @patch('modules.ui.ui_translator.UITranslator')
    def test_get_ui_translator_creates_instance(self, mock_ui_translator_class):
        """Test that get_ui_translator creates an instance if none exists."""
        # Arrange
        mock_instance = MagicMock()
        mock_ui_translator_class.return_value = mock_instance
        mock_logger = MagicMock()
        
        # Act
        with patch('modules.ui.ui_translator._INSTANCE', None):
            result = get_ui_translator(translation_id=TEST_TRANSLATION_ID, logger=mock_logger)
        
        # Assert
        assert result is mock_instance
        mock_ui_translator_class.assert_called_once_with(
            translation_id=TEST_TRANSLATION_ID, 
            logger=mock_logger
        )

    @patch('modules.ui.ui_translator.UITranslator')
    def test_get_ui_translator_reuses_instance(self, mock_ui_translator_class):
        """Test that get_ui_translator reuses the existing instance."""
        # Arrange
        mock_instance = MagicMock()
        mock_logger = MagicMock()
        
        # Act
        with patch('modules.ui.ui_translator._INSTANCE', mock_instance):
            result = get_ui_translator(logger=mock_logger)
        
        # Assert
        assert result is mock_instance
        mock_ui_translator_class.assert_not_called()

    @patch('modules.ui.ui_translator.UITranslator')
    def test_get_ui_translator_updates_translation_id(self, mock_ui_translator_class):
        """Test that get_ui_translator updates the translation ID if provided."""
        # Arrange
        mock_instance = MagicMock()
        mock_instance.translation_id = "old_id"
        mock_logger = MagicMock()
        
        # Act
        with patch('modules.ui.ui_translator._INSTANCE', mock_instance):
            result = get_ui_translator(translation_id="new_id", logger=mock_logger)
        
        # Assert
        assert result is mock_instance
        mock_instance.set_translation_id.assert_called_once_with("new_id")
        mock_ui_translator_class.assert_not_called()