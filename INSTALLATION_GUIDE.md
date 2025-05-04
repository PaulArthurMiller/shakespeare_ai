# Shakespeare AI - Installation Guide

This guide will walk you through the simple process of installing and running the Shakespeare AI application on your system.

## System Requirements

- Windows 10 or 11, macOS 10.15+, or Linux
- Python 3.8 or higher
- 8GB RAM recommended
- Internet connection (for API access)

## Step-by-Step Installation

### 1. Install Python (if not already installed)

#### For Windows:
1. Download the latest Python installer from [python.org](https://www.python.org/downloads/)
2. Run the installer
3. **Important**: Check the box "Add Python to PATH" during installation
4. Click "Install Now"
5. Verify installation by opening PowerShell and typing:
   ```
   python --version
   ```

#### For macOS:
1. Install using Homebrew:
   ```
   brew install python
   ```
2. Or download from [python.org](https://www.python.org/downloads/)

#### For Linux:
```
sudo apt update
sudo apt install python3 python3-pip
```

### 2. Download and Extract Shakespeare AI

1. Unzip the provided Shakespeare AI package to a location of your choice
2. Open a terminal or PowerShell window
3. Navigate to the extracted folder:
   ```
   cd path\to\shakespeare_ai
   ```

### 3. Set Up a Virtual Environment (Recommended)

#### Windows:
```
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux:
```
python -m venv venv
source venv/bin/activate
```

### 4. Install Required Packages

```
pip install -r requirements.txt
```

### 5. Install spaCy Language Model

```
python -m spacy download en_core_web_sm
```

### 6. Configure API Keys

1. Create a file named `.env` in the main project directory
2. Add your API keys to this file:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## Running the Application

After installation, run the application with:

```
streamlit run streamlit_ui.py
```

The application should automatically open in your default web browser. If it doesn't, you can access it by navigating to:
```
http://localhost:8501
```

## Troubleshooting

### Common Issues:

1. **"Python command not found"**
   - Make sure Python is installed and added to your PATH
   - Try using `python3` instead of `python` on macOS/Linux

2. **"ImportError: No module found"**
   - Ensure you've activated the virtual environment
   - Try reinstalling dependencies: `pip install -r requirements.txt`

3. **"API Error"**
   - Check that your API keys are correctly set in the `.env` file
   - Verify your internet connection

4. **"ModuleNotFoundError: No module named 'en_core_web_sm'"**
   - Run: `python -m spacy download en_core_web_sm`

### Still Need Help?

If you encounter any issues during installation or runtime, please contact:
- Email: [paularthurmiller@gmail.com]
