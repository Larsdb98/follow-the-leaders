import requests
import pandas as pd
from bs4 import BeautifulSoup
from follow_the_leaders.secret_vars import SEC_HEADERS


class FilingsFetcher:
    """
    Generalized SEC latest Form fetcher (13F, 4, 144, etc.)
    """

    BASE_URL = "https://data.sec.gov/submissions/CIK{}.json"
    SEC_HEADERS = SEC_HEADERS

    def __init__(self, cik: str):
        self.cik = cik.zfill(10)
        self.submissions = None

    def _fetch_submissions(self):
        url = self.BASE_URL.format(self.cik)
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        self.submissions = r.json()

    def _find_text(self, soup, tag_name):
        """Safe helper to extract text from an XML tag."""
        tag = soup.find(tag_name)
        return tag.text.strip() if tag else None

    def _get_latest_filing(self, form_type: str) -> dict:
        """
        Generic method to get metadata for the latest given form type.
        Returns a dict with { 'accession', 'date', 'url', 'form' }.
        """
        if self.submissions is None:
            self._fetch_submissions()

        forms = self.submissions["filings"]["recent"]

        for i, form in enumerate(forms["form"]):
            if form == form_type:
                accession = forms["accessionNumber"][i].replace("-", "")
                filing_date = forms["filingDate"][i]
                base_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{accession}"

                # Fetch index.json to list included files
                index_url = f"{base_url}/index.json"
                r = requests.get(index_url, headers=self.SEC_HEADERS)
                if r.status_code != 200:
                    continue

                files = r.json()["directory"]["item"]
                return {
                    "accession": accession,
                    "filing_date": filing_date,
                    "base_url": base_url,
                    "files": files,
                    "form": form,
                }

        raise ValueError(f"No {form_type} filing found for CIK {self.cik}")

    # ─────────────────────────────────────────────
    # PARSERS
    # ─────────────────────────────────────────────
    def parse_13f(self, filing: dict) -> pd.DataFrame:
        """Parse Form 13F infotable."""
        xml_file = next(
            (f for f in filing["files"] if "info" in f["name"].lower()), None
        )
        if not xml_file:
            raise ValueError("No infotable XML found.")
        url = f"{filing['base_url']}/{xml_file['name']}"
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")

        holdings = []
        for info in soup.find_all("infoTable"):
            holdings.append(
                {
                    "issuer": info.find_text("nameOfIssuer"),
                    "cusip": info.find_text("cusip"),
                    "value_usd": (
                        int(info.find_text("value")) * 1000
                        if info.find("value")
                        else None
                    ),
                    "shares": (
                        int(info.find_text("sshPrnamt"))
                        if info.find("sshPrnamt")
                        else None
                    ),
                }
            )

        df = pd.DataFrame(holdings)
        df["filing_date"] = filing["filing_date"]
        df["form_type"] = "13F-HR"
        return df

    def parse_form4(self, filing: dict) -> pd.DataFrame:
        """Parse insider trades from Form 4 XML."""
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

    def parse_form144(self, filing: dict) -> pd.DataFrame:
        """Parse Form 144 text (basic metadata only)."""
        text_file = next(
            (f for f in filing["files"] if f["name"].lower().endswith(".txt")), None
        )
        if not text_file:
            raise ValueError("No text file found for Form 144.")
        url = f"{filing['base_url']}/{text_file['name']}"
        return pd.DataFrame(
            [
                {
                    "filing_date": filing["filing_date"],
                    "form_type": "144",
                    "source_url": url,
                }
            ]
        )

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────
    def get_latest(self, form_type: str) -> pd.DataFrame:
        filing = self._get_latest_filing(form_type)
        if form_type == "13F-HR":
            return self.parse_13f(filing)
        elif form_type == "4":
            return self.parse_form4(filing)
        elif form_type == "144":
            return self.parse_form144(filing)
        else:
            raise ValueError(f"Unsupported form type: {form_type}")


def main():
    fetcher = FilingsFetcher("1321655")  # Palantir
    form4_df = fetcher.get_latest("4")
    print("Latest Form 4 filing:")
    print(form4_df.head())

    form144_df = fetcher.get_latest("144")
    print("Latest Form 144 filing:")
    print(form144_df.head())


if __name__ == "__main__":
    main()
