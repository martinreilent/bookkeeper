#!/usr/bin/env python3
"""
Script to scan a Beancount file and generate open account directives.

This script reads a Beancount file, extracts all account names used in transactions,
and generates corresponding 'open' directives that can be added to your main
Beancount file or accounts file.
"""

import re
import sys
from pathlib import Path
from typing import Set, Dict, List
from collections import defaultdict
import argparse


def extract_accounts_from_beancount(file_path: str) -> Dict[str, Set[str]]:
    """
    Extract all account names and currencies from a Beancount file.
    
    Returns:
        Dict mapping account names to set of currencies used
    """
    accounts = defaultdict(set)
    
    # Regex pattern to match account lines in transactions
    # Matches lines like "  Assets:EE:SEB:2010  -0.01 EUR"
    account_pattern = re.compile(r'^\s+([A-Z][A-Za-z0-9:_-]+)\s+[+-]?[\d,]+\.?\d*\s+([A-Z]{3})')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                # Skip comments and empty lines
                if line.strip().startswith(';') or not line.strip():
                    continue
                
                # Look for account lines in transactions
                match = account_pattern.match(line)
                if match:
                    account_name = match.group(1)
                    currency = match.group(2)
                    accounts[account_name].add(currency)
                    
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    
    return accounts


def check_existing_opens(file_path: str) -> Set[str]:
    """
    Check for existing open directives in the file to avoid duplicates.
    
    Returns:
        Set of account names that already have open directives
    """
    existing_opens = set()
    open_pattern = re.compile(r'^\s*\d{4}-\d{2}-\d{2}\s+open\s+([A-Z][A-Za-z0-9:_-]+)')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = open_pattern.match(line)
                if match:
                    existing_opens.add(match.group(1))
    except FileNotFoundError:
        # File doesn't exist, no existing opens
        pass
    except Exception as e:
        print(f"Warning: Could not read existing opens from '{file_path}': {e}", file=sys.stderr)
    
    return existing_opens


def generate_open_directives(accounts: Dict[str, Set[str]], 
                           existing_opens: Set[str] = None,
                           open_date: str = "1900-01-01") -> List[str]:
    """
    Generate open account directives for the given accounts.
    
    Args:
        accounts: Dict mapping account names to currencies
        existing_opens: Set of accounts that already have open directives
        open_date: Date to use for opening accounts
        
    Returns:
        List of open directive strings
    """
    if existing_opens is None:
        existing_opens = set()
    
    directives = []
    
    # Sort accounts by category and name for better organization
    sorted_accounts = sorted(accounts.keys())
    
    # Group accounts by their top-level category
    categories = defaultdict(list)
    for account in sorted_accounts:
        if account not in existing_opens:
            category = account.split(':')[0]
            categories[category].append(account)
    
    # Generate directives grouped by category
    for category in sorted(['Assets', 'Liabilities', 'Income', 'Expenses', 'Equity']):
        if category in categories:
            if directives:  # Add empty line between categories
                directives.append("")
            
            directives.append(f";; {category} accounts")
            
            for account in categories[category]:
                currencies = accounts[account]
                # Use the most common currency, or EUR as default
                primary_currency = 'EUR' if 'EUR' in currencies else list(currencies)[0]
                
                # Format with proper spacing for alignment
                directive = f"{open_date} open {account:<35} {primary_currency}"
                directives.append(directive)
    
    # Add any remaining categories not in the standard list
    remaining_categories = set(categories.keys()) - {'Assets', 'Liabilities', 'Income', 'Expenses', 'Equity'}
    for category in sorted(remaining_categories):
        if directives:
            directives.append("")
        
        directives.append(f";; {category} accounts")
        
        for account in categories[category]:
            currencies = accounts[account]
            primary_currency = 'EUR' if 'EUR' in currencies else list(currencies)[0]
            directive = f"{open_date} open {account:<35} {primary_currency}"
            directives.append(directive)
    
    return directives


def main():
    parser = argparse.ArgumentParser(
        description="Generate open account directives from a Beancount file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate opens for transactions.beancount and save to accounts.beancount
  python generate_account_opens.py transactions.beancount
  
  # Generate opens and print to stdout
  python generate_account_opens.py transactions.beancount --stdout
  
  # Check against existing opens in accounts.beancount
  python generate_account_opens.py transactions.beancount --check-existing accounts.beancount
  
  # Use custom open date
  python generate_account_opens.py transactions.beancount --open-date 2020-01-01
        """
    )
    
    parser.add_argument('input_file', 
                       help='Path to the Beancount file to scan')
    parser.add_argument('--output', '-o',
                       help='Output file for the open directives (default: accounts.beancount)')
    parser.add_argument('--stdout', 
                       action='store_true',
                       help='Print directives to stdout instead of file')
    parser.add_argument('--check-existing',
                       help='Path to existing accounts file to check for duplicate opens')
    parser.add_argument('--open-date',
                       default='1900-01-01',
                       help='Date to use for opening accounts (default: 1900-01-01)')
    parser.add_argument('--append', '-a',
                       action='store_true',
                       help='Append to output file instead of overwriting')
    
    args = parser.parse_args()
    
    # Validate input file
    if not Path(args.input_file).exists():
        print(f"Error: Input file '{args.input_file}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    # Extract accounts from the input file
    print(f"Scanning '{args.input_file}' for account names...", file=sys.stderr)
    accounts = extract_accounts_from_beancount(args.input_file)
    
    if not accounts:
        print("No accounts found in the input file.", file=sys.stderr)
        sys.exit(0)
    
    print(f"Found {len(accounts)} unique accounts.", file=sys.stderr)
    
    # Check for existing opens if requested
    existing_opens = set()
    if args.check_existing:
        print(f"Checking for existing opens in '{args.check_existing}'...", file=sys.stderr)
        existing_opens = check_existing_opens(args.check_existing)
        if existing_opens:
            print(f"Found {len(existing_opens)} existing open directives.", file=sys.stderr)
    
    # Generate open directives
    directives = generate_open_directives(accounts, existing_opens, args.open_date)
    
    if not directives:
        print("All accounts already have open directives.", file=sys.stderr)
        sys.exit(0)
    
    # Prepare output content
    header = [
        ";; Account opening directives",
        f";; Generated from: {args.input_file}",
        f";; Generated on: {Path(__file__).stat().st_mtime}",
        "",
    ]
    
    output_lines = header + directives
    output_content = '\n'.join(output_lines) + '\n'
    
    # Output results
    if args.stdout:
        print(output_content, end='')
    else:
        output_file = args.output or 'accounts.beancount'
        mode = 'a' if args.append else 'w'
        
        try:
            with open(output_file, mode, encoding='utf-8') as f:
                if args.append:
                    f.write('\n')  # Add newline before appending
                f.write(output_content)
            
            action = "Appended to" if args.append else "Written to"
            print(f"{action} '{output_file}' - {len([d for d in directives if d and not d.startswith(';')])} open directives generated.", file=sys.stderr)
            
        except Exception as e:
            print(f"Error writing to '{output_file}': {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
