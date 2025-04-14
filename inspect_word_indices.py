import json
import spacy

def _tokenize_line_spacy(text):
    """Tokenize the line as done in line_chunker.py (excluding punctuation and spaces, no merging)."""
    doc = nlp(text)
    tokens = [token.text for token in doc if not token.is_space and not token.is_punct]
    return tokens

def load_lines(path="data/processed_chunks/lines.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data["chunks"]

def find_line(chunks, title, act, scene, line):
    for chunk in chunks:
        if (
            chunk.get("title") == title
            and chunk.get("act") == act
            and chunk.get("scene") == scene
            and chunk.get("line") == int(line)
        ):
            return chunk
    return None

def inspect_loop():
    chunks = load_lines()
    print("\n=== Shakespeare Chunk Word Inspector (spaCy-aligned, no merging) ===")

    while True:
        print("\nEnter values to locate a line and return the words at a specific range.\n")

        title = input("Title: ").strip()
        act = input("Act (e.g. I): ").strip()
        scene = input("Scene (e.g. II): ").strip()
        line = input("Line number within scene: ").strip()
        word_index = input("Word index range (start,end): ").strip()

        try:
            start_idx, end_idx = map(int, word_index.split(","))
        except ValueError:
            print("Invalid word index format. Use start,end (e.g. 3,6).")
            continue

        chunk = find_line(chunks, title, act, scene, line)
        if not chunk:
            print("Line not found. Check your inputs.")
        else:
            words = _tokenize_line_spacy(chunk['text'])
            if start_idx < 0 or end_idx >= len(words):
                print(f"Invalid indices. Line only has {len(words)} words.")
            else:
                print("\nLine Text:")
                print(f"  {chunk['text']}")
                print("\nspaCy-Aligned Word Tokens:")
                print("  " + " | ".join(f"{i}:{w}" for i, w in enumerate(words)))
                print("\nSelected Words:")
                print("  " + " ".join(words[start_idx:end_idx + 1]))

        cont = input("\nContinue? (Y/N): ").strip().lower()
        if cont != "y":
            print("Goodbye!")
            break

if __name__ == "__main__":
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        print("spaCy model 'en_core_web_sm' not found. Install with:\n")
        print("    python -m spacy download en_core_web_sm\n")
        exit(1)

    inspect_loop()
