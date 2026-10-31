from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argcomplete

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--value", choices=json.loads(os.environ["ARGCOMPLETE_TEST_CHOICES"]))
argcomplete.autocomplete(parser)
print(json.dumps(vars(parser.parse_args())))
