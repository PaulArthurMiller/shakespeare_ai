# Get the directory where this script is located
$SCRIPT_DIR = $PSScriptRoot

# Configuration
$IMAGE_NAME = "shakespeare-ai:latest"
$CONTAINER_NAME = "shakespeare-ai"
$PORT = 8501

# Create the required directories right where the script is
mkdir -Force "$SCRIPT_DIR\embeddings" | Out-Null
mkdir -Force "$SCRIPT_DIR\outputs" | Out-Null
mkdir -Force "$SCRIPT_DIR\logs" | Out-Null
mkdir -Force "$SCRIPT_DIR\translation_sessions" | Out-Null

# Make sure the chromadb_vectors folder is in the right place
if (!(Test-Path "$SCRIPT_DIR\embeddings\chromadb_vectors") -and (Test-Path "$SCRIPT_DIR\chromadb_vectors")) {
    Write-Host "Moving database to correct location..."
    Move-Item "$SCRIPT_DIR\chromadb_vectors" "$SCRIPT_DIR\embeddings\"
}

# Check if the container is already running
$running = docker ps -q -f name=$CONTAINER_NAME
if ($running) {
    Write-Host "Shakespeare AI is already running!"
    Start-Process "http://localhost:$PORT"
    Write-Host "Press Enter to close this window."
    Read-Host
    exit 0
}

# Check if the image exists locally, if not pull it
try {
    docker image inspect $IMAGE_NAME | Out-Null
} catch {
    Write-Host "Downloading Shakespeare AI (this may take a few minutes)..."
    docker pull $IMAGE_NAME
}

# Check API keys
# ——————————————————————————————————————————————
# Load existing keys (if any), then prompt for any that are missing
$KEY_FILE = "$SCRIPT_DIR\api_keys.txt"
$OPENAI_API_KEY = $null
$ANTHROPIC_API_KEY = $null

if (Test-Path $KEY_FILE) {
    $keyFile = Get-Content $KEY_FILE
    foreach ($line in $keyFile) {
        if ($line -match '^OPENAI_API_KEY\s*=\s*["''](.+)["'']') {
            $OPENAI_API_KEY = $Matches[1]
        }
        if ($line -match '^ANTHROPIC_API_KEY\s*=\s*["''](.+)["'']') {
            $ANTHROPIC_API_KEY = $Matches[1]
        }
    }
}

# Prompt for any missing keys
if (-not $OPENAI_API_KEY) {
    Write-Host "Enter your OpenAI API key (or press Enter to skip):"
    $OPENAI_API_KEY = Read-Host
}
if (-not $ANTHROPIC_API_KEY) {
    Write-Host "Enter your Anthropic API key (or press Enter to skip):"
    $ANTHROPIC_API_KEY = Read-Host
}

# Write back both keys (overwrite file)
@"
OPENAI_API_KEY='$OPENAI_API_KEY'
ANTHROPIC_API_KEY='$ANTHROPIC_API_KEY'
"@ | Out-File -FilePath $KEY_FILE -Encoding UTF8
# ——————————————————————————————————————————————


# Start the Docker container
Write-Host "Starting Shakespeare AI..."
docker run -d `
    --name $CONTAINER_NAME `
    -p $PORT`:8501 `
    -e OPENAI_API_KEY="$OPENAI_API_KEY" `
    -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" `
    -v "${SCRIPT_DIR}:/app" `
    -v "${SCRIPT_DIR}\embeddings\chromadb_vectors:/app/embeddings/chromadb_vectors" `
    $IMAGE_NAME

# Open the browser to the application
Start-Sleep -Seconds 3
Start-Process "http://localhost:$PORT"

Write-Host "Shakespeare AI is now running!"
Write-Host "When you're finished, use the 'Stop Shakespeare AI' script."
Write-Host "Press Enter to close this window."
Read-Host