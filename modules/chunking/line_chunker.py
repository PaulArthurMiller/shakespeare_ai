"""
Line chunker module for Shakespeare AI project.

This module provides functionality to chunk Shakespeare's text into full lines,
preserving speaker information and basic line metadata.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from .base import ChunkBase


class LineChunker(ChunkBase):
    """Chunker for processing Shakespeare's text into full lines.
    
    This chunker splits text into individual lines, handling speaker labels and
    maintaining act/scene structure information.
    """
    
    def __init__(self):
        """Initialize the LineChunker."""
        super().__init__(chunk_type='line')
        # Regular expressions for detecting structural elements
        self.act_pattern = re.compile(r'^ACT\s+([IVX]+)', re.IGNORECASE)
        self.scene_pattern = re.compile(r'^SCENE\s+([IVX]+)', re.IGNORECASE)
        self.speaker_pattern = re.compile(r'^([A-Z][A-Z\s]+)\.(.+)$')
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Split the play text into individual lines with metadata.
        
        Args:
            text (str): The play text to process
            
        Returns:
            List[Dict[str, Any]]: List of line chunks with metadata
        """
        lines = text.strip().split('\n')
        chunks = []
        
        current_act = None
        current_scene = None
        current_speaker = None
        line_index = 0
        
        for line_no, line in enumerate(lines):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Check for act markers
            act_match = self.act_pattern.match(line)
            if act_match:
                current_act = act_match.group(1)
                current_scene = None  # Reset scene when act changes
                continue
            
            # Check for scene markers
            scene_match = self.scene_pattern.match(line)
            if scene_match:
                current_scene = scene_match.group(1)
                continue
            
            # Check for speaker and dialogue
            speaker_match = self.speaker_pattern.match(line)
            if speaker_match:
                current_speaker = speaker_match.group(1).strip()
                dialogue = speaker_match.group(2).strip()
            else:
                dialogue = line
            
            # Only create chunks for actual dialogue lines
            if dialogue:
                # Increment line index only for dialogue lines
                line_index += 1
                
                # Create the chunk with all relevant metadata
                chunk = {
                    'chunk_id': f'line_{line_index}',
                    'text': dialogue,
                    'line_number': line_no + 1,  # 1-based line numbering
                    'act': current_act,
                    'scene': current_scene,
                    'speaker': current_speaker,
                    'char_length': len(dialogue),
                    'word_count': len(dialogue.split())
                }
                chunks.append(chunk)
        
        return chunks
    
    def get_speaker_lines(self, speaker: str) -> List[Dict[str, Any]]:
        """Get all lines for a specific speaker.
        
        Args:
            speaker (str): The speaker name to filter by
            
        Returns:
            List[Dict[str, Any]]: List of line chunks for the specified speaker
        """
        return [chunk for chunk in self.chunks if chunk.get('speaker') == speaker]
    
    def get_lines_by_act_scene(self, act: str, scene: str) -> List[Dict[str, Any]]:
        """Get all lines from a specific act and scene.
        
        Args:
            act (str): The act number (e.g., 'I', 'V')
            scene (str): The scene number (e.g., 'I', 'III')
            
        Returns:
            List[Dict[str, Any]]: List of line chunks from the specified act and scene
        """
        return [
            chunk for chunk in self.chunks 
            if chunk.get('act') == act and chunk.get('scene') == scene
        ]
    
    def get_dialogue_exchange(self, start_index: int, max_lines: int = 10) -> List[Dict[str, Any]]:
        """Get a dialogue exchange starting from a specific line.
        
        Args:
            start_index (int): The starting line index
            max_lines (int): Maximum number of lines to include
            
        Returns:
            List[Dict[str, Any]]: List of consecutive line chunks
        """
        if not self.chunks or start_index >= len(self.chunks):
            return []
        
        end_index = min(start_index + max_lines, len(self.chunks))
        return self.chunks[start_index:end_index]