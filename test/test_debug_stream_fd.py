from __future__ import annotations

import gc
import os
import unittest

from argcomplete.finders import CompletionFinder


def fd_is_open(fd: int) -> bool:
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


class TestDebugStreamFdOwnership(unittest.TestCase):
    def test_init_debug_stream_does_not_close_unowned_fd(self):
        # An embedding process may already use fd 9 for its own purposes
        # (for example, pytest's faulthandler dup of stderr lands on fd 9 when
        # capture is active). Initializing the debug stream must never close it.
        was_open = fd_is_open(9)
        saved = os.dup(9) if was_open else None
        try:
            with open(os.devnull, "w") as devnull:
                os.dup2(devnull.fileno(), 9)
                finder = CompletionFinder()
                finder._init_debug_stream()
                # Reinitializing drops the first wrapper; garbage collection
                # must not close fd 9 as a side effect.
                finder._init_debug_stream()
                gc.collect()
                self.assertTrue(fd_is_open(9), "initializing the debug stream closed fd 9")
        finally:
            if saved is not None:
                os.dup2(saved, 9)
                os.close(saved)
            elif fd_is_open(9):
                os.close(9)


if __name__ == "__main__":
    unittest.main()
