# tests/ui/test_session_manager.py
import pytest
import os
import json
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path

from modules.ui.session_manager import (
    setup_session_directory,
    generate_translation_id,
    get_session_info_path,
    get_session_info,
    get_all_sessions,
    create_new_session,
    save_session_info,
    update_scene_info,
    is_scene_translated
)

class TestSessionManager:
    
    @patch('modules.ui.session_manager.os.makedirs')
    def test_setup_session_directory(self, mock_makedirs):
        """Test setting up the session directory."""
        # Act
        setup_session_directory()
        
        # Assert
        mock_makedirs.assert_called_once_with("translation_sessions", exist_ok=True)
    
    @patch('modules.ui.session_manager.datetime')
    @patch('modules.ui.session_manager.uuid.uuid4')
    def test_generate_translation_id(self, mock_uuid, mock_datetime):
        """Test generating a translation ID."""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20250101_1200"
        mock_uuid.return_value = MagicMock(__str__=lambda x: "123456789012")
        
        # Act
        translation_id = generate_translation_id()
        
        # Assert
        assert translation_id == "trans_20250101_1200_123456"
        
    def test_get_session_info_path(self):
        """Test getting the session info path."""
        # Act
        path = get_session_info_path("test_id")
        
        # Assert
        expected_path = os.path.join("translation_sessions", "test_id_translation_info.json")
        assert path == expected_path
        
    @patch('modules.ui.session_manager.os.path.exists')
    @patch('modules.ui.session_manager.open', new_callable=mock_open, read_data='{"translation_id": "test_id", "scenes_translated": []}')
    def test_get_session_info_existing(self, mock_file, mock_exists):
        """Test getting info for an existing session."""
        # Arrange
        mock_exists.return_value = True
        
        # Act
        info = get_session_info("test_id")
        
        # Assert
        assert info["translation_id"] == "test_id"
        assert "scenes_translated" in info
    
    @patch('modules.ui.session_manager.Path.glob')
    @patch('modules.ui.session_manager.open', new_callable=mock_open, read_data='{"translation_id": "test_id", "scenes_translated": []}')
    def test_get_all_sessions(self, mock_file, mock_glob):
        """Test getting all sessions."""
        # Arrange
        mock_path1 = MagicMock()
        mock_path1.name = "test_id_translation_info.json"
        mock_glob.return_value = [mock_path1]
        
        # Act
        sessions = get_all_sessions()
        
        # Assert
        assert len(sessions) == 1
        assert sessions[0]["translation_id"] == "test_id"