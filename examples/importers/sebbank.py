import csv
import datetime
import re
from os import path
from dateutil.parser import parse

import beangulp
from beangulp import mimetypes
from beangulp.importers import csvbase
from beangulp.testing import main
from beangulp import utils

from beancount.core import amount
from beancount.core import data
from beancount.core import flags
from beancount.core.number import D

log = utils.logger(verbosity=1, err=True)


class SebBankCSVImporter(beangulp.Importer):
    """Importer for SEB Estonia CSV (kontovv) files."""
    
    def __init__(self, account_prefix, account_unknown="Equity:Opening-Balances"):
        self.account_prefix = account_prefix  # e.g., "Assets:EE:SEB"
        self.account_unknown = account_unknown

    def identify(self, filepath):
        mimetype, encoding = mimetypes.guess_type(filepath)
        if mimetype != "text/csv":
            return False
        with open(filepath) as fd:
            head = fd.read(256)

        # The CSV files are encoded in UTF-8 with a BOM, so we need to
        # decode it properly to handle the BOM.
        head = head.encode().decode("utf-8-sig")

        return head.startswith("Kliendi konto;Dokumendi number")

    def filename(self, filepath):
        return "seb." + path.basename(filepath)
    
    def account(self, filepath):
        # Extract account number from the first transaction in the file
        try:
            with open(filepath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                for row in reader:
                    account_number = row.get('Kliendi konto', '').strip('"')
                    if account_number:
                        # Take last 4 digits of account number for readability
                        account_suffix = account_number[-4:] if len(account_number) >= 4 else account_number
                        return f"{self.account_prefix}:{account_suffix}"
                    break
        except Exception:
            pass
        return self.account_prefix
    
    def date(self, filepath):
        """Extract the date of the last transaction in the CSV file."""
        try:
            with open(filepath, encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';')
                last_date = None
                for row in reader:
                    date_str = row.get('Kuupäev', '').strip('"')
                    if date_str:
                        try:
                            transaction_date = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
                            if last_date is None or transaction_date > last_date:
                                last_date = transaction_date
                        except ValueError:
                            continue
                return last_date
        except Exception:
            return super().date(filepath)
    
    def extract(self, filepath, existing):
        """Extract transactions from SEB CSV file."""
        entries = []
        
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for index, row in enumerate(reader):
                # Skip empty rows
                if not any(row.values()):
                    continue
                    
                meta = data.new_metadata(filepath, index)
                
                # Parse date
                date_str = row.get('Kuupäev', '').strip('"')
                if not date_str:
                    continue
                    
                try:
                    txn_date = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
                except ValueError:
                    log(f"Invalid date format: {date_str}")
                    continue
                
                # Parse amount and determine if debit or credit
                amount_str = row.get('Summa', '').replace(',', '.')
                debit_credit = row.get('Deebet/Kreedit (D/C)', '').strip('"')
                
                # Parse currency from CSV
                currency = row.get('Valuuta', '').strip('"')
                if not currency:
                    currency = 'EUR'  # Default fallback
                
                try:
                    amount_num = D(amount_str)
                    # If it's a debit (D), amount should be negative for our account
                    if debit_credit == 'D':
                        amount_num = -amount_num
                except (ValueError, TypeError):
                    log(f"Invalid amount: {amount_str}")
                    continue
                
                # Get the account number for this transaction
                account_number = row.get('Kliendi konto', '').strip('"')
                if account_number:
                    # Take last 4 digits of account number for readability
                    account_suffix = account_number[-4:] if len(account_number) >= 4 else account_number
                    main_account = f"{self.account_prefix}:{account_suffix}"
                else:
                    main_account = self.account_prefix
                
                # Create description from various fields
                description_parts = []
                
                # Add payee/payer name if available
                payee = row.get('Saaja/maksja nimi', '').strip('"')
                if payee and payee != 'SEB':
                    description_parts.append(payee)
                
                # Add explanation/description
                explanation = row.get('Selgitus', '').strip('"')
                if explanation:
                    description_parts.append(explanation)
                
                # Add transaction type if helpful
                txn_type = row.get('Tüüp', '').strip('"')
                if txn_type and txn_type not in ['MK', 'H']:  # Skip common types
                    description_parts.append(f"({txn_type})")
                
                description = ' | '.join(description_parts) if description_parts else 'SEB Transaction'
                
                # Determine counterparty account
                counterparty_account = self._get_counterparty_account(row)
                
                # Create transaction
                postings = [
                    data.Posting(
                        main_account,
                        amount.Amount(amount_num, currency),
                        None, None, None, None
                    ),
                    data.Posting(
                        counterparty_account,
                        amount.Amount(-amount_num, currency),
                        None, None, None, None
                    )
                ]
                
                # Add reference number as link if available
                links = set()
                ref_num = row.get('Arhiveerimistunnus', '').strip('"')
                if ref_num:
                    links.add(f"seb-{ref_num}")
                
                txn = data.Transaction(
                    meta, txn_date, flags.FLAG_OKAY, None, description,
                    data.EMPTY_SET, links, postings
                )
                
                entries.append(txn)
        
        return entries
    
    def _get_counterparty_account(self, row):
        """Determine the appropriate counterparty account based on transaction details."""
        
        # Check if there's a specific counterparty account
        counterparty_account_str = row.get('Saaja/maksja konto', '').strip('"')
        payee = row.get('Saaja/maksja nimi', '').strip('"')
        explanation = row.get('Selgitus', '').strip('"').lower()
        txn_type = row.get('Tüüp', '').strip('"')
        
        # Bank fees and charges (but not interest income)
        if (payee == 'SEB' or 'teenustasu' in explanation or 'intressi tulumaks' in explanation) and 'intresside väljamaks' not in explanation:
            return "Expenses:Bank:Fees"
        
        # Interest income
        if 'intresside väljamaks' in explanation:
            return "Income:Interest"
        
        # Card transactions - try to categorize
        if 'kaart' in explanation:
            if any(keyword in explanation for keyword in ['selver', 'kiosk', 'rimi', 'maxima']):
                return "Expenses:Food:Groceries"
            elif any(keyword in explanation for keyword in ['circle k', 'neste', 'alexela']):
                return "Expenses:Transportation:Fuel"
            elif any(keyword in explanation for keyword in ['takko', 'h&m', 'reserved']):
                return "Expenses:Clothing"
            elif any(keyword in explanation for keyword in ['netflix', 'apple', 'spotify']):
                return "Expenses:Entertainment:Subscriptions"
            elif any(keyword in explanation for keyword in ['hotell', 'hotel']):
                return "Expenses:Travel:Accommodation"
            else:
                return "Expenses:Unknown"
        
        # Salary or known income sources
        if any(keyword in explanation for keyword in ['puhkusetasu', 'palk', 'töötasu']):
            return "Income:Salary"
        
        # Utilities
        if any(keyword in payee.lower() for keyword in ['eesti energia', 'telia', 'elion']):
            return "Expenses:Utilities"
        
        # Insurance
        if 'kindlustus' in explanation.lower() or 'kindlustus' in payee.lower():
            return "Expenses:Insurance"
        
        # Loan payments
        if txn_type == 'L' or 'lep.' in explanation:
            return "Liabilities:Loan"
        
        # Transfers to/from known accounts
        if counterparty_account_str and counterparty_account_str.startswith('EE'):
            if 'martin' in payee.lower():
                return "Assets:Transfers"
            else:
                # Clean up payee name for account name (remove special characters)
                clean_payee = re.sub(r'[^A-Za-z0-9]', '', payee) if payee else "Unknown"
                return f"Assets:External:{clean_payee}" if clean_payee else "Assets:External:Unknown"
        
        # Donations
        if any(keyword in explanation.lower() for keyword in ['annetus', 'annetamine']):
            return "Expenses:Charity"
        
        # Default to unknown expenses for debits, unknown income for credits
        debit_credit = row.get('Deebet/Kreedit (D/C)', '').strip('"')
        if debit_credit == 'D':
            return "Expenses:Unknown"
        else:
            return "Income:Unknown"
    


if __name__ == "__main__":
    main(SebBankCSVImporter("Assets:EE:SEB"))



