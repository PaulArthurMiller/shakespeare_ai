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

from modules.playwright.scene_writer import SceneWriter

def main():
    writer = SceneWriter(
        config_path="modules/playwright/config.py",
        expanded_story_path="data/modern_play/expanded_story.json"
    )
    writer.generate_scenes()
    print("Scene generation complete. Check 'data/modern_play/generated_scenes/' for output.")

if __name__ == "__main__":
    main()
