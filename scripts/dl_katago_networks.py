"""Downloads KataGo networks from https://katagotraining.org/networks/."""

import dataclasses
import pathlib
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup
from simple_parsing import ArgumentParser
from tqdm.auto import tqdm


@dataclasses.dataclass
class Config:
    """Configuration for the script."""

    download_dir: str = "/nas/ucb/k8/go-attack/katago-networks"

    dry_run: bool = False


def get_links() -> pd.Series:
    """Parses the network table from https://katagotraining.org/networks/."""
    r = requests.get("https://katagotraining.org/networks/")
    soup = BeautifulSoup(r.content, "html.parser")

    # Parse table as pandas dataframe
    # When parsing <a></a> tags, get the actual link instead of the text
    table = soup.find("table")
    for a in table.find_all("a"):  # type: ignore
        a.replace_with(a["href"])
    return (
        pd.read_html(str(table), header=0, flavor="bs4")[0]
        .set_index("Name")["Network File"]
        .dropna()
    )


def main(cfg: Config):
    """
    Downloads KataGo networks from https://katagotraining.org/networks/.
    Only downloads networks that have not already been downloaded.
    """
    links = get_links()

    # Filter out models that have already been downloaded
    links = links[
        ~links.index.isin(
            x.name.rstrip(".bin.gz")
            for x in pathlib.Path(cfg.download_dir).glob("*.bin.gz")
        )
    ]

    if cfg.dry_run:
        print(links)
        return

    link: str
    for link in tqdm(links):
        # Download the link into the download directory
        # Stream the download so we don't have to load the whole file into memory
        with requests.get(link, stream=True) as r:
            r.raise_for_status()
            with open(pathlib.Path(cfg.download_dir) / link.split("/")[-1], "wb") as f:
                for chunk in r.iter_content(chunk_size=2**20):  # 1MB chunks
                    f.write(chunk)

        # The KataGo server has a rate limit of 20r/m
        # Per https://github.com/katago/katago-server/blob/master/compose/production/nginx/default.conf.template # noqa: E501
        # So we will wait 3 seconds between each download
        time.sleep(3)


if __name__ == "__main__":
    # Parse config
    parser = ArgumentParser()
    parser.add_arguments(Config, dest="cfg")
    args = parser.parse_args()
    cfg: Config = args.cfg

    main(cfg)
