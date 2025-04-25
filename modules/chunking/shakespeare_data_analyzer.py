# shakespeare_data_analyzer.py

import json
import os
import logging
from collections import defaultdict, Counter
from typing import Dict, Set, List, Tuple, Any, Optional, Union, DefaultDict
from datetime import datetime

# Define custom type for our work statistics
WorkStats = Dict[str, Union[Set[str], DefaultDict[str, Set[str]], int, List[Tuple[int, Optional[int], str]]]]

def setup_logging(log_path: str) -> logging.Logger:
    """Set up logging to file and console"""
    # Create logger
    logger = logging.getLogger("shakespeare_analyzer")
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # File handler
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def analyze_shakespeare_data(json_path: str, logger: logging.Logger) -> None:
    """
    Analyze the Shakespeare lines data for metadata issues.
    
    Args:
        json_path: Path to the lines.json file
        logger: Logger for output
    """
    # Load the JSON data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data: Dict[str, Any] = json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        return
    
    if "chunks" not in data:
        logger.error("Error: JSON data doesn't contain 'chunks' key")
        return
    
    chunks: List[Dict[str, Any]] = data["chunks"]
    logger.info(f"Total chunks: {len(chunks)}")
    
    # Create data structures to track statistics
    works_data: Dict[str, WorkStats] = {}
    for title in {chunk.get("title", "UNKNOWN") for chunk in chunks}:
        works_data[title] = {
            "acts": set(),
            "scenes": defaultdict(set),  # act -> scenes
            "lines": 0,
            "null_acts": 0,
            "null_scenes": 0,
            "null_scene_lines": []  # Save line numbers with null scenes for inspection
        }
    
    metadata_issues: Dict[str, List[str]] = defaultdict(list)
    
    # Process each chunk
    for i, chunk in enumerate(chunks):
        # Get title and metadata
        title: str = chunk.get("title", "UNKNOWN")
        act: Optional[str] = chunk.get("act")
        scene: Optional[str] = chunk.get("scene")
        line_num: Optional[int] = chunk.get("line")
        text: str = chunk.get("text", "")
        
        # Count lines
        stats = works_data[title]
        stats["lines"] = cast(int, stats["lines"]) + 1
        
        # Track acts and scenes
        if act is None or act == "" or str(act).lower() == "null":
            stats["null_acts"] = cast(int, stats["null_acts"]) + 1
        else:
            cast(Set[str], stats["acts"]).add(str(act))
        
        # Track scenes
        if scene is None or scene == "" or str(scene).lower() == "null":
            stats["null_scenes"] = cast(int, stats["null_scenes"]) + 1
            # Save index and text of null scene lines for inspection
            cast(List[Tuple[int, Optional[int], str]], stats["null_scene_lines"]).append(
                (i, line_num, text[:50] + "...")
            )
        else:
            scenes_dict = cast(DefaultDict[str, Set[str]], stats["scenes"])
            if act is not None:
                scenes_dict[str(act)].add(str(scene))
        
        # Check for issues
        if not title or title == "UNKNOWN":
            metadata_issues["missing_title"].append(f"Chunk {i}: Missing title")
        
        if not isinstance(line_num, (int, float)) and line_num != 0:  # Allow for line 0
            metadata_issues["missing_line"].append(f"Chunk {i}: Missing line number in {title}")
    
    # Look for inconsistencies in acts
    act_sequence_issues: Dict[str, List[str]] = defaultdict(list)
    current_title: Optional[str] = None
    current_act: Optional[str] = None
    act_counts: Dict[str, int] = {}
    
    for i, chunk in enumerate(chunks):
        title: str = chunk.get("title", "UNKNOWN")
        act: Optional[str] = chunk.get("act")
        
        # Reset tracking when title changes
        if title != current_title:
            current_title = title
            current_act = act
            act_counts = Counter()
        
        # Skip null acts for sequence checking
        if act is None or act == "" or str(act).lower() == "null":
            continue
            
        act_str = str(act)
        
        # Check for act repetition
        if current_act is not None and act_str == current_act:
            act_counts[act_str] += 1
            # Flag extremely long act repetitions (allows for common sequences)
            if act_counts[act_str] > 1000:  # Threshold for suspiciously long acts
                act_sequence_issues[title].append(f"Act {act_str} appears {act_counts[act_str]} times in a row")
        else:
            # Check for act regression (Act II -> Act I)
            if current_act is not None and title != "THE SONNETS":  # Skip this check for sonnets
                # Handle Roman numeral comparisons
                roman_values = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
                
                # Simple conversion for basic Roman numerals
                def simple_roman_to_int(roman: str) -> int:
                    if all(c in roman_values for c in roman.upper()):
                        value = 0
                        for c in roman.upper():
                            value += roman_values[c]
                        return value
                    return 0
                
                # Only compare if both look like Roman numerals
                if (all(c in roman_values for c in current_act.upper()) and 
                    all(c in roman_values for c in act_str.upper())):
                    act_val = simple_roman_to_int(act_str)
                    current_act_val = simple_roman_to_int(current_act)
                    
                    if 0 < act_val < current_act_val:
                        act_sequence_issues[title].append(
                            f"Act regression from {current_act} to {act_str} at chunk {i}")
            
            current_act = act_str
            act_counts = Counter([act_str])
    
    # Check for duplicate scenes within same act
    duplicate_scenes: Dict[str, List[str]] = defaultdict(list)
    for title, stats in works_data.items():
        scenes_dict = cast(DefaultDict[str, Set[str]], stats["scenes"])
        for act, scenes in scenes_dict.items():
            # Convert set to list to check if we have expected scene progression
            if len(scenes) > 1:  # Only check if more than one scene
                scene_list = sorted(scenes)
                
                # Try to convert to integers for comparison if possible
                try:
                    numeric_scenes = [int(s) for s in scene_list]
                    for i in range(1, len(numeric_scenes)):
                        # Check for scenes that don't increase sequentially
                        if numeric_scenes[i] != numeric_scenes[i-1] + 1:
                            duplicate_scenes[title].append(
                                f"Act {act}: Non-sequential scenes {numeric_scenes[i-1]} to {numeric_scenes[i]}")
                except ValueError:
                    # If scenes aren't numeric, just look for duplicates
                    if len(scene_list) != len(set(scene_list)):
                        duplicate_scenes[title].append(
                            f"Act {act}: Contains duplicate scene numbers {', '.join(scene_list)}")
    
    # ===== PRINT ANALYSIS RESULTS =====
    logger.info("\n========= SHAKESPEARE DATA ANALYSIS =========")
    logger.info(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"File Analyzed: {json_path}")
    logger.info("==============================================\n")
    
    # 1. Works with null acts
    logger.info("\n=== WORKS WITH NULL ACTS ===")
    has_null_acts = False
    for title, stats in sorted(works_data.items()):
        null_acts = cast(int, stats["null_acts"])
        if null_acts > 0:
            logger.info(f"{title}: {null_acts} lines with null acts")
            has_null_acts = True
    if not has_null_acts:
        logger.info("No works with null acts found.")
    
    # 2. Works with null scenes
    logger.info("\n=== WORKS WITH NULL SCENES ===")
    has_null_scenes = False
    for title, stats in sorted(works_data.items()):
        null_scenes = cast(int, stats["null_scenes"])
        if null_scenes > 0:
            logger.info(f"{title}: {null_scenes} lines with null scenes")
            null_scene_lines = cast(List[Tuple[int, Optional[int], str]], stats['null_scene_lines'])
            for idx, line_num, text in null_scene_lines[:3]:  # Show max 3 examples
                logger.info(f"  - Line {line_num}: {text}")
            if len(null_scene_lines) > 3:
                logger.info(f"  ... and {len(null_scene_lines) - 3} more")
            has_null_scenes = True
    if not has_null_scenes:
        logger.info("No works with null scenes found.")
    
    # 3. Act sequence issues
    logger.info("\n=== ACT SEQUENCE ISSUES ===")
    if act_sequence_issues:
        for title, issues in sorted(act_sequence_issues.items()):
            logger.info(f"{title}:")
            for issue in issues:
                logger.info(f"  - {issue}")
    else:
        logger.info("No act sequence issues found.")
    
    # 4. Duplicate or non-sequential scenes
    logger.info("\n=== SCENE SEQUENCE ISSUES ===")
    if duplicate_scenes:
        for title, issues in sorted(duplicate_scenes.items()):
            logger.info(f"{title}:")
            for issue in issues:
                logger.info(f"  - {issue}")
    else:
        logger.info("No scene sequence issues found.")
    
    # 5. Unusual act counts
    logger.info("\n=== UNUSUAL ACT COUNTS ===")
    normal_act_count = 5
    found_unusual = False
    for title, stats in sorted(works_data.items()):
        acts_set = cast(Set[str], stats["acts"])
        act_count = len(acts_set) if acts_set else 0
        if act_count != normal_act_count and "SONNETS" not in title:
            logger.info(f"{title}: Has {act_count} acts (expected {normal_act_count})")
            found_unusual = True
    if not found_unusual:
        logger.info("All plays have the expected 5 acts.")
    
    # 6. Complete work statistics
    logger.info("\n=== COMPLETE WORK STATISTICS ===")
    for title, stats in sorted(works_data.items()):
        acts_set = cast(Set[str], stats["acts"])
        act_count = len(acts_set) if acts_set else 0
        
        scenes_dict = cast(DefaultDict[str, Set[str]], stats["scenes"])
        scene_counts = [len(scenes) for act, scenes in scenes_dict.items()]
        scene_count = sum(scene_counts)
        
        # Format the statistics
        logger.info(f"\n{title}")
        logger.info(f"  Acts: {act_count}" + (" + null" if cast(int, stats['null_acts']) > 0 else ""))
        if act_count > 0:
            logger.info(f"  Act Numbers: {', '.join(sorted(acts_set))}")
        logger.info(f"  Scenes: {scene_count}" + (" + null" if cast(int, stats['null_scenes']) > 0 else ""))
        logger.info(f"  Lines: {stats['lines']}")
        
        # Scene distribution per act
        if act_count > 0:
            logger.info("  Scene distribution per act:")
            for act in sorted(scenes_dict.keys()):
                if act is not None and act != "null":
                    scenes = scenes_dict[act]
                    logger.info(f"    Act {act}: {len(scenes)} scenes")
                    if len(scenes) > 0:
                        logger.info(f"      Scene Numbers: {', '.join(sorted(scenes))}")
    
    # 7. Missing metadata
    logger.info("\n=== MISSING METADATA ===")
    if any(metadata_issues.values()):
        for issue_type, issues in metadata_issues.items():
            if issues:
                logger.info(f"\n{issue_type.replace('_', ' ').title()}:")
                for issue in issues[:20]:  # Limit to avoid overwhelming output
                    logger.info(f"- {issue}")
                if len(issues) > 20:
                    logger.info(f"... and {len(issues) - 20} more issues")
    else:
        logger.info("No missing metadata found.")
    
    # 8. Recommendations
    logger.info("\n=== RECOMMENDATIONS ===")
    has_recommendations = False
    
    if has_null_acts:
        logger.info("- Check all 'null' acts - these could be introductory material outside the main acts")
        has_recommendations = True
    
    if has_null_scenes:
        logger.info("- Check all 'null' scenes - these could be prologues or choruses that need proper labeling")
        has_recommendations = True
    
    if any(metadata_issues.values()):
        logger.info("- Fix missing metadata (titles, line numbers) identified above")
        has_recommendations = True
    
    if act_sequence_issues:
        logger.info("- Review act sequence issues which may indicate incorrect ordering or labeling")
        has_recommendations = True
    
    if duplicate_scenes:
        logger.info("- Review works with duplicate or non-sequential scene numbers")
        has_recommendations = True
        
    if not has_recommendations:
        logger.info("No issues found - data appears to be well-structured!")
    
    logger.info("\n=== END OF ANALYSIS ===")

# Add missing import
from typing import cast

if __name__ == "__main__":
    lines_json_path = "data/processed_chunks/lines.json"
    log_file = "shakespeare_data_analysis.log"
    
    logger = setup_logging(log_file)
    logger.info(f"Starting analysis of {lines_json_path}")
    analyze_shakespeare_data(lines_json_path, logger)
    logger.info(f"Analysis complete. Results saved to {log_file}")
    print(f"Analysis complete. Results saved to {log_file}")