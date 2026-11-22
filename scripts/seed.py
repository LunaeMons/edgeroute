"""Load the CDN providers listed in ``data/cdns.json`` into the local database.

Run it with ``make seed``. It is safe to run more than once: providers that already
exist are skipped, not duplicated.
"""

import json
from pathlib import Path

from app import db
from app.cdns import repository
from app.cdns.schemas import CdnCreate

# Built from this file's location, so the script works from any working directory.
DATA = Path(__file__).resolve().parent.parent / "data" / "cdns.json"


def main() -> None:
    """Create the tables and insert every provider that is not there yet."""
    db.init_db()
    with db.connect() as conn:
        existing = {cdn["name"] for cdn in repository.list_cdns(conn)}
        for item in json.loads(DATA.read_text()):
            if item["name"] in existing:
                print(f"skip   {item['name']}")
                continue
            # Going through the CdnCreate model applies the same validation as the API.
            repository.create_cdn(conn, CdnCreate(**item))
            print(f"added  {item['name']}")


# Run main() only when executed as a script, not when imported.
if __name__ == "__main__":
    main()
