# tests/ui/test_integration.py
import pytest
import os
from unittest.mock import patch, MagicMock

from modules.ui.ui_translator import UITranslator
from modules.ui.session_manager import create_new_session

class TestIntegration:
    
    @pytest.mark.skipif(not os.getenv("RUN_INTEGRATION_TESTS"), reason="Integration tests disabled")
    @patch('modules.ui.ui_translator.TranslationManager')
    @patch('modules.ui.session_manager.save_session_info')
    def test_translator_with_session(self, mock_save_session, mock_translation_manager, mock_logger):
        """Test the translator with a real session."""
        # Arrange
        translation_id = create_new_session("test_output")
        assert translation_id is not None
        
        # Create mock return values
        mock_manager = MagicMock()
        mock_translation_manager.return_value = mock_manager
        mock_manager.translate_line.return_value = {
            "text": "To be, or not to be: that is the question.",
            "references": [{"title": "Hamlet"}],
            "original_modern_line": "Should I live or die?"
        }
        
        # Act
        translator = UITranslator(translation_id=translation_id, logger=mock_logger)
        translator.initialize()
        result = translator.translate_line("Should I live or die?")
        
        # Assert
        assert result is not None
        assert "text" in result
        assert result["text"] == "To be, or not to be: that is the question."
        mock_manager.start_translation_session.assert_called_once_with(translation_id)