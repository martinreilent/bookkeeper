# Account Mapper Module

The `account_mapper.py` module provides reusable account mapping logic for Beancount importers. It helps categorize transactions consistently across different bank importers.

## Features

- **Shared categorization logic**: Use the same mapping rules across multiple bank importers
- **Bank-specific customization**: Support for bank-specific fee detection and categorization
- **Extensible design**: Easy to add new categorization rules in one place
- **Estonian language support**: Includes keywords and patterns for Estonian banks

## Usage

### Basic Usage

```python
from .account_mapper import AccountMapper

# Initialize with bank name for bank-specific categorization
mapper = AccountMapper(bank_name="SEB")

# Get account for a transaction
account = mapper.get_counterparty_account(
    payee="Selver",
    explanation="kaart ostukoht selver",
    txn_type="",
    debit_credit="D",
    counterparty_account_str=""
)
# Returns: "Expenses:Food:Groceries"
```

### Using in Importers

```python
class YourBankImporter(beangulp.Importer):
    def __init__(self, account_prefix):
        self.account_prefix = account_prefix
        self.account_mapper = AccountMapper(bank_name="YourBank")
    
    def _get_counterparty_account(self, transaction_data):
        return self.account_mapper.get_counterparty_account(
            payee=transaction_data['payee'],
            explanation=transaction_data['description'],
            # ... other fields
        )
```

### Convenience Function

For simple usage without creating an instance:

```python
from .account_mapper import get_counterparty_account

account = get_counterparty_account(
    payee="Netflix",
    explanation="kaart netflix subscription",
    debit_credit="D",
    bank_name="SEB"
)
# Returns: "Expenses:Entertainment:Subscriptions"
```

## Supported Categories

### Income
- `Income:Salary` - Salary and employment income
- `Income:Interest` - Interest from savings accounts
- `Income:External:*` - Transfers from external accounts

### Expenses
- `Expenses:Food:Groceries` - Grocery stores (Selver, Rimi, Maxima, etc.)
- `Expenses:Transportation:Fuel` - Gas stations (Circle K, Neste, Alexela)
- `Expenses:Clothing` - Clothing stores (H&M, Reserved, Takko)
- `Expenses:Entertainment:Subscriptions` - Digital subscriptions (Netflix, Spotify, Apple)
- `Expenses:Travel:Accommodation` - Hotels and accommodation
- `Expenses:Utilities` - Utilities (Eesti Energia, Telia, Elion)
- `Expenses:Insurance` - Insurance payments
- `Expenses:Bank:Fees` - Bank fees and charges
- `Expenses:Charity` - Donations
- `Expenses:External:*` - Transfers to external accounts
- `Expenses:Unknown` - Unrecognized expenses

### Liabilities
- `Liabilities:Loan` - Loan payments

## Customization

### Adding New Categories

To add new merchant categories, modify the `_categorize_card_transaction` method in `AccountMapper`:

```python
def _categorize_card_transaction(self, explanation: str) -> str:
    # Add new category
    pharmacy_keywords = ['apteek', 'pharmacy', 'benu']
    if any(keyword in explanation for keyword in pharmacy_keywords):
        return "Expenses:Health:Pharmacy"
    
    # ... existing code
```

### Bank-Specific Customization

Extend the `AccountMapper` class for bank-specific logic:

```python
class YourBankAccountMapper(AccountMapper):
    def _is_bank_fee(self, payee: str, explanation: str) -> bool:
        # Add bank-specific fee detection
        if 'your_bank_specific_fee' in explanation:
            return True
        return super()._is_bank_fee(payee, explanation)
```

## Migration from sebbank.py

The SEB bank importer has been updated to use this module. The functionality remains the same, but the categorization logic is now centralized and reusable.

## Testing

Test your categorization rules by importing the module:

```python
from account_mapper import AccountMapper

mapper = AccountMapper("SEB")
print(mapper.get_counterparty_account(
    payee="Selver", 
    explanation="kaart ostukoht selver tallinn",
    debit_credit="D"
))
```
