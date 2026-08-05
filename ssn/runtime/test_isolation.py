"""
Per-test runtime-data isolation for the governed unittest runner.
"""

from __future__ import annotations

import os
import unittest
from typing import Optional

from ssn.runtime.paths import PerTestIsolation


def _shares_state(test: unittest.TestCase) -> bool:
    return bool(getattr(test, "ssn_share_runtime_state", False)) or bool(
        getattr(getattr(test, "__class__", None), "ssn_share_runtime_state", False)
    )


class IsolatedTestResult(unittest.TextTestResult):
    """Allocates a unique runtime-data directory before each test."""

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self._isolation: Optional[PerTestIsolation] = None
        self.last_data_dirs: list[str] = []

    def startTest(self, test: unittest.TestCase) -> None:  # noqa: N802
        if not _shares_state(test):
            self._isolation = PerTestIsolation(prefix="siona-test-")
            data = self._isolation.start()
            self.last_data_dirs.append(str(data))
            # Expose to the test instance for assertions
            setattr(test, "_ssn_runtime_data_dir", str(data))
        else:
            self._isolation = None
        super().startTest(test)

    def stopTest(self, test: unittest.TestCase) -> None:  # noqa: N802
        try:
            super().stopTest(test)
        finally:
            if self._isolation is not None:
                self._isolation.stop(cleanup=True)
                self._isolation = None


class IsolatedTextTestRunner(unittest.TextTestRunner):
    resultclass = IsolatedTestResult
