# tests/ui/test_ui_translator.py
import pytest
import os
from unittest.mock import patch, MagicMock

from modules.ui.ui_translator import UITranslator

class TestUITranslator:
    
    @patch('modules.ui.ui_translator.TranslationManager')
    def test_initialization(self, mock_translation_manager_class, mock_logger, test_translation_id):
        """Test that the translator initializes correctly."""
        # Arrange - Create mock instance with necessary methods
        mock_translation_manager_instance = MagicMock()
        mock_translation_manager_instance.start_translation_session = MagicMock()
        mock_translation_manager_class.return_value = mock_translation_manager_instance
        
        translator = UITranslator(translation_id=test_translation_id, logger=mock_logger)
        
        # Act
        result = translator.initialize()
        
        # Assert
        assert result is True
        assert translator.is_initialized is True
        assert translator.translation_id == test_translation_id
        mock_logger.info.assert_called()
        mock_translation_manager_class.assert_called_once()
        mock_translation_manager_instance.start_translation_session.assert_called_once_with(test_translation_id)
    
    @patch('modules.ui.ui_translator.TranslationManager')
    def test_initialization_error_handling(self, mock_translation_manager, mock_logger):
        """Test error handling during initialization."""
        # Arrange
        mock_translation_manager.side_effect = Exception("Test error")
        translator = UITranslator(logger=mock_logger)
        
        # Act
        result = translator.initialize()
        
        # Assert
        assert result is False
        assert translator.is_initialized is False
        mock_logger.error.assert_called()
    
    @patch('modules.ui.ui_translator.TranslationManager')
    def test_translate_line(self, mock_translation_manager, mock_logger, mock_translator_manager):
        """Test translating a single line."""
        # Arrange
        translator = UITranslator(logger=mock_logger)
        translator.translation_manager = mock_translator_manager
        translator.is_initialized = True
        modern_line = "Should I live or die? That's what I'm trying to decide."
        
        # Act
        result = translator.translate_line(modern_line, use_hybrid_search=True)
        
        # Assert
        assert result is not None
        assert "text" in result
        assert result["text"] == "To be, or not to be: that is the question."
        mock_translator_manager.translate_line.assert_called_once_with(
            modern_line=modern_line,
            selector_results={},
            use_hybrid_search=True
        )
    
    @patch('modules.ui.ui_translator.TranslationManager')
    def test_translate_lines(self, mock_translation_manager, mock_logger, mock_translator_manager):
        """Test translating multiple lines."""
        # Arrange
        translator = UITranslator(logger=mock_logger)
        translator.translation_manager = mock_translator_manager
        translator.is_initialized = True
        modern_lines = ["Line 1", "Line 2"]
        
        # Act
        results = translator.translate_lines(modern_lines)
        
        # Assert
        assert len(results) > 0
        mock_translator_manager.translate_group.assert_called_once_with(
            modern_lines=modern_lines,
            use_hybrid_search=True
        )
    
    @patch('modules.ui.ui_translator.is_scene_translated', return_value=False)
    @patch('modules.ui.ui_translator.update_scene_info')
    @patch('modules.ui.ui_translator.get_session_info')
    @patch('modules.ui.ui_translator.extract_act_scene_from_filename')
    @patch('modules.ui.ui_translator.parse_markdown_scene')
    @patch('modules.ui.ui_translator.SceneSaver')
    @patch('modules.ui.ui_translator.TranslationManager')
    @patch('modules.ui.ui_translator.os.path.exists', return_value=True)
    def test_translate_file(
        self, 
        mock_exists,
        mock_translation_manager_class,
        mock_scene_saver_class,
        mock_parse_markdown_scene,
        mock_extract_act_scene,
        mock_get_session_info,
        mock_update_scene_info,
        mock_is_scene_translated,
        mock_logger,
        mock_translator_manager
    ):
        """Test translating a file."""
        # Arrange
        translator = UITranslator(translation_id="test_translation_id", logger=mock_logger)
        translator.translation_manager = mock_translator_manager
        translator.is_initialized = True
        
        # Set up mocks with more complete responses
        mock_extract_act_scene.return_value = ("1", "1")
        mock_parse_markdown_scene.return_value = ["Line 1", "Line 2"]
        mock_get_session_info.return_value = {"output_dir": "test_output"}
        
        # Ensure SceneSaver behaves correctly
        mock_saver_instance = MagicMock()
        mock_scene_saver_class.return_value = mock_saver_instance
        mock_saver_instance.save_scene.return_value = None
        
        # Create a comprehensive mock for translate_lines
        dummy_translations = [
            {
                "text": "To be, or not to be: that is the question.",
                "temp_ids": ["line_1"],
                "references": [{"title": "Hamlet", "act": "3", "scene": "1", "line": "56"}],
                "original_modern_line": "Line 1"
            },
            {
                "text": "Whether 'tis nobler in the mind to suffer.",
                "temp_ids": ["line_2"],
                "references": [{"title": "Hamlet", "act": "3", "scene": "1", "line": "57"}],
                "original_modern_line": "Line 2"
            }
        ]
        translator.translate_lines = MagicMock(return_value=dummy_translations)
        
        # Act
        success, output_dir, line_count = translator.translate_file(
            filepath="test_file.md",
            output_dir="test_output"
        )
        
        # Assert
        assert success is True
        assert output_dir == "test_output"
        assert line_count == 2
        
        # Additional assertions to verify method calls
        mock_extract_act_scene.assert_called_once()
        mock_parse_markdown_scene.assert_called_once()
        mock_scene_saver_class.assert_called_once()
        mock_saver_instance.save_scene.assert_called_once()
        mock_update_scene_info.assert_called_once()
    
    @patch('modules.ui.ui_translator.TranslationManager')
    def test_error_handling_translate_line(self, mock_translation_manager, mock_logger):
        """Test error handling during line translation."""
        # Arrange
        translator = UITranslator(logger=mock_logger)
        translator.is_initialized = True
        translator.translation_manager = MagicMock()
        translator.translation_manager.translate_line.side_effect = Exception("Test error")
        
        # Mock the _log method to check how it's being called
        translator._log = MagicMock()
        
        # Act
        result = translator.translate_line("Test line")
        
        # Assert
        assert result is None
        # Check that _log was called with an error message (without the level parameter)
        translator._log.assert_called_with("Error translating line: Test error")