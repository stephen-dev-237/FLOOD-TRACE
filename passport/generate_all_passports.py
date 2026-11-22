import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from reconstruction.exposure_engine import (
    reconstruct_exposure
)

from passport.passport_generator import (
    generate_passport,
    save_passport
)


FLEET_DIR = (
    PROJECT_ROOT / "fleet"
)

QUEUE_FILE = (
    FLEET_DIR /
    "floodtrace_inspection_queue.csv"
)


def main():

    fleet = pd.read_csv(
        QUEUE_FILE
    )

    print("\nGenerating asset passports...\n")

    successful = 0
    failed = 0

    for asset_id in fleet[
        "asset_id"
    ]:

        source_file = (
            FLEET_DIR /
            f"{asset_id}.csv"
        )

        try:

            reconstructed_data, summary = (
                reconstruct_exposure(
                    str(source_file)
                )
            )

            passport = generate_passport(
                reconstructed_data,
                summary
            )

            save_passport(

                passport,

                f"passport/"
                f"{asset_id}_passport.json"
            )

            successful += 1

            print(
                f"[OK] {asset_id}"
            )

        except Exception as error:

            failed += 1

            print(
                f"[ERROR] {asset_id}: "
                f"{error}"
            )

    print("\n")
    print("=" * 60)

    print(
        f"Successful passports: "
        f"{successful}"
    )

    print(
        f"Failed passports: "
        f"{failed}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()