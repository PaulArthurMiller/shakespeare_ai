# Save this as download_nltk_resources.py and run it once
import nltk

# Download all resources needed for the chunker
resources = [
    'punkt',
    'averaged_perceptron_tagger',
    'cmudict'
]

for resource in resources:
    print(f"Downloading {resource}...")
    nltk.download(resource)

print("All required NLTK resources downloaded successfully.")