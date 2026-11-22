"""Load the CDN providers listed in ``data/cdns.json`` into the local database.

Run it with ``make seed``. It is safe to run more than once: providers that already
exist are skipped, not duplicated.
"""

import json
from pathlib import Path

from sqlalchemy.orm import Session

from app import db
from app.cdns import repository
from app.cdns.schemas import CdnCreate

# Built from this file's location, so the script works from any working directory.
DATA = Path(__file__).resolve().parent.parent / "data" / "cdns.json"


def main() -> None:
    """Bring the schema up to date and insert every provider that is not there yet."""
    db.migrate()
    # ``session.begin()`` commits when the block succeeds and rolls back if it raises.
    with Session(db.get_engine()) as session, session.begin():
        existing = {cdn.name for cdn in repository.list_cdns(session)}
        for item in json.loads(DATA.read_text()):
            if item["name"] in existing:
                print(f"skip   {item['name']}")
                continue
            # Going through the CdnCreate model applies the same validation as the API.
            repository.create_cdn(session, CdnCreate(**item))
            print(f"added  {item['name']}")


# Run main() only when executed as a script, not when imported.
if __name__ == "__main__":
    main()
    db.dispose_engines()
