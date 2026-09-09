import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.services.vision.field_validation.ingest import run_field_ingestion_cli

if __name__ == "__main__":
    run_field_ingestion_cli()
