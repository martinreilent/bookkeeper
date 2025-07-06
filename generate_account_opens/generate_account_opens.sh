#!/bin/bash

# Script to generate open account directives from a Beancount file
# Usage: ./generate_account_opens.sh <beancount_file> [output_file] [open_date]

set -euo pipefail

# Default values
DEFAULT_OUTPUT="accounts.beancount"
DEFAULT_DATE="1900-01-01"

# Function to show usage
usage() {
    cat << EOF
Usage: $0 <input_file> [output_file] [open_date]

Generate open account directives from a Beancount file.

Arguments:
  input_file   Path to the Beancount file to scan
  output_file  Output file for open directives (default: accounts.beancount)
  open_date    Date for opening accounts (default: 1900-01-01)

Examples:
  $0 transactions.beancount
  $0 transactions.beancount my_accounts.beancount 2020-01-01
  $0 transactions.beancount - 2020-01-01  # Output to stdout

EOF
}

# Check arguments
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
    exit 0
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-$DEFAULT_OUTPUT}"
OPEN_DATE="${3:-$DEFAULT_DATE}"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file '$INPUT_FILE' does not exist." >&2
    exit 1
fi

# Extract unique account names from the beancount file
# This regex looks for lines with account names followed by amounts
extract_accounts() {
    grep -E '^\s+[A-Z][A-Za-z0-9:_-]+\s+' "$INPUT_FILE" | \
    grep -E '\s+[A-Z]{3}\s*$' | \
    sed -E 's/^\s+([A-Z][A-Za-z0-9:_-]+)\s+.*$/\1/' | \
    sort -u
}

# Generate open directives
generate_opens() {
    local accounts_list="$1"
    
    echo ";; Account opening directives"
    echo ";; Generated from: $INPUT_FILE"
    echo ";; Generated on: $(date)"
    echo ""
    
    # Group accounts by category
    for category in Assets Liabilities Income Expenses Equity; do
        category_accounts=$(echo "$accounts_list" | grep "^$category:")
        if [ -n "$category_accounts" ]; then
            echo ";; $category accounts"
            echo "$category_accounts" | while IFS= read -r account; do
                if [ -n "$account" ]; then
                    printf "%-12s open %-35s EUR\n" "$OPEN_DATE" "$account"
                fi
            done
            echo ""
        fi
    done
}

# Main execution
echo "Scanning '$INPUT_FILE' for account names..." >&2

# Extract accounts
ACCOUNTS=$(extract_accounts)

if [ -z "$ACCOUNTS" ]; then
    echo "No accounts found in the input file." >&2
    exit 1
fi

ACCOUNT_COUNT=$(echo "$ACCOUNTS" | wc -l)
echo "Found $ACCOUNT_COUNT unique accounts." >&2

# Generate and output directives
if [ "$OUTPUT_FILE" = "-" ]; then
    # Output to stdout
    generate_opens "$ACCOUNTS"
else
    # Output to file
    generate_opens "$ACCOUNTS" > "$OUTPUT_FILE"
    echo "Written to '$OUTPUT_FILE' - $ACCOUNT_COUNT open directives generated." >&2
fi
