# tests/ui/test_file_helper.py
import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from modules.ui.file_helper import (
    ensure_directory,
    extract_act_scene_from_filename,
    parse_markdown_scene,
    save_text_to_file,
    load_text_from_file,
    save_json_to_file,
    load_json_from_file,
    roman_to_int
)

class TestFileHelper:
    
    @patch('modules.ui.file_helper.os.makedirs')
    def test_ensure_directory(self, mock_makedirs):
        """Test ensuring a directory exists."""
        # Act
        ensure_directory("test_dir")
        
        # Assert
        mock_makedirs.assert_called_once_with("test_dir", exist_ok=True)
    
    def test_extract_act_scene_from_filename(self):
        """Test extracting act and scene from various filename formats."""
        # Test cases for different filename formats
        test_cases = [
            ("act_1_scene_2.md", "1", "2"),
            ("act1_scene2.md", "1", "2"),
            ("a1s2.md", "1", "2"),
            ("I_1.md", "I", "1"),
            ("unknown.md", "unknown", "unknown")
        ]
        
        # Test each case
        for filename, expected_act, expected_scene in test_cases:
            act, scene = extract_act_scene_from_filename(filename)
            assert act == expected_act
            assert scene == expected_scene
    
    @patch('modules.ui.file_helper.open', new_callable=mock_open, read_data="# Header\n\nSome dialog line\n[Stage direction]\nCHARACTER\nMore dialog")
    def test_parse_markdown_scene(self, mock_file):
        """Test parsing a markdown scene file."""
        # Act
        lines = parse_markdown_scene("test_file.md")
        
        # Assert
        assert len(lines) == 2
        assert "Some dialog line" in lines
        assert "More dialog" in lines
        assert "# Header" not in lines
        assert "[Stage direction]" not in lines
        assert "CHARACTER" not in lines
    
    def test_roman_to_int(self):
        """Test converting Roman numerals to integers."""
        # Test cases
        test_cases = [
            ("I", 1),
            ("V", 5),
            ("X", 10),
            ("IV", 4),
            ("IX", 9),
            ("MCMXCIV", 1994)
        ]
        
        # Test each case
        for roman, expected in test_cases:
            result = roman_to_int(roman)
            assert result == expected
    
    @patch('modules.ui.file_helper.open', new_callable=mock_open)
    @patch('modules.ui.file_helper.os.makedirs')
    def test_save_text_to_file(self, mock_makedirs, mock_file):
        """Test saving text to a file."""
        # Act
        result = save_text_to_file("Test content", "test_dir/test_file.txt")
        
        # Assert
        assert result is True
        mock_makedirs.assert_called_once_with("test_dir", exist_ok=True)
        mock_file.assert_called_once_with("test_dir/test_file.txt", 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with("Test content")
    
    @patch('modules.ui.file_helper.open', new_callable=mock_open, read_data="Test content")
    def test_load_text_from_file(self, mock_file):
        """Test loading text from a file."""
        # Act
        result = load_text_from_file("test_file.txt")
        
        # Assert
        assert result == "Test content"
        mock_file.assert_called_once_with("test_file.txt", 'r', encoding='utf-8')