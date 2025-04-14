import os
import json
from typing import List, Dict, Any, Optional
from modules.utils.logger import CustomLogger
from openai import OpenAI
from anthropic import Anthropic
import importlib.util


class SceneWriter:
    def __init__(
        self,
        config_path: str = "modules/playwright/config.py",
        expanded_story_path: str = "data/modern_play/expanded_story.json"
    ):
        self.logger = CustomLogger("SceneWriter")
        self.logger.info("Initializing SceneWriter")

        self.config = self._load_config(config_path)
        self.model_provider = self.config.get("model_provider", "openai")
        self.model_name = self.config.get("model_name", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.7)

        self.expanded_story_path = expanded_story_path
        self.output_dir = "data/modern_play/generated_scenes_claude2"
        os.makedirs(self.output_dir, exist_ok=True)

        self.openai_client = None
        self.anthropic_client = None
        self._init_model_client()

        self.story = self._load_json(self.expanded_story_path)

    def _load_config(self, path: str) -> Dict[str, Any]:
        try:
            spec = importlib.util.spec_from_file_location("config", path)
            if spec is None or spec.loader is None:
                raise ImportError("Could not load config")

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

    def _init_model_client(self):
        if self.model_provider == "anthropic":
            self.logger.info("Using Anthropic client")
            self.anthropic_client = Anthropic()
        else:
            self.logger.info("Using OpenAI client")
            self.openai_client = OpenAI()

    def _load_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading JSON from {path}: {e}")
            return {}

    def _build_prompt(self, act: str, scene_data: Dict[str, Any]) -> str:
        setting = scene_data.get("setting", "")
        characters = ", ".join(scene_data.get("characters", []))
        beats = "\n- ".join(scene_data.get("beats", []))
        functions = ", ".join(scene_data.get("dramatic_functions", []))
        voice_primers = "\n".join([f"{char}: {desc}" for char, desc in scene_data.get("voice_primers", {}).items()])

        return f"""
You are writing dramatic dialog for a play inspired by Shakespeare's structure, but using **modern American English**.

All dialog must be grounded in the following themes: legacy vs mortality, logic without wisdom, the price of silence, power as isolation, and rewriting history. Let these ideas subtly shape tone, pacing, and conflict throughout each scene. Character voices and beats are provided. Maintain emotional resonance and moral complexity.

The setting is: {setting}

The characters in this scene are: {characters}

Use the following dramatic beats to guide the progression of dialog:
- {beats}

Dramatic tones and functions: {functions}

Voice guidelines:
{voice_primers}

Guidelines:
- Write dialog in the style and structure of Shakespeare (use poetic structure, rhythm, and dramatic arc), such as in MacBeth, but in **modern American English**
- Avoid archaic or Elizabethan vocabulary
- Favor poetic forms such as iambic pentameter and rhymed couplets at emotional or dramatic high points; elsewhere lean toward open verse
- Mix in shorter spoken lines and back and forth between characters where appropriate
- Use long, extended speeches, similar to Shakespeare, where a character's explanation of motives or plans is relevant
- Break long speeches into multiple lines, as Shakespeare would
- Include simple stage directions like [Mortimer enters], [Edgar aside], etc. Keep stage directions short and sparse.
- Each scene should contain **between 1,200 and 1,500 words of spoken text**, not counting character names or stage directions
- Return only the formatted play script

Here is an example of the output format:

[Enter CHARACTER NAME with attendants.]

CHARACTER NAME
I speak today about the subject,
Not just any subject,
But the one upon which I am speaking.

[Exit CHARACTER NAME]
"""

    def _call_model(self, prompt: str) -> str:
        if self.model_provider == "anthropic" and self.anthropic_client:
            response = self.anthropic_client.messages.create(
                model=self.model_name,
                max_tokens=4000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            )
            from anthropic.types import TextBlock
            content = "".join(
                block.text for block in response.content
                if isinstance(block, TextBlock)
            )
            return content.strip()

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

    def generate_scenes(self):
        for scene in self.story.get("scenes", []):
            act = scene.get("act", "X")
            scene_num = scene.get("scene", "X")
            self.logger.info(f"Generating Act {act}, Scene {scene_num}")
            prompt = self._build_prompt(act, scene)
            try:
                dialog = self._call_model(prompt)
                filename = f"act_{act.lower()}_scene_{scene_num}"
                with open(os.path.join(self.output_dir, f"{filename}.md"), "w", encoding="utf-8") as f:
                    f.write(f"ACT {act}\n\nSCENE {scene_num}\n\n{dialog}")
                with open(os.path.join(self.output_dir, f"{filename}.json"), "w", encoding="utf-8") as f:
                    json.dump({"act": act, "scene": scene_num, "script": dialog}, f, indent=2)
            except Exception as e:
                self.logger.error(f"Failed to generate scene {act}.{scene_num}: {e}")
