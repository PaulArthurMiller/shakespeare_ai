# main.py

# from modules.playwright.story_expander import StoryExpander

# def main():
#     expander = StoryExpander(
#         config_path="modules/playwright/config.py",
#         act_overview_path="data/prompts/act_overview.json",
#         character_voices_path="data/prompts/character_voices.json"
#     )
#     expanded_story = expander.expand_all()
#     print("Expansion complete. Check 'data/modern_play/expanded_story.json' for output.")

# if __name__ == "__main__":
#     main()

# main.py

# from modules.playwright.scene_writer import SceneWriter

# def main():
#     writer = SceneWriter(
#         config_path="modules/playwright/config.py",
#         expanded_story_path="data/modern_play/expanded_story2.json"
#     )
#     writer.generate_scenes()
#     print("Scene generation complete. Check 'data/modern_play/generated_scenes_claude2' for output.")

# if __name__ == "__main__":
#     main()

import os

def roman_to_int(roman: str) -> int:
    roman_map = {'i': 1, 'v': 5, 'x': 10}
    result = 0
    prev = 0
    for char in reversed(roman.lower()):
        value = roman_map.get(char, 0)
        if value < prev:
            result -= value
        else:
            result += value
            prev = value
    return result

directory = "data/modern_play/generated_scenes_claude2"
output_path = "data/modern_play/modern_play_combined2.md"

scene_files = sorted(
    [f for f in os.listdir(directory) if f.endswith(".md")],
    key=lambda x: (
        roman_to_int(x.split("_")[1]),
        int(x.split("_")[3].split(".")[0])
    )
)

combined_script = ""
for filename in scene_files:
    with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
        combined_script += f.read().strip() + "\n\n"

with open(output_path, "w", encoding="utf-8") as f:
    f.write(combined_script)

print(f"Combined play saved to: {output_path}")
