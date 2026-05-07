"""Idempotent CSV-driven seeder for the Load catalog."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

from app.core.db import engine
from app.models.load import Load

SEED_PATH = Path(__file__).resolve().parent.parent / "seeds" / "loads.csv"


def _parse_row(row: dict[str, str]) -> Load:
    return Load(
        load_id=row["load_id"].strip(),
        origin=row["origin"].strip(),
        destination=row["destination"].strip(),
        pickup_datetime=datetime.fromisoformat(row["pickup_datetime"]),
        delivery_datetime=datetime.fromisoformat(row["delivery_datetime"]),
        equipment_type=row["equipment_type"].strip(),
        loadboard_rate=float(row["loadboard_rate"]),
        notes=row.get("notes") or None,
        weight=float(row["weight"]),
        commodity_type=row["commodity_type"].strip(),
        num_of_pieces=int(row["num_of_pieces"]),
        miles=float(row["miles"]),
        dimensions=row["dimensions"].strip(),
    )


def seed_loads(force: bool = False) -> int:
    """Insert loads from CSV. Returns number of rows inserted (or replaced)."""
    if not SEED_PATH.exists():
        return 0

    inserted = 0
    with Session(engine) as session:
        existing_ids = set(session.exec(select(Load.load_id)).all())
        with SEED_PATH.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                load = _parse_row(row)
                if load.load_id in existing_ids and not force:
                    continue
                if force and load.load_id in existing_ids:
                    session.merge(load)
                else:
                    session.add(load)
                inserted += 1
        session.commit()
    return inserted
