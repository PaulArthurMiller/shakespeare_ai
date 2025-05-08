# run_tests.py
import pytest
import sys
import os

def run_tests():
    """Run the test suite."""
    # Set environment variables
    os.environ["PYTHONPATH"] = os.path.abspath(".")
    
    # Run unit tests only by default
    args = ["-v", "-m", "not integration"]
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            # Run all tests
            args = ["-v"]
            os.environ["RUN_INTEGRATION_TESTS"] = "1"
        elif sys.argv[1] == "--integration":
            # Run integration tests only
            args = ["-v", "-m", "integration"]
            os.environ["RUN_INTEGRATION_TESTS"] = "1"
    
    # Run pytest
    return pytest.main(args)

if __name__ == "__main__":
    sys.exit(run_tests())