import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Tuple, Dict, Optional
from datetime import datetime

from follow_the_leaders.secret_vars import SEC_HEADERS


class Form13FComparator:
    BASE_URL = "https://data.sec.gov/submissions/CIK{}.json"
    SEC_HEADERS = SEC_HEADERS

    def __init__(
        self,
        cik: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        self.cik = cik.zfill(10)
        self.submissions = None

        self.start_date = start_date
        self.end_date = end_date

    def _fetch_submissions(self) -> None:
        url = self.BASE_URL.format(self.cik)
        r = requests.get(url, headers=self.SEC_HEADERS)
        r.raise_for_status()
        self.submissions = r.json()

    def _get_recent_13f_urls(self, count=2) -> List:
        """Return URLs to the infoTable XMLs for the most recent filings."""
        if self.submissions is None:
            self._fetch_submissions()

        forms = self.submissions["filings"]["recent"]
        urls = []
        for i, form in enumerate(forms["form"]):
            if form == "13F-HR":
                accession = forms["accessionNumber"][i].replace("-", "")
                filing_date = forms["filingDate"][i]

                filing_dt = datetime.strptime(filing_date, "%Y-%m-%d")
                if self.start_date and filing_dt < self.start_date:
                    continue
                if self.end_date and filing_dt > self.end_date:
                    continue

                base_url = f"https://www.sec.gov/Archives/edgar/data/{int(self.cik)}/{accession}"
                index_url = f"{base_url}/index.json"
                r = requests.get(index_url, headers=self.SEC_HEADERS)
                r.raise_for_status()
                files = r.json()["directory"]["item"]

                for f in files:
                    name = f["name"].lower()
                    if "info" in name and name.endswith(".xml"):
                        urls.append((f"{base_url}/{f['name']}", filing_date))
                        break

                if len(urls) == count:
                    break

        if len(urls) < 2:
            if len(urls) == 0:
                raise ValueError(
                    f"No 13F filings found for CIK {self.cik} within the given date range "
                    f"({self.start_date} ➝ {self.end_date})."
                )
            elif len(urls) == 1:
                raise ValueError(
                    f"Only 1 filing found for CIK {self.cik} within the given date range "
                    f"({self.start_date} ➝ {self.end_date}). Filing date: {urls[0][1]}"
                )
        return urls

    def _parse_xml(self, xml_text: str) -> pd.DataFrame:
        soup = BeautifulSoup(xml_text, "lxml-xml")
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
            holdings.append(
                {
                    "issuer": issuer,
                    "cusip": cusip,
                    "value_usd": value,
                    "shares": shares,
                }
            )
        return pd.DataFrame(holdings)

    def get_last_two_filings(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        urls = self._get_recent_13f_urls(count=2)
        filings = []
        for url, filing_date in urls:
            r = requests.get(url, headers=self.SEC_HEADERS)
            r.raise_for_status()
            df = self._parse_xml(r.text)
            df["filing_date"] = filing_date
            filings.append(df)

        return filings[0], filings[1]  # latest, previous

    def compare_filings(self) -> Dict[str, pd.DataFrame]:
        latest, previous = self.get_last_two_filings()

        latest_date = latest["filing_date"].iloc[0]
        prev_date = previous["filing_date"].iloc[0]

        print(f"Type of latest_date: {type(latest_date)}")

        # Index by CUSIP
        latest_idx = latest.set_index("cusip")
        previous_idx = previous.set_index("cusip")

        new_buys = latest_idx.loc[~latest_idx.index.isin(previous_idx.index)].copy()
        new_buys["rank_value"] = new_buys["value_usd"].rank(
            ascending=False, method="first"
        )

        exits = previous_idx.loc[~previous_idx.index.isin(latest_idx.index)].copy()

        common = latest_idx.join(
            previous_idx, lsuffix="_new", rsuffix="_old", how="inner"
        )

        increases = common[common["shares_new"] > common["shares_old"]].copy()
        increases["issuer"] = increases["issuer_new"]
        increases["rank_value"] = increases["value_usd_new"].rank(
            ascending=False, method="first"
        )

        reductions = common[common["shares_new"] < common["shares_old"]].copy()
        reductions["issuer"] = reductions["issuer_new"]

        return {
            "latest_date": latest_date,
            "previous_date": prev_date,
            "new_buys": new_buys.reset_index(),
            "exits": exits.reset_index(),
            "increases": increases.reset_index(),
            "reductions": reductions.reset_index(),
        }


def main() -> int:
    comparator = Form13FComparator("1045810")  # Nvidia CIK for the example

    # comparator = Form13FComparator("1045810", start_date=datetime(2024, 1, 1), end_date=datetime(2024, 12, 31))
    changes = comparator.compare_filings()

    print(f"Comparing filings: {changes['previous_date']} ➝ {changes['latest_date']}")

    print("\n New Buys (ranked by $ value):")
    print(
        changes["new_buys"].sort_values("rank_value")[
            ["issuer", "cusip", "shares", "value_usd", "rank_value"]
        ]
    )

    print("\n Increases (ranked by $ value):")
    print(
        changes["increases"].sort_values("rank_value")[
            [
                "issuer",
                "cusip",
                "shares_new",
                "shares_old",
                "value_usd_new",
                "rank_value",
            ]
        ]
    )

    print("\n Exits:")
    print(changes["exits"][["issuer", "cusip", "shares", "value_usd"]])

    print("\n Reductions:")
    print(
        changes["reductions"][
            ["issuer", "cusip", "shares_new", "shares_old", "value_usd_new"]
        ]
    )

    return 0


if __name__ == "__main__":
    main()
