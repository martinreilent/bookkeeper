# Beancount Account Open Directive Generators

This repository contains two scripts to automatically generate `open` account directives for Beancount by scanning existing `.beancount` files for account usage.

## Scripts Overview

### 1. Python Script (`generate_account_opens.py`)
**Recommended for most users** - More features and better error handling.

**Features:**
- Scans Beancount files for account names and currencies
- Can check against existing open directives to avoid duplicates
- Groups accounts by category (Assets, Liabilities, Income, Expenses, Equity)
- Supports multiple output formats (file, stdout, append mode)
- Customizable open dates
- Detailed error reporting and validation

### 2. Bash Script (`generate_account_opens.sh`)
**Simpler alternative** - Good for basic use cases and shell scripting.

**Features:**
- Lightweight bash implementation
- Basic account extraction and grouping
- Supports file or stdout output
- Customizable open dates

## Installation

No installation required. Simply make the scripts executable:

```bash
chmod +x generate_account_opens.py generate_account_opens.sh
```

## Usage

### Python Script Examples

```bash
# Basic usage - scan transactions.beancount and output to accounts.beancount
python3 generate_account_opens.py examples/transactions.beancount

# Output to stdout
python3 generate_account_opens.py examples/transactions.beancount --stdout

# Check against existing opens to avoid duplicates
python3 generate_account_opens.py examples/transactions.beancount --check-existing examples/accounts.beancount

# Custom output file and open date
python3 generate_account_opens.py examples/transactions.beancount -o my_accounts.beancount --open-date 2020-01-01

# Append to existing file
python3 generate_account_opens.py examples/transactions.beancount -a --output existing_accounts.beancount

# Get help
python3 generate_account_opens.py --help
```

### Bash Script Examples

```bash
# Basic usage - output to accounts.beancount
./generate_account_opens.sh examples/transactions.beancount

# Output to stdout
./generate_account_opens.sh examples/transactions.beancount -

# Custom output file and date
./generate_account_opens.sh examples/transactions.beancount my_accounts.beancount 2020-01-01

# Get help
./generate_account_opens.sh --help
```

## Output Format

Both scripts generate properly formatted Beancount open directives:

```beancount
;; Account opening directives
;; Generated from: examples/transactions.beancount

;; Assets accounts
1900-01-01 open Assets:EE:SEB:2010                  EUR
1900-01-01 open Assets:External:PAJUMARKO           EUR
1900-01-01 open Assets:Transfers                    EUR

;; Liabilities accounts  
1900-01-01 open Liabilities:Loan                    EUR

;; Income accounts
1900-01-01 open Income:Interest                     EUR
1900-01-01 open Income:Salary                       EUR

;; Expenses accounts
1900-01-01 open Expenses:Bank:Fees                  EUR
1900-01-01 open Expenses:Insurance                  EUR
```

## How It Works

1. **Account Detection**: Both scripts scan the input Beancount file for lines containing account names followed by amounts and currencies
2. **Extraction**: Account names are extracted using regex patterns that match the Beancount transaction format
3. **Grouping**: Accounts are grouped by their top-level category (Assets, Liabilities, Income, Expenses, Equity)
4. **Deduplication**: The Python script can optionally check against existing open directives to avoid duplicates
5. **Output**: Properly formatted open directives are generated with consistent spacing and organization

## Account Detection Pattern

The scripts look for lines in this format:
```
  Assets:EE:SEB:2010  -0.01 EUR
  Expenses:Bank:Fees   0.01 EUR
```

This matches the standard Beancount transaction posting format with:
- Leading whitespace
- Account name (starting with capital letter)
- Amount with currency code

## Integration with Existing Files

### Method 1: Include Generated File
Add this line to your main Beancount file:
```beancount
include "accounts.beancount"
```

### Method 2: Copy and Paste
Copy the generated open directives directly into your main Beancount file.

### Method 3: Append Mode (Python only)
Use the `--append` flag to add new opens to an existing accounts file:
```bash
python3 generate_account_opens.py new_transactions.beancount --append --output accounts.beancount
```

## Requirements

### Python Script
- Python 3.6 or later
- No external dependencies (uses only standard library)

### Bash Script  
- Bash 4.0 or later
- Standard Unix tools: `grep`, `sed`, `sort`, `wc`

## Example Workflow

1. Import new transactions into your Beancount file
2. Run the generator to find new accounts:
   ```bash
   python3 generate_account_opens.py transactions.beancount --check-existing accounts.beancount
   ```
3. Review the generated opens and add them to your accounts file
4. Validate your Beancount file: `bean-check transactions.beancount`

## Troubleshooting

### No accounts found
- Check that your Beancount file contains properly formatted transactions
- Ensure account names start with a capital letter and use the standard format
- Verify the file path is correct

### Missing accounts in output
- The Python script excludes accounts that already have open directives when using `--check-existing`
- Make sure the account names in your transactions exactly match the format: `Category:Subcategory:Account`

### Permission errors
- Make sure the scripts are executable: `chmod +x generate_account_opens.py`
- Check write permissions for the output directory

## Testing

Run the example script to see both generators in action:
```bash
./example_usage.sh
```

This will demonstrate various usage patterns and generate sample output files.

## Contributing

Feel free to submit issues or pull requests to improve these scripts. Common enhancement ideas:
- Support for more currency types
- Better account name normalization
- Integration with Beancount importers
- GUI interface

## License

These scripts are provided as-is for use with Beancount. Feel free to modify and distribute as needed.
