import requests
import pandas as pd
from bs4 import BeautifulSoup

from follow_the_leaders.secret_vars import SEC_HEADERS


class Form13FFetcher:
    """
    Fetcher + Parser for SEC Form 13F filings.

    Example:
        fetcher = Form13FFetcher("1067983")  # CIK for Berkshire Hathaway
        df = fetcher.get_latest_holdings()
        print(df.head())
    """

    BASE_URL = "https://data.sec.gov/submissions/CIK{}.json"
    SEC_HEADERS = SEC_HEADERS

    def __init__(self, cik: str):
        # SEC requires 10-digit, zero-padded CIKs
        self.cik = cik.zfill(10)
        self.submissions = None

    def _fetch_submissions(self) -> None:
        """Get all submissions metadata for this CIK."""
        url = self.BASE_URL.format(self.cik)
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        self.submissions = r.json()

    def _get_latest_13f_url(self) -> str:
        """Find the URL of the latest 13F XML information table."""
        if self.submissions is None:
            self._fetch_submissions()

        forms = self.submissions["filings"]["recent"]
        for i, form in enumerate(forms["form"]):
            if form == "13F-HR":  # holdings report
                accession = forms["accessionNumber"][i].replace("-", "")
                base_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{accession}"

                # Look inside the Index.json for actual file names
                index_url = f"{base_url}/index.json"
                r = requests.get(index_url, headers=self.SEC_HEADERS)
                r.raise_for_status()
                files = r.json()["directory"]["item"]

                # Try to find the infotable XML
                for f in files:
                    name = f["name"].lower()
                    if "info" in name and name.endswith(".xml"):
                        return f"{base_url}/{f['name']}"

                raise ValueError("No infotable XML found in the filing.")

        raise ValueError("No 13F-HR filing found for this CIK.")

    def _parse_xml(self, xml_text: str) -> pd.DataFrame:
        """Parse the 13F XML infoTable into a DataFrame."""
        soup = BeautifulSoup(xml_text, "xml")
        holdings = []

        for info in soup.find_all("infoTable"):
            issuer = (
                info.find("nameOfIssuer").text if info.find("nameOfIssuer") else None
            )
            cusip = info.find("cusip").text if info.find("cusip") else None
            value = int(info.find("value").text) * 1000 if info.find("value") else None
            shares = (
                int(info.find("sshPrnamt").text) if info.find("sshPrnamt") else None
            )
            share_type = (
                info.find("sshPrnamtType").text if info.find("sshPrnamtType") else None
            )
            putcall = info.find("putCall").text if info.find("putCall") else None

            holdings.append(
                {
                    "issuer": issuer,
                    "cusip": cusip,
                    "value_usd": value,
                    "shares": shares,
                    "share_type": share_type,
                    "put_call": putcall,
                }
            )

        return pd.DataFrame(holdings)

    def get_latest_holdings(self) -> pd.DataFrame:
        """Fetch and parse the latest 13F filing into a DataFrame."""
        xml_url = self._get_latest_13f_url()
        r = requests.get(xml_url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        return self._parse_xml(r.text)


def main():
    fetcher = Form13FFetcher("1045810")  # nvidia:  0001045810, berkshire: 1067983
    df = fetcher.get_latest_holdings()

    print(df.head())


if __name__ == "__main__":
    main()
