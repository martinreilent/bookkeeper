"""
Account mapping utilities for transaction categorization.

This module provides reusable account mapping logic that can be shared
across different bank importers to ensure consistent categorization.
"""
import re
from typing import Optional, Dict, Any


class AccountMapper:
    """
    Maps transaction details to appropriate Beancount account names.
    
    This class encapsulates the logic for categorizing transactions based on
    payee names, descriptions, transaction types, and other transaction metadata.
    """
    
    def __init__(self, bank_name: str = ""):
        """
        Initialize the account mapper.
        
        Args:
            bank_name: The name of the bank for bank-specific categorization
        """
        self.bank_name = bank_name.upper()
    
    def get_counterparty_account(self, 
                               payee: str = "",
                               explanation: str = "",
                               txn_type: str = "",
                               debit_credit: str = "",
                               counterparty_account_str: str = "",
                               **kwargs) -> str:
        """
        Determine the appropriate counterparty account based on transaction details.
        
        Args:
            payee: The payee/payer name
            explanation: Transaction description/explanation
            txn_type: Transaction type code
            debit_credit: Whether transaction is debit (D) or credit (C)
            counterparty_account_str: The counterparty's account number
            **kwargs: Additional transaction metadata
            
        Returns:
            The appropriate Beancount account name
        """
        # Normalize inputs
        payee = payee.strip() if payee else ""
        explanation = explanation.strip().lower() if explanation else ""
        txn_type = txn_type.strip() if txn_type else ""
        debit_credit = debit_credit.strip() if debit_credit else ""
        counterparty_account_str = counterparty_account_str.strip() if counterparty_account_str else ""
        
        # Bank fees and charges (but not interest income)
        if self._is_bank_fee(payee, explanation):
            return "Expenses:Bank:Fees"
        
        # Interest income
        if self._is_interest_income(explanation):
            return "Income:Interest"
        
        # Card transactions - try to categorize
        if self._is_card_transaction(explanation):
            return self._categorize_card_transaction(explanation)
        
        # Salary or known income sources
        if self._is_salary(explanation):
            return "Income:Salary"
        
        # Utilities
        if self._is_utilities(payee):
            return "Expenses:Utilities"
        
        # Insurance
        if self._is_insurance(payee, explanation):
            return "Expenses:Insurance"
        
        # Loan payments
        if self._is_loan_payment(txn_type, explanation):
            return "Liabilities:Loan"
        
        # Donations
        if self._is_donation(explanation):
            return "Expenses:Charity"
        
        # Transfers to/from known accounts
        if self._is_external_transfer(counterparty_account_str):
            return self._get_external_transfer_account(payee, debit_credit)
        
        # Default categorization
        return self._get_default_account(debit_credit)
    
    def _is_bank_fee(self, payee: str, explanation: str) -> bool:
        """Check if transaction is a bank fee."""
        bank_indicators = [self.bank_name.lower(), 'teenustasu', 'intressi tulumaks']
        payee_lower = payee.lower()
        
        # Bank fees but not interest income
        is_from_bank = any(indicator in payee_lower for indicator in bank_indicators if indicator)
        has_fee_keywords = any(keyword in explanation for keyword in ['teenustasu', 'intressi tulumaks'])
        is_not_interest = 'intresside väljamaks' not in explanation
        
        return (is_from_bank or has_fee_keywords) and is_not_interest
    
    def _is_interest_income(self, explanation: str) -> bool:
        """Check if transaction is interest income."""
        return 'intresside väljamaks' in explanation
    
    def _is_card_transaction(self, explanation: str) -> bool:
        """Check if transaction is a card transaction."""
        return 'kaart' in explanation
    
    def _categorize_card_transaction(self, explanation: str) -> str:
        """Categorize card transactions based on merchant/description."""
        # Grocery stores
        grocery_keywords = ['selver', 'kiosk', 'rimi', 'maxima']
        if any(keyword in explanation for keyword in grocery_keywords):
            return "Expenses:Food:Groceries"
        
        # Gas stations
        fuel_keywords = ['circle k', 'neste', 'alexela']
        if any(keyword in explanation for keyword in fuel_keywords):
            return "Expenses:Transportation:Fuel"
        
        # Clothing stores
        clothing_keywords = ['takko', 'h&m', 'reserved']
        if any(keyword in explanation for keyword in clothing_keywords):
            return "Expenses:Clothing"
        
        # Entertainment/Subscriptions
        entertainment_keywords = ['netflix', 'apple', 'spotify']
        if any(keyword in explanation for keyword in entertainment_keywords):
            return "Expenses:Entertainment:Subscriptions"
        
        # Hotels/Accommodation
        accommodation_keywords = ['hotell', 'hotel']
        if any(keyword in explanation for keyword in accommodation_keywords):
            return "Expenses:Travel:Accommodation"
        
        # Default for unrecognized card transactions
        return "Expenses:Unknown"
    
    def _is_salary(self, explanation: str) -> bool:
        """Check if transaction is salary or income."""
        salary_keywords = ['puhkusetasu', 'palk', 'töötasu']
        return any(keyword in explanation for keyword in salary_keywords)
    
    def _is_utilities(self, payee: str) -> bool:
        """Check if transaction is for utilities."""
        utility_keywords = ['eesti energia', 'telia', 'elion']
        payee_lower = payee.lower()
        return any(keyword in payee_lower for keyword in utility_keywords)
    
    def _is_insurance(self, payee: str, explanation: str) -> bool:
        """Check if transaction is insurance-related."""
        insurance_keywords = ['kindlustus', 'poliis']
        payee_lower = payee.lower()
        return (any(keyword in explanation for keyword in insurance_keywords) or
                any(keyword in payee_lower for keyword in insurance_keywords))
    
    def _is_loan_payment(self, txn_type: str, explanation: str) -> bool:
        """Check if transaction is a loan payment."""
        return txn_type == 'L' or 'lep.' in explanation
    
    def _is_donation(self, explanation: str) -> bool:
        """Check if transaction is a donation."""
        donation_keywords = ['annetus', 'annetamine']
        return any(keyword in explanation for keyword in donation_keywords)
    
    def _is_external_transfer(self, counterparty_account_str: str) -> bool:
        """Check if transaction is a transfer to/from external account."""
        return counterparty_account_str and counterparty_account_str.startswith('EE')
    
    def _get_external_transfer_account(self, payee: str, debit_credit: str) -> str:
        """Get account for external transfers."""
        if payee:
            # First replace spaces with hyphens, then remove other non-alphanumeric characters except hyphens
            clean_payee = re.sub(r'\s+', '-', payee.strip())  # Replace spaces with hyphens
            clean_payee = re.sub(r'[^A-Za-z0-9-]', '', clean_payee.upper())  # Remove other special chars but keep hyphens
        else:
            clean_payee = "Unknown"
        
        if debit_credit == 'D':
            # Debit means money going out, so it's a transfer from this account
            return f"Expenses:External:{clean_payee}"
        else:
            # Credit means money coming in, so it's a transfer to this account
            return f"Income:External:{clean_payee}"
    
    def _get_default_account(self, debit_credit: str) -> str:
        """Get default account based on debit/credit."""
        if debit_credit == 'D':
            return "Expenses:Unknown"
        else:
            return "Income:Unknown"


# Convenience function for backwards compatibility and simple usage
def get_counterparty_account(payee: str = "",
                           explanation: str = "",
                           txn_type: str = "",
                           debit_credit: str = "",
                           counterparty_account_str: str = "",
                           bank_name: str = "",
                           **kwargs) -> str:
    """
    Convenience function to get counterparty account without instantiating AccountMapper.
    
    Args:
        payee: The payee/payer name
        explanation: Transaction description/explanation
        txn_type: Transaction type code
        debit_credit: Whether transaction is debit (D) or credit (C)
        counterparty_account_str: The counterparty's account number
        bank_name: Name of the bank for bank-specific categorization
        **kwargs: Additional transaction metadata
        
    Returns:
        The appropriate Beancount account name
    """
    mapper = AccountMapper(bank_name)
    return mapper.get_counterparty_account(
        payee=payee,
        explanation=explanation,
        txn_type=txn_type,
        debit_credit=debit_credit,
        counterparty_account_str=counterparty_account_str,
        **kwargs
    )
