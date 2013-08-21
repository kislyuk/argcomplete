#!/usr/bin/env python
# -*- coding: utf-8 -*-
import locale
import os
import sys
if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest
import shutil
from tempfile import TemporaryFile, mkdtemp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from argcomplete import *

IFS = '\013'

class TempDir(object):
    """temporary directory for testing FilesCompletion

    usage:
    with TempDir(prefix="temp_fc") as t:
        print('tempdir', t)
        # you are not chdir-ed to the temporary directory
        # everything created here will be deleted
    """
    def __init__(self, suffix="", prefix='tmpdir', dir=None):
        self.tmp_dir = mkdtemp(suffix=suffix, prefix=prefix, dir=dir)
        self.old_dir = os.getcwd()

    def __enter__(self):
        os.chdir(self.tmp_dir)
        return self.tmp_dir

    def __exit__(self, *err):
        os.chdir(self.old_dir)
        shutil.rmtree(self.tmp_dir)


class TestArgcomplete(unittest.TestCase):

    def setUp(self):
        os.environ['_ARGCOMPLETE'] = "yes"
        os.environ['_ARC_DEBUG'] = "yes"
        os.environ['IFS'] = IFS

    def tearDown(self):
        pass

    def run_completer(self, parser, command, point=None):
        with TemporaryFile() as t:
            #os.environ['COMP_LINE'] = command.encode(locale.getpreferredencoding())
            os.environ['COMP_LINE'] = command
            os.environ['COMP_POINT'] = point if point else str(len(command))
            os.environ['COMP_WORDBREAKS'] = '"\'@><=;|&(:'
            self.assertRaises(SystemExit, autocomplete, parser, output_stream=t,
                              exit_method=sys.exit)
            t.seek(0)
            return t.read().decode(locale.getpreferredencoding()).split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        assert(set(completions) == set(['-h', '--help', '--foo', '--bar']))

    def test_action_activation(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        expected_outputs = (("prog ", ['bus', 'car', '-h', '--help']),
            ("prog bu", ['bus ']),
            ("prog bus ", ['apple', 'orange', '-h', '--help']),
            ("prog bus appl", ['apple ']),
            ("prog bus apple ", ['-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

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
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"ab@c.d\" ", ['--url', '--email', '-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_file_completion(self):
        # setup and teardown should probably be in class
        from argcomplete.completers import FilesCompleter
        with TempDir(prefix='test_dir_fc', dir='.') as t:
            fc = FilesCompleter()
            os.makedirs(os.path.join('abcdef', 'klm'))
            self.assertEqual(fc('a'), ['abcdef/'])
            os.makedirs(os.path.join('abcaha', 'klm'))
            with open('abcxyz', 'w') as fp:
                fp.write('test')
            self.assertEqual(set(fc('a')), set(['abcdef/', 'abcaha/', 'abcxyz']))

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
            ("prog --age 1 eggs", ['eggs']),
            ("prog --age 2 eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs \"on a", ['\"on a train', '\"on a boat']),
            ("prog eggs on\\ a", ['on a train', 'on a boat']),
            ("prog spam ", ['iberico', 'ham', '--help', '-h']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    if sys.version_info >= (2, 7):
        @unittest.skip("currently works on either 2 or 3, but not both")
        def test_non_ascii(self):
            def make_parser():
                parser = argparse.ArgumentParser()
                parser.add_argument('--книга', choices=['Трудно быть богом', 'Парень из преисподней', 'Понедельник начинается в субботу'])
                return parser

            expected_outputs = (("prog ", ['--книга', '-h', '--help']),
                ("prog --книга ", ['Трудно быть богом', 'Парень из преисподней', 'Понедельник начинается в субботу']),
                ("prog --книга П", ['Парень из преисподней', 'Понедельник начинается в субботу']),
                ("prog --книга Пу", ['']),
                )

            for cmd, output in expected_outputs:
                output = [o.decode(locale.getpreferredencoding()) for o in output]
                self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

if __name__ == '__main__':
    unittest.main()
