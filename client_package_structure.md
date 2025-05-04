# Shakespeare AI - Client Package Structure

This document outlines the files and directories that should be included in the client package. This represents the cleaned version of the project with only the components necessary for running the application.

```
shakespeare_ai/
├── streamlit_ui.py              # Main Streamlit application
├── setup.py                     # Installation script
├── requirements.txt             # Package dependencies
├── README.md                    # Project documentation
├── INSTALLATION_GUIDE.md        # Detailed setup instructions
├── .env.template                # Environment variable template
│
├── modules/
│   ├── ui/                      # UI helper modules
│   │   ├── __init__.py
│   │   ├── config_manager.py    # Configuration management
│   │   ├── session_manager.py   # Translation session management
│   │   ├── file_helper.py       # File operations
│   │   ├── ui_translator.py     # Translator UI adapter
│   │   └── ui_playwright.py     # Playwright UI adapter
│   │
│   ├── playwright/              # Play generation modules
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration
│   │   ├── story_expander.py    # Expands story outlines
│   │   ├── scene_writer.py      # Generates scenes
│   │   └── artistic_adjuster.py # Refines content
│   │
│   ├── translator/              # Translation modules
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration
│   │   ├── translation_manager.py # Main controller
│   │   ├── assembler.py         # Assembles Shakespeare lines
│   │   ├── selector.py          # Selects candidate quotes
│   │   ├── scene_saver.py       # Saves translated scenes
│   │   ├── types.py             # Type definitions
│   │   └── rag_caller.py        # Interfaces with RAG
│   │
│   ├── rag/                     # RAG system
│   │   ├── __init__.py
│   │   ├── search_engine.py     # Handles search queries
│   │   ├── vector_store.py      # Interfaces with Chroma
│   │   ├── used_map.py          # Tracks used quotes
│   │   └── embeddings.py        # Embedding generation
│   │
│   ├── chunking/                # Text chunking modules (needed for search)
│   │   ├── __init__.py
│   │   ├── base.py              # Base chunker class
│   │   ├── line_chunker.py      # For reference only
│   │   ├── phrase_chunker.py    # Used by search engine
│   │   └── fragment_chunker.py  # Used by search engine
│   │
│   ├── validation/              # Validation modules
│   │   ├── __init__.py
│   │   └── validator.py         # Validates translations
│   │
│   ├── output/                  # Output generation
│   │   ├── __init__.py
│   │   ├── final_output_generator.py # Creates final documents
│   │   └── format_translated_play.py # Formatting functions
│   │
│   └── utils/                   # Utility modules
│       ├── __init__.py
│       ├── logger.py            # Logging utility
│       └── env.py               # Environment variables
│
├── embeddings/                  # Pre-built database (large)
│   └── chromadb_vectors/        # Chroma database files
│       ├── lines/               # Line embeddings
│       ├── phrases/             # Phrase embeddings
│       └── fragments/           # Fragment embeddings
│
├── data/                        # Data files
│   ├── processed_chunks/        # Pre-processed text chunks
│   │   ├── lines.json           # Line chunks
│   │   ├── phrases.json         # Phrase chunks
│   │   └── fragments.json       # Fragment chunks
│   │
│   ├── prompts/                 # Templates for playwright
│   │   ├── character_voices.json # Character voice definitions
│   │   └── scene_summaries.json # Scene summaries 
│   │
│   ├── templates/               # Story templates
│   │   └── default_play.json    # Default play template
│   │
│   └── modern_play/             # Modern play examples
│       └── modern_play_combined.md # Example play
│
├── outputs/                     # Output directories
│   ├── translated_scenes/       # For translated scenes
│   ├── test_run/                # For test outputs
│   └── section_translations/    # For section outputs
│
└── translation_sessions/        # Session storage
    └── README.md                # Explanation of session files
```

## Notes on Files and Directories

### Core Application Files
- `streamlit_ui.py` - The main Streamlit interface
- Setup and configuration files for easy installation

### Modules Directory
Contains all the code modules organized by functionality:
- `ui/` - User interface related code
- `playwright/` - Play generation code
- `translator/` - Translation code
- `rag/` - Retrieval-augmented generation system
- `chunking/` - Text chunking modules (needed for search)
- `validation/` - Validation related code
- `output/` - Output generation code
- `utils/` - Utility functions

### Embeddings Directory
Contains the pre-built Chroma database with vector embeddings.
This is one of the largest components and is required for the RAG system.

### Data Directory
Contains essential data files:
- Pre-processed text chunks that the RAG system uses
- Templates and configuration for the playwright
- Example play content

### Outputs Directory
Empty directories where the application will save its outputs.

### Translation Sessions Directory
Where translation session information is stored.

## Excluded Components

The following components used during development are not included:
- Raw text datasets used for training
- Text cleaning and extraction tools
- Embedding generation scripts (though the embedding module itself is included)
- Database building and management utilities
- Experimental and development scripts
- Test data and test scripts not required for operation