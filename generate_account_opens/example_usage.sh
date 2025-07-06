#!/bin/bash

# Example usage script for the Beancount account open generators
# This script demonstrates both the Python and Bash versions

echo "=== Beancount Account Open Directive Generator Examples ==="
echo

# Check if the transactions file exists
TRANSACTIONS_FILE="examples/transactions.beancount"
if [ ! -f "$TRANSACTIONS_FILE" ]; then
    echo "Error: $TRANSACTIONS_FILE not found"
    exit 1
fi

echo "1. Using Python script to generate new opens (excluding existing ones):"
echo "   Command: python3 generate_account_opens.py $TRANSACTIONS_FILE --check-existing examples/accounts.beancount --stdout"
echo
python3 generate_account_opens.py $TRANSACTIONS_FILE --check-existing examples/accounts.beancount --stdout | head -10
echo "   ... (output truncated)"
echo

echo "2. Using Bash script to generate all opens:"
echo "   Command: ./generate_account_opens.sh $TRANSACTIONS_FILE -"
echo
./generate_account_opens.sh $TRANSACTIONS_FILE - | head -10
echo "   ... (output truncated)"
echo

echo "3. Generating to a file (Python):"
echo "   Command: python3 generate_account_opens.py $TRANSACTIONS_FILE -o new_accounts.beancount"
python3 generate_account_opens.py $TRANSACTIONS_FILE -o new_accounts.beancount
echo "   Generated file: new_accounts.beancount"
echo

echo "4. Generating with custom date (Bash):"
echo "   Command: ./generate_account_opens.sh $TRANSACTIONS_FILE custom_accounts.beancount 2020-01-01"
./generate_account_opens.sh $TRANSACTIONS_FILE custom_accounts.beancount 2020-01-01
echo "   Generated file: custom_accounts.beancount"
echo

echo "Generated files:"
ls -la *.beancount | grep -E "(new_accounts|custom_accounts)"
echo

echo "To clean up test files:"
echo "   rm -f new_accounts.beancount custom_accounts.beancount"
