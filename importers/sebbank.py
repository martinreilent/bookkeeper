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

from account_mapper import AccountMapper

log = utils.logger(verbosity=1, err=True)


class SebBankCSVImporter(beangulp.Importer):
    """Importer for SEB Estonia CSV (kontovv) files."""
    
    def __init__(self, account_prefix, create_new_accounts=True):
        self.account_prefix = account_prefix  # e.g., "Assets:EE:SEB"
        self.create_new_accounts = create_new_accounts  # Whether to create new accounts for unique postings
        self.account_mapper = AccountMapper(bank_name="SEB")

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
                meta['__source__'] = str(row)
                
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
                        account=main_account,
                        units=amount.Amount(amount_num, currency),
                        cost=None, 
                        price=None, 
                        flag=None,
                        meta=None
                    ),
                    data.Posting(
                        account=counterparty_account,
                        units=amount.Amount(-amount_num, currency),
                        cost=None, 
                        price=None, 
                        flag=None,
                        meta=None
                    )
                ]
                
                # Add reference number as link if available
                links = set()
                ref_num = row.get('Arhiveerimistunnus', '').strip('"')
                if ref_num:
                    links.add(f"seb-{ref_num}")
                
                txn = data.Transaction(
                    meta=meta,
                    date=txn_date,
                    flag=flags.FLAG_OKAY,
                    payee=payee,
                    narration=description,
                    tags=data.EMPTY_SET,
                    links=links,
                    postings=postings
                )
                
                entries.append(txn)

        # filter out all unique accounts and prepend to array with data.open()
        # TODO make this better by
        # 1. Also checking existing entries for accounts
        # 2. Making sure that correct date is used for Open entries (incase csv is not ordered by date)
        # 3. Make it part of the same loop as entries, so that metadata index is correct
        unique_accs = {}
        if self.create_new_accounts:
            for entry in entries:
                for posting in entry.postings:
                    if posting.account not in unique_accs:
                        unique_accs[posting.account] = data.Open(
                                date=entry.date,
                                account=posting.account,
                                meta=data.new_metadata(filepath, 1),
                                currencies=[posting.units.currency],
                                booking=None,
                            )
                            
        return list(unique_accs.values()) + entries
    
    def _get_counterparty_account(self, row):
        """Determine the appropriate counterparty account based on transaction details."""
        
        return self.account_mapper.get_counterparty_account(
            payee=row.get('Saaja/maksja nimi', '').strip('"'),
            explanation=row.get('Selgitus', '').strip('"'),
            txn_type=row.get('Tüüp', '').strip('"'),
            debit_credit=row.get('Deebet/Kreedit (D/C)', '').strip('"'),
            counterparty_account_str=row.get('Saaja/maksja konto', '').strip('"')
        )
    


if __name__ == "__main__":
    main(SebBankCSVImporter("Assets:SEB"))



