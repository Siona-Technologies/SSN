# ssn/tests/test_phase43_cli_smoke.py

import unittest

from ssn.runtime.cli import main


class TestPhase43CliSmoke(unittest.TestCase):

    def test_cli_state_smoke(self):
        code = main(["state", "--role", "OWNER"])
        self.assertEqual(code, 0)

    def test_cli_chat_smoke(self):
        code = main(["chat", "--role", "OWNER", "--text", "hello", "--context", "{}"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
