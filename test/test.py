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
            os.environ['COMP_WORDBREAKS'] = '"\'@><=;|&(:'
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

    def test_completers(self):
        def c_url(prefix, parsed_args, **kwargs):
            return [ "http://url1", "http://url2" ]

        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument("--url").completer = c_url
            parser.add_argument("--email", nargs=3, choices=['a@b.c', 'a@b.d', 'ab@c.d', 'bcd@e.f', 'bce@f.g'])
            return parser

        expected_outputs = (("prog --url ", ['http\\://url1', 'http\\://url2']),
            ("prog --url \"", ['"http://url1', '"http://url2']),
            ("prog --url \"http://url1\" --email ", ['a\\@b.c', 'a\\@b.d', 'ab\\@c.d', 'bcd\\@e.f', 'bce\\@f.g']),
            ("prog --url \"http://url1\" --email a", ['a\\@b.c', 'a\\@b.d', 'ab\\@c.d']),
            ("prog --url \"http://url1\" --email \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"ab@c.d\"", ['--url', '--email', '-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_subparsers(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument("--age", type=int)
            sub = parser.add_subparsers()
            eggs = sub.add_parser("eggs")
            eggs.add_argument("type", choices=['on a boat', 'with a goat', 'in the rain', 'on a train'])
            spam = sub.add_parser("spam")
            spam.add_argument("type", choices=['ham', 'iberico'])
            return parser

        expected_outputs = (("prog ", ['--help', 'eggs', '-h', 'spam', '--age']),
            ("prog --age 1 eggs", ['eggs ']),
            ("prog --age 2 eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs \"on a", ['\"on a train', '\"on a boat']),
            ("prog spam ", ['iberico', 'ham', '--help', '-h']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

if __name__ == '__main__':
    unittest.main()
