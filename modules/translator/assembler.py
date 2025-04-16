# modules/translator/assembler.py

import json
import re
import importlib.util
from typing import List, Dict, Any, Optional
from modules.translator.types import CandidateQuote
from modules.utils.logger import CustomLogger
from openai import OpenAI
from anthropic import Anthropic
from anthropic.types import TextBlock


class Assembler:
    def __init__(self, config_path: str = "modules/playwright/config.py"):
        self.logger = CustomLogger("Assembler")
        self.logger.info("Initializing Assembler")

        self.config = self._load_config(config_path)
        self.model_provider = self.config.get("model_provider", "openai")
        self.model_name = self.config.get("model_name", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.7)

        self.openai_client: Optional[OpenAI] = None
        self.anthropic_client: Optional[Anthropic] = None
        self._init_model_client()

    def _load_config(self, path: str) -> Dict[str, Any]:
        spec = importlib.util.spec_from_file_location("config", path)
        if not spec or not spec.loader:
            raise ImportError("Could not load configuration")

        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        return {
            key: getattr(config_module, key)
            for key in dir(config_module)
            if not key.startswith("__")
        }

    def _init_model_client(self):
        if self.model_provider == "anthropic":
            self.anthropic_client = Anthropic()
        else:
            self.openai_client = OpenAI()

    def assemble_line(self, modern_line: str, prompt_data: Dict[str, List[Dict[str, Any]]], max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """Main method to assemble a translated line using only the provided quotes."""
        self.logger.info("Beginning line assembly")
        self.logger.debug(f"Modern line: {modern_line}")
        retries = 0

        while retries <= max_retries:
            # Use escalation prompt after first failure
            if retries > 0:
                prompt = self._build_escalation_prompt(modern_line, prompt_data, retries)
                self.logger.info(f"Using escalation prompt (attempt {retries+1})")
            else:
                prompt = self._build_prompt(modern_line, prompt_data)
                
            response = self._call_model(prompt)
            parsed = self._extract_output(response)

            if parsed is None:
                self.logger.warning(f"Failed to parse LLM output on attempt {retries + 1}")
                retries += 1
                continue

            assembled_line, temp_ids = parsed["text"], parsed["temp_ids"]

            if self._mini_validate(assembled_line, temp_ids, prompt_data):
                self.logger.info("Mini-validation succeeded")
                return {
                    "text": assembled_line,
                    "temp_ids": temp_ids
                }

            self.logger.warning(f"Mini-validation failed on attempt {retries + 1} for line: '{modern_line}'")
            retries += 1

        self.logger.error(f"Assembler failed after max retries for line: '{modern_line}'")
        return None

    def _build_escalation_prompt(self, modern_line: str, quote_options: Dict[str, List[Dict[str, Any]]], retry_count: int) -> str:
        """Build a stronger prompt that emphasizes the strict requirements."""
        quote_list = []
        for form, options in quote_options.items():
            for opt in options:
                temp_id = opt.get("temp_id")
                text = opt.get("text", "").strip()
                score = opt.get("score", None)
                line = f"[{form.upper()}] {temp_id}: \"{text}\""
                if score is not None:
                    line += f" (score: {score:.4f})"
                quote_list.append(line)

        quotes_str = "\n".join(quote_list)
        
        # Stronger language for the escalation prompt
        emphasis = "⚠️ CRITICAL REQUIREMENT ⚠️" if retry_count == 2 else "IMPORTANT"
        
        return f"""
        {emphasis}: You are translating modern English to Shakespeare-style verse. Your task requires ABSOLUTE PRECISION.

        YOU MUST FOLLOW THESE REQUIREMENTS EXACTLY:
        1. Use ONLY the exact Shakespeare quotes provided - WORD FOR WORD, with no additions or modifications
        2. The temp_ids in your response MUST be listed IN THE EXACT ORDER they appear in your assembled line
        3. Do not add ANY words that aren't in the quotes
        4. Do not include ANY proper nouns 
        5. Return only the assembled line and the ordered list of temp_ids used

        Modern line to translate:
        "{modern_line}"

        Available Shakespeare quotes (choose 1-3):
        {quotes_str}

        Output your result in this JSON format:
        {{
        "text": "<your assembled line using EXACTLY the words from the quotes, keeping punctuation>",
        "temp_ids": ["first_quote_used", "second_quote_used", ...] // MUST MATCH THE ORDER IN YOUR TEXT
        }}
        """.strip()

    def _build_prompt(self, modern_line: str, quote_options: Dict[str, List[Dict[str, Any]]]) -> str:
        quote_list = []
        for form, options in quote_options.items():
            for opt in options:
                temp_id = opt.get("temp_id")
                text = opt.get("text", "").strip()
                score = opt.get("score", None)
                line = f"[{form.upper()}] {temp_id}: \"{text}\""
                if score is not None:
                    line += f" (score: {score:.4f})"
                quote_list.append(line)

        quotes_str = "\n".join(quote_list)

        return f"""
    You are a playwright assistant generating Shakespeare-style dialog using a modern play line and selected source quotes. You use quotes from Shakespeare as puzzle pieces, fit together to match as closely as possible the modern play line.

    Your job:
    - Translate the modern English line into dramatic Shakespearean verse.
    - Use ONLY the provided Shakespearean quotes, EXACTLY as written - NO modifications whatsoever.
    - You MUST use the entire Shakespearean quote as provided - do not omit any words from a quote you choose.
    - You may select 1 to 3 Shakespearean quotes (they can be lines, phrases, or fragments).
    - You may only combine whole Shakespearean quotes - no partial usage is allowed.
    - You may rearrange the order of the Shakespearean quotes but not change their internal wording.
    - No proper nouns may be used.
    - Return only one final line and the list of temp_ids for the Shakespearean quotes used, in order.

    Modern play line:
    "{modern_line}"

    Here are your options:
    {quotes_str}

    Output your result in the following JSON format:
    {{
    "text": "<your translated line using EXACTLY the text from the selected quotes>",
    "temp_ids": ["temp_id_1", "temp_id_2", ...]
    }}
    """.strip()

    def _call_model(self, prompt: str) -> str:
        if self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=1024,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            content = "".join(
                block.text for block in response.content
                if isinstance(block, TextBlock)
            )
            return content.strip()

        if self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                temperature=self.temperature,
                messages=[
                    {"role": "system", "content": "You are a playwright assistant generating lines from source quotes."},
                    {"role": "user", "content": prompt}
                ]
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""

        raise RuntimeError("No valid LLM client configured.")

    def _extract_output(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parses the LLM output and extracts:
        {
            "text": "assembled line",
            "temp_ids": ["temp_id_1", "temp_id_2"]
        }
        """
        try:
            # Strip markdown-style JSON blocks
            cleaned = re.sub(r"^```(?:json)?\n?|```$", "", response_text.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned)
            if "text" in data and "temp_ids" in data:
                return data
        except Exception as e:
            self.logger.warning(f"Error parsing JSON output: {e}")
        return None

    def _mini_validate(self, assembled_line: str, temp_ids: List[str], quote_data: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Ensure the returned temp_ids were in the original options, and the text only includes valid pieces."""
        # First check if all temp_ids are valid
        valid_ids = {q["temp_id"] for quotes in quote_data.values() for q in quotes}
        for cid in temp_ids:
            if cid not in valid_ids:
                self.logger.warning(f"Invalid temp_id in response: {cid}")
                return False

        # Get the texts for the temp_ids that were used
        used_texts = []
        for form, quotes in quote_data.items():
            for quote in quotes:
                if quote["temp_id"] in temp_ids:
                    used_texts.append(quote["text"])
                    self.logger.debug(f"Used text from {quote['temp_id']}: '{quote['text']}'")
        
        # Normalize texts for comparison
        def normalize_for_comparison(text):
            # Remove punctuation and extra spaces
            text = re.sub(r'[^\w\s]', '', text.lower())
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        
        # Normalize the assembled line and all quotes
        normalized_assembled = normalize_for_comparison(assembled_line)
        normalized_quotes = [normalize_for_comparison(text) for text in used_texts]
        
        # Build all possible orderings of the quotes and see if any match the assembled text
        import itertools
        for perm in itertools.permutations(normalized_quotes):
            combined = " ".join(perm)
            if normalized_assembled == combined:
                self.logger.debug(f"Assembled line matches exact combination of quotes: {perm}")
                return True
        
        self.logger.warning(f"Assembled line does not match any combination of quotes")
        self.logger.debug(f"Normalized assembled: '{normalized_assembled}'")
        self.logger.debug(f"Normalized quotes: {normalized_quotes}")
        return False

    def reformat_result(self, assembled: Dict[str, Any], references: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "text": assembled["text"],
            "temp_ids": assembled["temp_ids"],
            "references": references
        }
