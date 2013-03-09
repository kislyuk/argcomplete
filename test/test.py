#!/usr/bin/env python
import locale
import os
import sys
import unittest
from tempfile import TemporaryFile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from argcomplete import *

IFS = '\013'

class TestArgcomplete(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ['_ARGCOMPLETE'] = "yes"
        os.environ['_ARC_DEBUG'] = "yes"
        os.environ['IFS'] = IFS

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run_completer(self, parser, command, point=None):
        with TemporaryFile() as t:
            os.environ['COMP_LINE'] = command
            os.environ['COMP_POINT'] = point if point else str(len(command))
            with self.assertRaises(SystemExit):
                autocomplete(parser, output_stream=t, exit_method=sys.exit)
            t.seek(0)
            return t.read().decode(locale.getpreferredencoding()).split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        assert(set(completions) == set(['-h', '--help', '--foo', '--bar']))

if __name__ == '__main__':
    unittest.main()
