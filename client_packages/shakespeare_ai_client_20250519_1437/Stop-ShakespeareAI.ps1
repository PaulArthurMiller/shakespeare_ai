# Configuration
$CONTAINER_NAME = "shakespeare-ai"

# Check if container exists
$containerExists = docker ps -a -q -f name=$CONTAINER_NAME
if (-not $containerExists) {
    Write-Host "Shakespeare AI is not running. No container to stop."
    Write-Host "Press Enter to close this window."
    Read-Host
    exit 0
}

# Stop the container
Write-Host "Stopping Shakespeare AI..."
docker stop $CONTAINER_NAME
if (-not $?) {
    Write-Host "Warning: Could not stop container. It might already be stopped."
}

# Remove the container
Write-Host "Removing container..."
docker rm $CONTAINER_NAME
if (-not $?) {
    Write-Host "Warning: Could not remove container."
    Write-Host "Trying to force remove..."
    docker rm -f $CONTAINER_NAME
    if (-not $?) {
        Write-Host "Error: Failed to remove the container. Please try manually with:"
        Write-Host "docker rm -f $CONTAINER_NAME"
    }
}

# Verify container is gone
$containerStillExists = docker ps -a -q -f name=$CONTAINER_NAME
if ($containerStillExists) {
    Write-Host "Warning: Container still exists. Please try to remove it manually with:"
    Write-Host "docker rm -f $CONTAINER_NAME"
} else {
    Write-Host "Shakespeare AI has been successfully stopped and removed."
}

Write-Host "Press Enter to close this window."
Read-Host