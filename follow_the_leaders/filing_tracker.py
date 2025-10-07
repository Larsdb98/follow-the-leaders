import pandas as pd
from pathlib import Path
from datetime import datetime


class FilingTracker:
    def __init__(self, log_path: str | Path = "data/processed_filings.csv"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        if self.log_path.exists():
            self.df = pd.read_csv(self.log_path, dtype=str)
        else:
            self.df = pd.DataFrame(
                columns=[
                    "cik",
                    "form_type",
                    "accession_number",
                    "filing_date",
                    "processed_at",
                ]
            )

    def is_new_filing(self, cik: str, form_type: str, accession_number: str) -> bool:
        """Check if a filing has already been processed."""
        match = (
            (self.df["cik"] == cik)
            & (self.df["form_type"] == form_type)
            & (self.df["accession_number"] == accession_number)
        )
        return not match.any()

    def log_filing(
        self, cik: str, form_type: str, accession_number: str, filing_date: str
    ):
        """Record a new filing as processed."""
        new_entry = {
            "cik": cik,
            "form_type": form_type,
            "accession_number": accession_number,
            "filing_date": filing_date,
            "processed_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.df = pd.concat([self.df, pd.DataFrame([new_entry])], ignore_index=True)
        self.df.to_csv(self.log_path, index=False)
