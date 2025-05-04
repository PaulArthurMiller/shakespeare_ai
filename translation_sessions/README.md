# Translation Sessions

This directory is used to store information about translation sessions in the Shakespeare AI application.

## What are Translation Sessions?

When you use the Translator functionality of Shakespeare AI, the system creates a "translation session" to track your progress. Each session has a unique ID and keeps track of:

- Which scenes have been translated
- When they were translated
- How many lines were translated
- Where the output files are stored
- The "used map" of previously used quotes

This information helps maintain continuity between translation runs and allows you to continue previous translation work.

## Session Files

For each translation session, a JSON file is created with the naming format:
```
{translation_id}_translation_info.json
```

These files contain metadata about the translation, not the actual translated content.

## Important Notes

- Do not delete these files while a translation is in progress
- The actual translated content is stored in the output directory (typically in `outputs/translated_scenes/`)
- You can view active translation sessions through the UI by selecting "Use Existing" in the Translation ID section

## Advanced Usage

For developers: The translation session system is managed by the `modules/ui/session_manager.py` module. Session IDs are generated automatically but can also be specified manually if needed.