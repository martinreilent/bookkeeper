import sys
from os import path

sys.path.insert(0, path.dirname(__file__))

from importers.sebbank import SebBankCSVImporter

# Define your importers
CONFIG = [
    SebBankCSVImporter("Assets:SEB", False),
]