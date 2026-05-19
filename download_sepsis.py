import sys
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "https://physionet.org/files/challenge-2019/1.0.0/training"
ROOT = Path(__file__).resolve().parent
DEST = ROOT / "Data" / "sepsis-2019"
DATA_SETS = ("training_setA", "training_setB")


def report_progress(block_num, block_size, total_size):
    if total_size > 0:
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 // total_size)
        mb = downloaded / (1024 * 1024)
        sys.stdout.write(f"\r  ... {percent}% ({mb:.1f} MB)")
        sys.stdout.flush()


def download_set(name):
    out_dir = DEST / name
    if out_dir.is_dir() and any(out_dir.rglob("*.psv")):
        print(f"{name}: da co du lieu, bo qua")
        return

    url = f"{BASE_URL}/{name}.zip"
    zip_path = DEST / f"{name}.zip"

    print(f"Dang tai {name}.zip tu PhysioNet ...")
    try:
        urllib.request.urlretrieve(url, zip_path, report_progress)
        print()
    except Exception as exc:
        print()
        print(f"Loi khi tai {name}: {exc}")
        print(f"Tai thu cong tai: {url}")
        sys.exit(1)

    print(f"Dang giai nen {name} ...")
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(DEST)
    zip_path.unlink()

    count = len(list(out_dir.rglob("*.psv")))
    print(f"{name}: {count} file .psv")


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for name in DATA_SETS:
        download_set(name)

    total = sum(len(list((DEST / n).rglob("*.psv"))) for n in DATA_SETS)
    print(f"Hoan tat. Tong cong {total} file benh nhan trong {DEST}")


if __name__ == "__main__":
    main()
