import os

# Adjust this to match your project's path
directory = "data/modern_play/generated_scenes_claude2"
output_path = "data/modern_play/modern_play_combined2.md"

# Sort files to ensure proper order: act_1_scene_1.md, etc.
scene_files = sorted(
    [f for f in os.listdir(directory) if f.endswith(".md")],
    key=lambda x: (int(x.split("_")[1]), int(x.split("_")[3].split(".")[0]))
)

# Combine all the markdown scene files
combined_script = ""
for filename in scene_files:
    with open(os.path.join(directory, filename), "r", encoding="utf-8") as f:
        combined_script += f.read().strip() + "\n\n"

# Save the full play to one file
with open(output_path, "w", encoding="utf-8") as f:
    f.write(combined_script)

print(f"Combined play saved to: {output_path}")
