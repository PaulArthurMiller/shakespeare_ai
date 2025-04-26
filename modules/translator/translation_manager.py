from typing import List, Optional, Dict, Any, cast, Union
from modules.utils.logger import CustomLogger
from modules.translator.types import CandidateQuote
from modules.validation.validator import Validator
from modules.translator.rag_caller import RagCaller
from modules.translator.selector import Selector
from modules.translator.assembler import Assembler
from modules.rag.used_map import UsedMap


class TranslationManager:
    def __init__(self, logger: Optional[CustomLogger] = None):
        self.logger = logger or CustomLogger("TranslationManager")
        self.logger.info("Initializing TranslationManager")

        self.used_map: UsedMap = UsedMap(logger=self.logger)
        self.validator: Validator = Validator()
        self.rag: RagCaller = RagCaller(logger=self.logger)
        self.selector: Selector = Selector(used_map=self.used_map, validator=self.validator, logger=self.logger)
        self.assembler: Assembler = Assembler()

        self.translation_id: Optional[str] = None

    def _generate_translation_id(self) -> str:
        import uuid
        return str(uuid.uuid4())[:8]

    def start_translation_session(self, translation_id: Optional[str] = None):
        self.translation_id = translation_id or self._generate_translation_id()
        self.logger.info(f"Starting translation session: {self.translation_id}")
        self.used_map.load(self.translation_id)

    def translate_line(self, modern_line: str, selector_results: Dict[str, List[CandidateQuote]]) -> Optional[Dict[str, Any]]:
        if not self.translation_id:
            raise RuntimeError("Translation session not started. Call start_translation_session().")

        self.logger.info(f"Translating line: {modern_line}")

        try:
            # === STEP 1: Prompt Preparation ===
            self.logger.debug("STEP 1: Calling Selector.prepare_prompt_structure")
            min_options_per_level = 3  # Minimum quotes we want per level
            prompt_structure, temp_map = self.selector.prepare_prompt_structure(selector_results, min_options=min_options_per_level)
            
            # Count total valid options across all levels
            total_options = sum(len(options) for options in prompt_structure.values())
            
            # Check if we have enough options total (at least 3 across all levels)
            if total_options < 3:
                self.logger.warning(f"STEP 1 INITIAL: Only {total_options} valid candidates total. Attempting to retrieve more...")
                
                # Attempt to get more candidates with extended search - double the top_k
                extended_results = self.rag.retrieve_all(modern_line, top_k=20)
                
                # Try again with the extended results
                prompt_structure, temp_map = self.selector.prepare_prompt_structure(extended_results, min_options=min_options_per_level)
                
                # Count options again
                total_options = sum(len(options) for options in prompt_structure.values())
                
                if total_options < 1:
                    self.logger.warning("STEP 1 EXTENDED: Extended search still produced insufficient candidates. Trying hybrid search...")
                    
                    # Try hybrid search as a last resort
                    hybrid_results = self.rag.hybrid_search(modern_line, top_k=10)
                    
                    # FIX: Check if hybrid_results contains expected structure before proceeding
                    if not hybrid_results or not all(key in hybrid_results for key in ["line", "phrases", "fragments"]):
                        self.logger.error("STEP 1 FAILED: Hybrid search returned invalid or incomplete results")
                        return None
                        
                    prompt_structure, temp_map = self.selector.prepare_prompt_structure(hybrid_results, min_options=min_options_per_level)
                    
                    total_options = sum(len(options) for options in prompt_structure.values())
                    if total_options < 1:
                        self.logger.error("STEP 1 FAILED: All search methods produced no valid candidates.")
                        return None
                    else:
                        self.logger.info(f"STEP 1 HYBRID: Retrieved {total_options} valid candidates after hybrid search.")
                else:
                    self.logger.info(f"STEP 1 EXTENDED: Retrieved {total_options} valid candidates after extended search.")
            
            self.logger.debug("STEP 1 COMPLETE: Prompt structure and temp_map created.")

            # === STEP 2: LLM Assembly ===
            self.logger.debug("STEP 2: Calling Assembler.assemble_line")
            assembled_result = self.assembler.assemble_line(modern_line, prompt_structure)
            
            # If assembler fails after its internal retries, try hybrid search as a fallback
            if not assembled_result:
                self.logger.warning("STEP 2 REGULAR FAILED: Assembler failed after all retries. Attempting hybrid search fallback.")
                
                # Get new quotes using hybrid search
                self.logger.info("STEP 2 FALLBACK: Trying hybrid search for additional quotes")
                hybrid_results = self.rag.hybrid_search(modern_line, top_k=15)
                
                # FIX: Check if hybrid_results contains expected structure before proceeding
                if not hybrid_results or not all(key in hybrid_results for key in ["line", "phrases", "fragments"]):
                    self.logger.error("STEP 2 FALLBACK FAILED: Hybrid search returned invalid or incomplete results")
                    return None
                    
                # Process the hybrid results
                hybrid_prompt_structure, hybrid_temp_map = self.selector.prepare_prompt_structure(hybrid_results, min_options=min_options_per_level)
                
                # Check if we have new options
                total_hybrid_options = sum(len(options) for options in hybrid_prompt_structure.values())
                self.logger.info(f"STEP 2 FALLBACK: Found {total_hybrid_options} candidates via hybrid search")
                
                if total_hybrid_options > 0:
                    # Try one more assembly attempt with the hybrid results
                    self.logger.info("STEP 2 FALLBACK: Attempting assembly with hybrid search results")
                    assembled_result = self.assembler.assemble_line(modern_line, hybrid_prompt_structure)
                    
                    # Update temp_map if successful
                    if assembled_result:
                        self.logger.info("STEP 2 FALLBACK: Hybrid search assembly successful")
                        temp_map = hybrid_temp_map
                    else:
                        self.logger.error("STEP 2 FAILED: Both regular and hybrid assembly methods failed")
                        return None
                else:
                    self.logger.error("STEP 2 FAILED: Hybrid search produced no valid candidates")
                    return None
            
            self.logger.debug("STEP 2 COMPLETE: Assembler returned assembled_result.")

            # === STEP 3: Extract result and fix temp_ids format if needed ===
            assembled_text = assembled_result.get("text", "").strip()
            temp_ids_used = assembled_result.get("temp_ids", [])

            if isinstance(temp_ids_used, dict):
                self.logger.warning("STEP 3: LLM returned temp_ids as dict, converting to list.")
                temp_ids_used = list(temp_ids_used.values())

            if not assembled_text or not temp_ids_used:
                self.logger.warning("STEP 3 FAILED: Missing text or temp_ids in assembler output.")
                return None
            self.logger.debug("STEP 3 COMPLETE: Assembled text and temp_ids extracted.")
            
            # Log the actual assembled content for debugging
            self.logger.info(f"Assembled text: '{assembled_text}' using temp_ids: {temp_ids_used}")

            # === STEP 4: Validation of returned IDs ===
            self.logger.debug("STEP 4: Validating temp_ids_used and looking up candidates")
            valid_temp_ids = set(temp_map.keys())
            invalid_ids = [tid for tid in temp_ids_used if tid not in valid_temp_ids]
            if invalid_ids:
                self.logger.warning(f"STEP 4 FAILED: Invalid temp_ids in result: {invalid_ids}")
                return None

            used_candidates = [temp_map[cid] for cid in temp_ids_used]
            references = [c.reference for c in used_candidates]
            
            # Log references for debugging
            for i, ref in enumerate(references):
                self.logger.debug(f"Reference {i+1}: {ref}")
                
            self.logger.debug("STEP 4 COMPLETE: Used candidates and references extracted.")

            # === STEP 5: Line Validation ===
            self.logger.debug("STEP 5: Running final validator.validate_line")
            validation_result = self.validator.validate_line(assembled_text, references)
            if not validation_result:
                self.logger.warning("STEP 5 FAILED: Validator failed on assembled line.")
                return None
            self.logger.debug("STEP 5 COMPLETE: Validator confirmed line is valid.")

            # === STEP 6: Mark Used ===
            self.logger.debug("STEP 6: Updating used map with references.")
            for ref in references:
                # Create reference key from reference parts with better handling of null/None values
                title = ref.get('title', '')
                act = ref.get('act', '')
                scene = ref.get('scene', '')
                line = ref.get('line', '')
                
                # Create a consistent reference key
                ref_key = f"{title}|{act if act is not None else 'NULL'}|{scene if scene is not None else 'NULL'}|{line}"
                
                # Extract word indices
                word_index_str = ref.get("word_index", "")
                if word_index_str and isinstance(word_index_str, str):
                    try:
                        # Handle different word_index formats
                        word_indices = []
                        if "," in word_index_str:
                            start, end = map(int, word_index_str.split(","))
                            word_indices = list(range(start, end + 1))
                        elif "-" in word_index_str:
                            start, end = map(int, word_index_str.split("-"))
                            word_indices = list(range(start, end + 1))
                        else:
                            # Try single number case
                            try:
                                index = int(word_index_str.strip())
                                word_indices = [index]
                            except ValueError:
                                self.logger.warning(f"Invalid word_index format: {word_index_str}")
                                continue
                        
                        # Log the reference key and word indices for debugging
                        self.logger.debug(f"Marking used: [{ref_key}] -> {word_indices}")
                        
                        # Mark as used
                        self.used_map.mark_used(ref_key, word_indices)
                        
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Invalid word_index format: {word_index_str} - {e}")
                else:
                    self.logger.warning(f"Missing or invalid word_index in reference: {ref}")
            
            self.used_map.save()
            self.logger.debug("STEP 6 COMPLETE: Used map updated and saved.")

            # === STEP 7: Return Final Output ===
            self.logger.info("Line translated and validated successfully.")
            
            # Create the full reference information
            full_references = []
            for cid, ref in zip(temp_ids_used, references):
                full_ref = {
                    "temp_id": cid,
                    "title": ref.get("title", "Unknown"),
                    "act": ref.get("act", "Unknown"),
                    "scene": ref.get("scene", "Unknown"),
                    "line": ref.get("line", "Unknown"),
                    "word_index": ref.get("word_index", "0,0")
                }
                full_references.append(full_ref)
            
            return {
                "text": assembled_text,
                "temp_ids": temp_ids_used,  # Keep temp_ids for debugging
                "references": full_references,  # Use the improved references
                "original_modern_line": modern_line  # Store the original modern line
            }

        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            self.log_decision({
                "status": "error",
                "input": modern_line,
                "error": str(e)
            })
            return None

    def translate_group(self, modern_lines: List[str]) -> List[Dict[str, Any]]:
        """Translate a group of modern lines."""
        self.logger.info(f"Translating group of {len(modern_lines)} lines")
        results = []
        
        for line in modern_lines:
            selector_results = self.rag.retrieve_all(line)
            result = self.translate_line(line, selector_results)
            if result is not None:
                results.append(result)
        
        return results

    def translate_scene(self, scene_lines: List[str]) -> List[Dict[str, Any]]:
        self.logger.info(f"Starting scene translation: {len(scene_lines)} lines")
        translated_scene: List[Dict[str, Any]] = []

        for i, line in enumerate(scene_lines):
            self.logger.info(f"Translating line {i + 1}/{len(scene_lines)}")
            selector_results = self.rag.retrieve_all(line)
            translated = self.translate_line(line, selector_results)
            if translated:
                translated_scene.append(translated)
            else:
                self.logger.warning(f"Line {i + 1} failed translation and was skipped")

        self.logger.info(f"Completed scene translation: {len(translated_scene)} lines generated")
        return translated_scene

    def get_usage_map(self) -> Dict[str, Any]:
        return self.used_map.get_used_map()

    def log_decision(self, details: Dict[str, Any]) -> None:
        self.logger.debug(f"Decision Log: {details}")