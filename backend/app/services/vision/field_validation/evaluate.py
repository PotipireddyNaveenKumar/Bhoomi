import sys
import os

# Delegate directly to runner script
from backend.scripts.evaluate_field_validation import run_field_validation_audit

if __name__ == "__main__":
    run_field_validation_audit()
