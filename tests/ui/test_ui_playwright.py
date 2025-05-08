# tests/ui/test_ui_playwright.py
import pytest
import os
from unittest.mock import patch, MagicMock

from modules.ui.playwright.ui_playwright import UIPlaywright

class TestUIPlaywright:
    
    def test_initialization(self, mock_logger):
        """Test that the playwright initializes correctly."""
        # Arrange & Act
        playwright = UIPlaywright(logger=mock_logger)
        
        # Assert
        assert playwright.logger == mock_logger
        assert playwright.base_output_dir == "data/modern_play"
        mock_logger.info.assert_called()
    
    @patch('modules.ui.ui_playwright.save_playwright_config')
    def test_update_config(self, mock_save_config, mock_logger):
        """Test updating the playwright configuration."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        mock_save_config.return_value = True
        
        # Act
        result = playwright.update_config({"model_provider": "anthropic"})
        
        # Assert
        assert result is True
        mock_save_config.assert_called_once_with({"model_provider": "anthropic"})
    
    @patch('modules.ui.ui_playwright.save_json_to_file')
    @patch('modules.ui.ui_playwright.ensure_directory')
    def test_save_character_voices(self, mock_ensure_dir, mock_save_json, mock_logger):
        """Test saving character voices."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        characters = {"Hamlet": "Melancholic and philosophical"}
        mock_save_json.return_value = True
        
        # Act
        result = playwright.save_character_voices(characters)
        
        # Assert
        assert result is True
        mock_ensure_dir.assert_called()
        mock_save_json.assert_called_once_with(characters, playwright.characters_path)
    
    @patch('modules.ui.ui_playwright.load_json_from_file')
    def test_load_character_voices(self, mock_load_json, mock_logger):
        """Test loading character voices."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        expected_characters = {"Hamlet": "Melancholic and philosophical"}
        mock_load_json.return_value = expected_characters
        
        # Act
        result = playwright.load_character_voices()
        
        # Assert
        assert result == expected_characters
        mock_load_json.assert_called_once_with(playwright.characters_path)
    
    @patch('modules.ui.ui_playwright.StoryExpander')
    @patch('modules.ui.ui_playwright.load_playwright_config')
    def test_expand_story(self, mock_load_config, mock_story_expander, mock_logger):
        """Test expanding a story."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        mock_load_config.return_value = {"model_provider": "anthropic"}
        
        # Create a mock StoryExpander instance
        mock_expander = MagicMock()
        mock_story_expander.return_value = mock_expander
        mock_expander.expand_all_scenes.return_value = None
        
        # Act
        success, result = playwright.expand_story()
        
        # Assert
        assert success is True
        assert result == playwright.expanded_story_path
        mock_story_expander.assert_called_once()
        mock_expander.expand_all_scenes.assert_called_once()
        
    @patch('modules.ui.ui_playwright.SceneWriter')
    @patch('modules.ui.ui_playwright.os.path.exists')
    def test_generate_scenes(self, mock_exists, mock_scene_writer, mock_logger):
        """Test generating scenes."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        mock_exists.return_value = True
        
        # Create a mock SceneWriter instance
        mock_writer = MagicMock()
        mock_scene_writer.return_value = mock_writer
        mock_writer.generate_scenes.return_value = None
        mock_writer.output_dir = "test_output_dir"
        
        # Act
        success, result = playwright.generate_scenes()
        
        # Assert
        assert success is True
        assert result == "test_output_dir"
        mock_scene_writer.assert_called_once()
        mock_writer.generate_scenes.assert_called_once()
    
    @patch('modules.ui.ui_playwright.ArtisticAdjuster')
    @patch('modules.ui.ui_playwright.os.path.exists')
    @patch('modules.ui.ui_playwright.ensure_directory')
    def test_adjust_scene(self, mock_ensure_dir, mock_exists, mock_artistic_adjuster, mock_logger):
        """Test adjusting a scene."""
        # Arrange
        playwright = UIPlaywright(logger=mock_logger)
        mock_exists.return_value = True
        
        # Create a mock ArtisticAdjuster instance
        mock_adjuster = MagicMock()
        mock_artistic_adjuster.return_value = mock_adjuster
        mock_adjuster.revise_scene.return_value = "Adjusted scene text"
        
        # Act
        success, result = playwright.adjust_scene(
            scene_path="test_scene.md",
            critique="Make it more dramatic"
        )
        
        # Assert
        assert success is True
        assert result == "Adjusted scene text"
        mock_artistic_adjuster.assert_called_once()
        mock_adjuster.revise_scene.assert_called_once_with(
            scene_path="test_scene.md",
            critique="Make it more dramatic",
            output_dir=os.path.join(playwright.base_output_dir, "final_edits")
        )