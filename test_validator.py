import json
import unittest
from pathlib import Path

import agentfeed_validator as validator


ROOT = Path(__file__).resolve().parent


class FreeValidatorTests(unittest.TestCase):
    def test_complete(self):
        product = json.loads((ROOT / "examples/product-complete.json").read_text())
        self.assertTrue(validator.validate(product)["ready"])

    def test_secret_not_echoed(self):
        product = json.loads((ROOT / "examples/product-complete.json").read_text())
        secret = "sk-" + "example1234567890abcdef"
        product["description"] += secret
        text = json.dumps(validator.validate(product))
        self.assertIn("SECRET_DETECTED", text)
        self.assertNotIn(secret, text)


if __name__ == "__main__":
    unittest.main()
