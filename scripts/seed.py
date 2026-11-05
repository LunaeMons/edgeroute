"""Load the CDN providers in data/cdns.json into the local database."""
import json
from pathlib import Path

from app import db
from app.cdns import repository
from app.cdns.schemas import CdnCreate

DATA = Path(__file__).resolve().parent.parent / "data" / "cdns.json"


def main() -> None:
    """Create the tables and insert any provider that is not there yet."""
    db.init_db()
    with db.connect() as conn:
        existing = {cdn["name"] for cdn in repository.list_cdns(conn)}
        for item in json.loads(DATA.read_text()):
            if item["name"] in existing:
                print(f"skip   {item['name']}")
                continue
            repository.create_cdn(conn, CdnCreate(**item))
            print(f"added  {item['name']}")


if __name__ == "__main__":
    main()
