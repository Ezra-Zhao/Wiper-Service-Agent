"""Minimal test runner (no pytest dependency).

Usage:  python tests/run_tests.py   (from the repo root)
Runs every test_* function in tests/test_*.py. Supports two fixtures by
name: tmp_path (a fresh pathlib.Path) and monkeypatch (setattr with undo).
"""
import inspect
import pathlib
import sys
import tempfile
import traceback

sys.path.insert(0, ".")


class MonkeyPatch:
    def __init__(self):
        self._orig = []

    def setattr(self, obj, name, value):
        import importlib
        target = importlib.import_module(obj) if isinstance(obj, str) else obj
        self._orig.append((target, name, getattr(target, name)))
        setattr(target, name, value)

    def undo(self):
        for target, name, value in reversed(self._orig):
            setattr(target, name, value)
        self._orig.clear()


def main() -> int:
    import tests.test_agent as test_agent
    import tests.test_hardening as test_hardening
    passed, failed = 0, []
    for mod in (test_agent, test_hardening):
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            sig = inspect.signature(fn)
            kwargs, mp = {}, None
            if "tmp_path" in sig.parameters:
                kwargs["tmp_path"] = pathlib.Path(tempfile.mkdtemp())
            if "monkeypatch" in sig.parameters:
                mp = MonkeyPatch()
                kwargs["monkeypatch"] = mp
            try:
                fn(**kwargs)
                passed += 1
            except Exception:
                failed.append(f"{mod.__name__}.{name}")
                print(f"FAIL {mod.__name__}.{name}\n{traceback.format_exc()[-1500:]}")
            finally:
                if mp:
                    mp.undo()
    print(f"\n{passed} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
