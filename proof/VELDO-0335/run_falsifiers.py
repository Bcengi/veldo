"""Run the authoritative finding 335 teeth campaign; print its measured receipt."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    spec = importlib.util.spec_from_file_location('teeth335', ROOT / 'scripts/check_teeth_mutations.py')
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    sys.argv = [str(ROOT / 'scripts/check_teeth_mutations.py'), '--finding', '335', *sys.argv[1:]]
    return driver.main()


if __name__ == '__main__':
    raise SystemExit(main())
