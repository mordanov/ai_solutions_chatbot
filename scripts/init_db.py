"""CLI: initialise the relational database and optionally seed with sample data."""
import argparse
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chatbot.config import settings
from chatbot.data.models import Base
from chatbot.data.seed import seed


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialise the chatbot database")
    parser.add_argument(
        "--seed", action="store_true", help="Populate with sample data after creation"
    )
    parser.add_argument(
        "--database-url",
        default=settings.database_url,
        help="SQLAlchemy database URL (overrides DATABASE_URL env var)",
    )
    args = parser.parse_args()

    engine = create_engine(args.database_url)
    Base.metadata.create_all(engine)
    print(f"Tables created against {args.database_url}")

    if args.seed:
        with Session(engine) as session:
            seed(session)
        print("Sample data seeded.")


if __name__ == "__main__":
    sys.exit(main())
