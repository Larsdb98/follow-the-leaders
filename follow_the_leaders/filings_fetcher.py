import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from follow_the_leaders.secret_vars import SEC_HEADERS
from follow_the_leaders._logger import log_debug, log_info, log_error


class FilingsFetcher:
    """
    Unified fetcher for SEC filings (Form 4, 144, 13F, etc.) with local caching and purging.
    """

    BASE_URL = "https://data.sec.gov/submissions/CIK{}.json"
    SEC_HEADERS = SEC_HEADERS

    CACHE_DIR = Path("data/cache")
    CACHE_TTL_HOURS = 12  # Re-fetch every 12 hours
    PURGE_OLDER_THAN_DAYS = 7  # Remove cache files older than 7 days

    def __init__(self, cik: str, cache_dir: str | Path = None):
        self.cik = cik.zfill(10)
        self.submissions: Optional[dict] = None
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._purge_old_cache_files()  # Clean old cache entries

    # ─────────────────────────────────────────────
    # Cache helpers
    # ─────────────────────────────────────────────
    def _cache_path(self) -> Path:
        hashed = hashlib.md5(self.cik.encode()).hexdigest()
        return self.CACHE_DIR / f"{hashed}_submissions.json"

    def _load_cache(self) -> Optional[dict]:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if datetime.now() - mtime > timedelta(hours=self.CACHE_TTL_HOURS):
                return None
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            return None

    def _save_cache(self, data: dict) -> None:
        with open(self._cache_path(), "w") as f:
            json.dump(data, f)

    def _purge_old_cache_files(self):
        """Delete cache files older than PURGE_OLDER_THAN_DAYS."""
        now = datetime.now()
        removed = 0
        for file in self.CACHE_DIR.glob("*_submissions.json"):
            try:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if now - mtime > timedelta(days=self.PURGE_OLDER_THAN_DAYS):
                    file.unlink()
                    removed += 1
            except Exception:
                continue
        if removed > 0:
            log_info(f"FilingsFetcher :: Purged {removed} old cache file(s).")

    # ─────────────────────────────────────────────
    # SEC data fetch
    # ─────────────────────────────────────────────
    def _fetch_submissions(self) -> None:
        cached = self._load_cache()
        if cached:
            self.submissions = cached
            return

        log_info(f"FilingsFetcher :: Fetching fresh SEC data for CIK {self.cik}...")
        url = self.BASE_URL.format(self.cik)
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        self.submissions = r.json()
        self._save_cache(self.submissions)

    # ─────────────────────────────────────────────
    # Retrieve filings metadata
    # ─────────────────────────────────────────────
    def get_recent_filings(self, form_type: str, count: int = 5) -> List[Dict]:
        log_debug(f"FilingsFetcher :: Pulling the {count} most recent filings...")
        if self.submissions is None:
            self._fetch_submissions()

        filings = []
        recent = self.submissions["filings"]["recent"]

        for i, f_type in enumerate(recent["form"]):
            if f_type.upper() == form_type.upper():
                accession = recent["accessionNumber"][i].replace("-", "")
                filing_date = recent["filingDate"][i]
                base_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{accession}"
                index_url = f"{base_url}/index.json"

                try:
                    r = requests.get(index_url, headers=self.SEC_HEADERS)
                    r.raise_for_status()
                    files = r.json()["directory"]["item"]
                except Exception:
                    files = []

                filings.append(
                    {
                        "accession": accession,
                        "filing_date": filing_date,
                        "base_url": base_url,
                        "files": files,
                    }
                )

                if len(filings) >= count:
                    break

        if not filings:
            log_error(
                f"FilingsFetcher :: No filings found for {form_type} (CIK {self.cik})"
            )
            raise ValueError(f"No filings found for {form_type} (CIK {self.cik})")

        return filings

    # ─────────────────────────────────────────────
    # XML helper
    # ─────────────────────────────────────────────
    @staticmethod
    def _find_text(soup, tag_name: str) -> Optional[str]:
        tag = soup.find(tag_name)
        return tag.text.strip() if tag else None

    # ─────────────────────────────────────────────
    # Parse Form 4 (insider trades)
    # ─────────────────────────────────────────────
    def parse_form4(self, filing: Dict) -> pd.DataFrame:
        xml_file = next(
            (f for f in filing["files"] if f["name"].lower().endswith(".xml")), None
        )
        if not xml_file:
            raise ValueError("No XML file found for Form 4.")

        url = f"{filing['base_url']}/{xml_file['name']}"
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")

        insider_name = self._find_text(soup, "rptOwnerName")
        issuer_name = self._find_text(soup, "issuerName")

        trades = []
        for trans in soup.find_all("nonDerivativeTransaction"):
            trade = {
                "issuer": issuer_name,
                "insider": insider_name,
                "transaction_date": self._find_text(trans, "transactionDate"),
                "transaction_code": self._find_text(trans, "transactionCode"),
                "shares": self._find_text(trans, "transactionShares"),
                "price": self._find_text(trans, "transactionPricePerShare"),
            }
            trades.append(trade)

        df = pd.DataFrame(trades)
        df["filing_date"] = filing["filing_date"]
        df["form_type"] = "4"
        return df

    # ─────────────────────────────────────────────
    # Parse Form 144 (insider sales)
    # ─────────────────────────────────────────────
    def parse_form144(self, filing: Dict) -> pd.DataFrame:
        txt_file = next(
            (f for f in filing["files"] if f["name"].lower().endswith(".txt")), None
        )
        if not txt_file:
            raise ValueError("No .txt file found for Form 144.")

        url = f"{filing['base_url']}/{txt_file['name']}"
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()

        text = r.text
        snippet = text[:300].replace("\n", " ")

        df = pd.DataFrame(
            [
                {
                    "issuer": None,
                    "filing_url": url,
                    "summary": snippet,
                    "filing_date": filing["filing_date"],
                    "form_type": "144",
                }
            ]
        )

        return df


def main():
    """
    Quick test for the FilingsFetcher class.
    Tries to pull the latest Form 4 and 144 filings for NVIDIA (CIK 1045810).
    """
    cik = "1045810"  # NVIDIA
    fetcher = FilingsFetcher(cik)

    # Test caching and Form 4 parsing
    try:
        filings = fetcher.get_recent_filings("4", count=2)
        print(f"\n✅ Found {len(filings)} recent Form 4 filings for CIK {cik}")
        for f in filings:
            df = fetcher.parse_form4(f)
            print(df.head(), "\n")
    except Exception as e:
        print(f"⚠️ Error fetching Form 4: {e}")

    # Test Form 144 parsing
    try:
        filings = fetcher.get_recent_filings("144", count=1)
        print(f"\n✅ Found {len(filings)} recent Form 144 filings for CIK {cik}")
        df = fetcher.parse_form144(filings[0])
        print(df.head(), "\n")
    except Exception as e:
        print(f"⚠️ Error fetching Form 144: {e}")


if __name__ == "__main__":
    main()
