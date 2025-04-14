import json
import pandas as pd
from collections import defaultdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load phrase and fragment chunks
def load_chunks(path):
    logging.info(f"Loading chunks from {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["chunks"]

phrase_data = load_chunks("data/processed_chunks/phrases.json")
fragment_data = load_chunks("data/processed_chunks/fragments.json")
line_data = load_chunks("data/processed_chunks/lines.json")

logging.info("Calculating fragment stats...")
fragment_lengths = [chunk["word_count"] for chunk in fragment_data]
fragments_below_3 = sum(1 for wc in fragment_lengths if wc < 3)
fragments_above_6 = sum(1 for wc in fragment_lengths if wc > 6)

logging.info("Calculating phrase-line match counts...")
phrase_full_line = 0
for idx, chunk in enumerate(phrase_data):
    if idx % 25000 == 0 and idx > 0:
        logging.info(f"Processed {idx} phrases...")
    line_match = next((line["text"].strip() for line in line_data if line["chunk_id"] == chunk["chunk_id"].replace("phrase_", "chunk_")), "")
    if chunk["text"].strip() == line_match:
        phrase_full_line += 1

logging.info("Mapping phrases and fragments per line...")
phrases_per_line = defaultdict(int)
fragments_per_line = defaultdict(int)

for idx, chunk in enumerate(phrase_data):
    if idx % 25000 == 0 and idx > 0:
        logging.info(f"Counted {idx} phrases per line...")
    key = (chunk["title"], chunk["act"], chunk["scene"], chunk["line"])
    phrases_per_line[key] += 1

for idx, chunk in enumerate(fragment_data):
    if idx % 25000 == 0 and idx > 0:
        logging.info(f"Counted {idx} fragments per line...")
    key = (chunk["title"], chunk["act"], chunk["scene"], chunk["line"])
    fragments_per_line[key] += 1

all_line_keys = {
    (line["title"], line["act"], line["scene"], line["line"]) for line in line_data
}

lines_with_no_fragments = len([key for key in all_line_keys if fragments_per_line[key] == 0])
lines_with_no_phrases = len([key for key in all_line_keys if phrases_per_line[key] == 0])

logging.info("Summarizing counts per line...")
phrase_count_summary = defaultdict(int)
fragment_count_summary = defaultdict(int)

for count in phrases_per_line.values():
    phrase_count_summary[count] += 1

for count in fragments_per_line.values():
    fragment_count_summary[count] += 1

summary_rows = [
    {"Metric": "Total Phrase Chunks", "Value": len(phrase_data)},
    {"Metric": "Total Fragment Chunks", "Value": len(fragment_data)},
    {"Metric": "Fragments with < 3 words", "Value": fragments_below_3},
    {"Metric": "Fragments with > 6 words", "Value": fragments_above_6},
    {"Metric": "Phrases that match full line", "Value": phrase_full_line},
    {"Metric": "Lines with 0 fragments", "Value": lines_with_no_fragments},
    {"Metric": "Lines with 0 phrases", "Value": lines_with_no_phrases},
]

for count, lines in sorted(phrase_count_summary.items()):
    summary_rows.append({"Metric": f"Lines with {count} phrases", "Value": lines})

for count, lines in sorted(fragment_count_summary.items()):
    summary_rows.append({"Metric": f"Lines with {count} fragments", "Value": lines})

logging.info("Saving summary to CSV...")
df_summary = pd.DataFrame(summary_rows)
df_summary.to_csv("data/processed_chunks/chunking_summary.csv", index=False)
logging.info("✅ Chunking summary written to: data/processed_chunks/chunking_summary.csv")
