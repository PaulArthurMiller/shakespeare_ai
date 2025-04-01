"""
Text file cleaner script

This script removes blank lines or lines with just whitespace from a text file.
It creates a new cleaned file with the prefix 'cleaned_' by default.
"""

import argparse
import os
import sys

def clean_file(input_file, output_file=None, verbose=False):
    """
    Remove blank lines or lines with just whitespace from a text file.
    
    Args:
        input_file (str): Path to the input text file
        output_file (str, optional): Path to the output file. If None, adds 'cleaned_' prefix
        verbose (bool): If True, prints more information
        
    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    try:
        # If no output file is specified, create one with a 'cleaned_' prefix
        if not output_file:
            directory, filename = os.path.split(input_file)
            output_file = os.path.join(directory, f"cleaned_{filename}")
        
        # Track statistics
        total_lines = 0
        empty_lines = 0
        
        # Read the input file and write non-empty lines to the output file
        with open(input_file, 'r', encoding='utf-8') as in_file, open(output_file, 'w', encoding='utf-8') as out_file:
            for line in in_file:
                total_lines += 1
                
                # Check if line is empty or contains only whitespace
                if line.strip():
                    out_file.write(line)
                else:
                    empty_lines += 1
        
        # Create a success message
        message = (
            f"Cleaning complete!\n"
            f"Input file: {input_file}\n"
            f"Output file: {output_file}\n"
            f"Total lines processed: {total_lines}\n"
            f"Empty lines removed: {empty_lines}\n"
            f"Remaining lines: {total_lines - empty_lines}"
        )
        
        if verbose:
            print(message)
            
        return True, message
    
    except FileNotFoundError:
        error_msg = f"Error: The file '{input_file}' was not found."
        if verbose:
            print(error_msg)
        return False, error_msg
    
    except PermissionError:
        error_msg = f"Error: Permission denied when trying to access '{input_file}' or create '{output_file}'."
        if verbose:
            print(error_msg)
        return False, error_msg
    
    except Exception as e:
        error_msg = f"Error: An unexpected error occurred: {str(e)}"
        if verbose:
            print(error_msg)
        return False, error_msg

def main():
    """Run the script with hardcoded file paths."""
    input_file = 'data/raw_texts/complete_shakespeare_cleaned.txt'
    output_file = 'data/processed_texts/complete_shakespeare_ready.txt'
    
    # Make sure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"Cleaning file: {input_file}")
    print(f"Output will be saved to: {output_file}")
    
    success, message = clean_file(input_file, output_file, verbose=True)
    
    if not success:
        print(message)
        sys.exit(1)
    
    print("File cleaning completed successfully.")

if __name__ == "__main__":
    main()