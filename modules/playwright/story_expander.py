import json
import os
import importlib.util
import re
from typing import Dict, Any, List, Optional
from modules.utils.logger import CustomLogger
from openai import OpenAI
from anthropic import Anthropic


class StoryExpander:
    def __init__(
        self,
        config_path: str = "modules/playwright/config.py",
        scene_summaries_path: str = "data/prompts/scene_summaries.json",
        character_voices_path: str = "data/prompts/character_voices.json"
    ) -> None:
        self.logger = CustomLogger("StoryExpander")
        self.logger.info("Initializing StoryExpander")

        self.config = self._load_config(config_path)
        self.model_provider: str = self.config.get("model_provider", "openai")
        self.model_name: str = self.config.get("model_name", "gpt-4o")
        self.temperature: float = self.config.get("temperature", 0.7)

        self.openai_client: Optional[OpenAI] = None
        self.anthropic_client: Optional[Anthropic] = None
        self._init_model_client()

        self.scene_summaries: Dict[str, Any] = self._load_json(scene_summaries_path)
        self.character_voices: Dict[str, str] = self._load_json(character_voices_path)
        self.thematic_guidelines: str = (
            "Global thematic instructions provided by the client. "
            "Ensure all scenes reflect these themes consistently."
        )

    def _load_config(self, path: str) -> Dict[str, Any]:
        spec = importlib.util.spec_from_file_location("config", path)
        if spec is None or spec.loader is None:
            raise ImportError("Could not load configuration")

        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)

        return {
            key: getattr(config_module, key)
            for key in dir(config_module)
            if not key.startswith("__")
        }

    def _load_json(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _init_model_client(self) -> None:
        if self.model_provider == "anthropic":
            self.anthropic_client = Anthropic()
        else:
            self.openai_client = OpenAI()

    def _build_prompt(self, scene_data: Dict[str, Any]) -> str:
        voice_descriptions = "\n".join(
            f"{char}: {desc}" for char, desc in self.character_voices.items()
        )

        return f"""
You are expanding detailed scene summaries into structured scene descriptions for a modern play styled like Shakespeare's Macbeth, but using contemporary American English.

Scene Overview:
{scene_data["overview"]}

Thematic Guidelines:
{self.thematic_guidelines}

Characters and their voice styles:
{voice_descriptions}

Setting:
{scene_data.get("setting", "Provide a rich, suitable setting.")}

Characters present:
{', '.join(scene_data["characters"])}

Additional Instructions:
{scene_data.get("additional_instructions", "None")}

Provide detailed expansions for this scene including:
- Rich setting description
- 3 to 5 clear dramatic beats directly based on the scene overview
- Dramatic function tags (e.g., #DIALOGUE_TURN, #SOLILOQUY)
- Specific onstage events (entrances, exits, notable actions)
- Voice primers for each character present

Output JSON strictly formatted as:
{{
  "act": "{scene_data["act"]}",
  "scene": {scene_data["scene"]},
  "setting": "...",
  "characters": ["..."],
  "voice_primers": {{"Character": "Primer"}},
  "dramatic_functions": ["#..."],
  "beats": ["..."],
  "onstage_events": ["..."]
}}
""".strip()

    def _clean_json_response(self, response: str) -> str:
        cleaned = re.sub(r"^```(?:json)?\n?|```$", "", response.strip(), flags=re.MULTILINE)
        return cleaned.strip()

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
                    {
  "role": "system",
  "content": (
    "You are a literary scene development assistant for a modern Shakespeare-inspired play. "
    "Your role is to expand scene summaries into fully structured dramatic outlines—deeply rooted in the play’s central themes.\n\n"

    "Thematic Guidelines (use throughout all expansions):\n\n"

    "1. Legacy vs. Mortality\n"
    "   - Mortimer’s obsession with leaving a legacy mirrors King Lear’s tragic misjudgment. "
    "Emphasize that true legacy is not controlled—it is entrusted.\n\n"

    "2. Logic Without Wisdom\n"
    "   - The Djinn embodies the dangers of cold rationality, like an AI fulfilling commands with flawless logic but no moral compass. "
    "It is Ariel without empathy, or Macbeth’s witches without malice. Highlight how Mortimer’s own desires are exposed as hollow.\n\n"

    "3. The Price of Silence\n"
    "   - Edgar’s passivity, Leila’s containment, and the philosopher’s stolen voice all show that silence enables oppression. "
    "The Djinn’s silencing is systemic, not cruel. Let characters confront or embody the tension between voice and silence.\n\n"

    "4. Power as Isolation\n"
    "   - Every ascent isolates. Mortimer sheds connections one by one—son, lover, allies—until he is left with only his illusions. "
    "Use power transitions to increase dramatic loneliness.\n\n"

    "5. Rewriting History / Information Control\n"
    "   - Mortimer’s erasure of his misdeeds parallels Othello and Richard III, but with a modern twist. "
    "He doesn’t justify his actions—he deletes them. Show how truth is manipulated or burned in service of legacy and control.\n\n"

    "Let each scene reflect one or more of these threads, even subtly. The audience should feel the play’s philosophical undercurrent even when it is not stated aloud."
  )
},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""

        return ""

    def expand_all_scenes(self) -> None:
        expanded_scenes: List[Dict[str, Any]] = []
        for scene_data in self.scene_summaries.get("scenes", []):
            try:
                self.logger.info(f"Expanding Act {scene_data['act']}, Scene {scene_data['scene']}")
                prompt = self._build_prompt(scene_data)
                expanded_scene_json = self._call_model(prompt)
                cleaned = self._clean_json_response(expanded_scene_json)
                expanded_scene = json.loads(cleaned)
                expanded_scenes.append(expanded_scene)
            except Exception as e:
                self.logger.error(f"Failed to expand scene {scene_data['act']}.{scene_data['scene']}: {e}")

        final_output = {"scenes": expanded_scenes}
        output_path = "data/modern_play/expanded_story2.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Expanded scenes saved to {output_path}")


if __name__ == "__main__":
    expander = StoryExpander()
    expander.expand_all_scenes()
