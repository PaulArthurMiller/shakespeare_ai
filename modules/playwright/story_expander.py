import json
import os
from typing import Dict, Any, List, Optional
from modules.utils.logger import CustomLogger
from openai import OpenAI
from anthropic import Anthropic
import importlib.util


class StoryExpander:
    def __init__(
        self,
        config_path: str = "modules/playwright/config.py",
        act_overview_path: str = "data/prompts/act_overview.json",
        character_voices_path: str = "data/prompts/character_voices.json"
    ):
        self.logger = CustomLogger("StoryExpander")
        self.logger.info("Initializing StoryExpander")

        self.config = self._load_config(config_path)
        self.model_provider = self.config.get("model_provider", "openai")
        self.model_name = self.config.get("model_name", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.7)
        self.random_seed = self.config.get("random_seed", None)

        self.openai_client = None
        self.anthropic_client = None

        self._init_model_client()
        self.act_overviews = self._load_json(act_overview_path)
        self.character_voices = self._load_json(character_voices_path)

    def _load_config(self, path: str) -> Dict[str, Any]:
        try:
            spec = importlib.util.spec_from_file_location("config", path)
            if spec is None or spec.loader is None:
                raise ImportError("Could not load module spec or loader is missing")

            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)  # type: ignore[attr-defined]

            self.logger.info("Loaded configuration from config.py")
            return {
                key: getattr(config_module, key)
                for key in dir(config_module)
                if not key.startswith("__")
            }
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.logger.info(f"Loaded JSON data from {path}")
                return data
        except FileNotFoundError:
            self.logger.error(f"File not found: {path}")
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON format in file: {path}")
        return {}

    def _init_model_client(self):
        if self.model_provider == "anthropic":
            self.logger.info("Using Anthropic client")
            self.anthropic_client = Anthropic()
        else:
            self.logger.info("Using OpenAI client")
            self.openai_client = OpenAI()

    

    def _build_prompt(self, act: str, overview: str) -> str:
        voice_descriptions = "\n".join(
            [f"{char}: {desc}" for char, desc in self.character_voices.items()]
        )

        prompt = f"""
You are a story developer working on a five-act play, written in modern English but structured dramatically like Shakespeare's *Macbeth*. The tone should reflect psychological tension, moral complexity, and escalating tragedy.

Act {act}: {overview}

Characters and their voice styles:
{voice_descriptions}

Use the following guidance when expanding this act:
- Develop this act into **3–6 scenes**, balancing public confrontations, private introspections, and thematic pivots.
- Include **soliloquies** for characters facing moral dilemmas or emotional breakdowns.
- You may add **minor characters** for comic relief, exposition, or to enrich dramatic contrast—Shakespeare often does this.
- Keep character arcs consistent: if a character dies or exits irrevocably, do not return them in later acts.
- Consider callbacks to earlier scenes, symbols, or omens.
- Use Shakespearean devices such as **foreshadowing**, **reversals of fortune**, **visions**, **ghosts or spirits**, **irony**, **parallelism**, and **tragic recognition (anagnorisis)**.

Structure your output like this (in JSON):

{{
  "act": "{act}",
  "scenes": [
    {{
      "scene": 1,
      "setting": "...",
      "characters": ["..."],
      "voice_primers": {{"Character": "Description"}},
      "dramatic_functions": ["#DIALOGUE_TURN", "#SOLILOQUY", "#FORESHADOWING", etc.],
      "beats": ["..."],
      "onstage_events": ["entrances", "exits", "key actions", etc.]
    }},
    ...
  ]
}}
"""
        return prompt.strip()

    def _clean_json_response(self, response: str) -> str:
        import re
        cleaned = re.sub(r"^```(?:json)?\n?|\n?```$", "", response.strip(), flags=re.MULTILINE)
        return cleaned.strip()

    def expand_all(self) -> Dict[str, Any]:
        all_expanded = {}
        for act, overview in self.act_overviews.items():
            try:
                self.logger.info(f"Expanding Act {act}")
                prompt = self._build_prompt(act, overview)
                response = self._call_model(prompt)
                cleaned_response = self._clean_json_response(response)
                self.logger.debug(f"Cleaned response for Act {act}:{cleaned_response}")
                parsed = json.loads(cleaned_response)
                all_expanded[act] = parsed
            except Exception as e:
                self.logger.error(f"Error expanding Act {act}: {e}")

        try:
            os.makedirs("data/modern_play", exist_ok=True)
            with open("data/modern_play/expanded_story.json", "w", encoding="utf-8") as f:
                json.dump(all_expanded, f, indent=2, ensure_ascii=False)
            self.logger.info("Expanded story saved to data/modern_play/expanded_story.json")
        except Exception as e:
            self.logger.error(f"Failed to save expanded story: {e}")

        return all_expanded

    def _call_model(self, prompt: str) -> str:
        if self.model_provider == "anthropic" and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=2048,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            for block in response.content:
                if isinstance(block, dict) and 'text' in block:
                    return block['text'].strip()
            return str(response)

        elif self.openai_client:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a playwright assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""

        else:
            raise RuntimeError("No valid model client initialized")
