import sys
import traceback


def run(module):
    tests = sorted(
        (name, fn)
        for name, fn in vars(module).items()
        if name.startswith("test_") and callable(fn)
    )
    failed = 0
    skipped = 0
    for name, fn in tests:
        try:
            result = fn()
            if result == "skip":
                skipped += 1
                print(f"SKIP {name}")
            else:
                print(f"PASS {name}")
        except Exception:
            failed += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    run_count = len(tests) - skipped
    print(f"\n{run_count - failed}/{run_count} passed, {skipped} skipped")
    sys.exit(1 if failed else 0)
