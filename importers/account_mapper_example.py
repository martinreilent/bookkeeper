"""
Example template showing how to use the AccountMapper in other bank importers.

This demonstrates how to integrate the shared account mapping logic
into different bank importers while allowing for bank-specific customizations.
"""

from .account_mapper import AccountMapper


class ExampleBankImporter:
    """Example template for using AccountMapper in other bank importers."""
    
    def __init__(self, account_prefix, bank_name=""):
        self.account_prefix = account_prefix
        # Initialize with bank-specific name for better categorization
        self.account_mapper = AccountMapper(bank_name=bank_name)
    
    def _get_counterparty_account(self, transaction_data):
        """
        Example of how to use AccountMapper in your importer.
        
        Args:
            transaction_data: Dictionary or object containing transaction details
            
        Returns:
            The appropriate Beancount account name
        """
        # Extract the relevant fields from your bank's transaction format
        # This will vary depending on your bank's CSV/data format
        
        return self.account_mapper.get_counterparty_account(
            payee=transaction_data.get('payee', ''),
            explanation=transaction_data.get('description', ''),
            txn_type=transaction_data.get('transaction_type', ''),
            debit_credit=transaction_data.get('debit_credit', ''),
            counterparty_account_str=transaction_data.get('counterparty_account', ''),
            # You can pass additional fields as needed
            # amount=transaction_data.get('amount'),
            # reference=transaction_data.get('reference'),
        )


class CustomizedBankImporter:
    """Example of extending AccountMapper with bank-specific logic."""
    
    def __init__(self, account_prefix, bank_name=""):
        self.account_prefix = account_prefix
        self.account_mapper = AccountMapper(bank_name=bank_name)
    
    def _get_counterparty_account(self, transaction_data):
        """
        Example showing how to add bank-specific logic while using the shared mapper.
        """
        
        # First try bank-specific mappings
        bank_specific_account = self._get_bank_specific_account(transaction_data)
        if bank_specific_account:
            return bank_specific_account
        
        # Fall back to the shared account mapper
        return self.account_mapper.get_counterparty_account(
            payee=transaction_data.get('payee', ''),
            explanation=transaction_data.get('description', ''),
            txn_type=transaction_data.get('transaction_type', ''),
            debit_credit=transaction_data.get('debit_credit', ''),
            counterparty_account_str=transaction_data.get('counterparty_account', ''),
        )
    
    def _get_bank_specific_account(self, transaction_data):
        """
        Add bank-specific account mapping logic here.
        
        Returns:
            Account name if a bank-specific mapping is found, None otherwise
        """
        # Example: Bank-specific merchant mappings
        payee = transaction_data.get('payee', '').lower()
        
        # Example bank-specific mappings
        if 'specific_bank_merchant' in payee:
            return "Expenses:BankSpecific:Category"
        
        # Return None to use the shared mapper
        return None


# Example usage in your main importer file:
"""
from .account_mapper_example import ExampleBankImporter

class YourBankImporter(ExampleBankImporter):
    def __init__(self, account_prefix):
        super().__init__(account_prefix, bank_name="YourBank")
    
    # Your bank-specific implementation...
"""
