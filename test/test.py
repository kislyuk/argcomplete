#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import os, sys, shutil

python2 = True if sys.version_info < (3, 0) else False

if python2:
    # Try to reset default encoding to a sane value
    # Note: This is incompatible with pypy
    import platform
    if platform.python_implementation() != "PyPy":
        try:
            import locale
            reload(sys).setdefaultencoding(locale.getdefaultlocale()[1])
        except:
            pass

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

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

    def run_completer(self, parser, command, point=None, **kwargs):
        if python2:
            command = unicode(command)
        if point is None:
            if python2:
                point = str(len(command))
            else:
                # Adjust point for wide chars
                point = str(len(command.encode(locale.getpreferredencoding())))
        with TemporaryFile() as t:
            #os.environ['COMP_LINE'] = command.encode(locale.getpreferredencoding())
            os.environ['COMP_LINE'] = command
            os.environ['COMP_POINT'] = point
            os.environ['_ARGCOMPLETE_COMP_WORDBREAKS'] = '"\'@><=;|&(:'
            self.assertRaises(SystemExit, autocomplete, parser, output_stream=t,
                              exit_method=sys.exit, **kwargs)
            t.seek(0)
            return t.read().decode(locale.getpreferredencoding()).split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        assert(set(completions) == set(['-h', '--help', '--foo', '--bar']))

    def test_choices(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('--ship', choices=['submarine', 'speedboat'])
            return parser

        expected_outputs = (("prog ", ['--ship', '-h', '--help']),
            ("prog --shi", ['--ship ']),
            ("prog --ship ", ['submarine', 'speedboat']),
            ("prog --ship s", ['submarine', 'speedboat']),
            ("prog --ship su", ['submarine ']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

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

    def test_action_activation_with_subparser(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(title='subcommands', metavar='subcommand')
            subparser_build = subparsers.add_parser('build')
            subparser_build.add_argument('var', choices=['bus', 'car'])
            subparser_build.add_argument('--profile', nargs=1)
            return parser

        expected_outputs = (("prog ", ['build', '-h', '--help']),
            ("prog bu", ['build ']),
            ("prog build ", ['bus', 'car', '--profile', '-h', '--help']),
            ("prog build ca", ['car ']),
            ("prog build car ", ['--profile', '-h', '--help']),
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
            ("prog --age 1 eggs", ['eggs ']),
            ("prog --age 2 eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs ", ['on a train', 'with a goat', 'on a boat', 'in the rain', '--help', '-h']),
            ("prog eggs \"on a", ['\"on a train', '\"on a boat']),
            ("prog eggs on\\ a", ['on a train', 'on a boat']),
            ("prog spam ", ['iberico', 'ham', '--help', '-h']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=['-h'])), set(output) - set(['-h']))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=['-h', '--help'])),
                             set(output) - set(['-h', '--help']))

    def test_non_ascii(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('--книга', choices=['Трудно быть богом',
                                                    'Парень из преисподней',
                                                    'Понедельник начинается в субботу'])
            return parser

        expected_outputs = (("prog ", ['--книга', '-h', '--help']),
            ("prog --книга ", ['Трудно быть богом', 'Парень из преисподней', 'Понедельник начинается в субботу']),
            ("prog --книга П", ['Парень из преисподней', 'Понедельник начинается в субботу']),
            ("prog --книга Пу", ['']),
            )

        for cmd, output in expected_outputs:
            if python2:
                output = [o.decode(locale.getpreferredencoding()) for o in output]
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_custom_validator(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        expected_outputs = (("prog ", ['-h', '--help']),
            ("prog bu", ['']),
            ("prog bus ", ['-h', '--help']),
            ("prog bus appl", ['']),
            ("prog bus apple ", ['-h', '--help']),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=lambda x,y: False) ), set(output))

    def test_different_validators(self):
        def make_parser():
            parser = argparse.ArgumentParser()
            parser.add_argument('var', choices=['bus', 'car'])
            parser.add_argument('value', choices=['orange', 'apple'])
            return parser

        validators = (
                lambda x,y: False,
                lambda x,y: True,
                lambda x,y: x.startswith(y),
        )

        expected_outputs = (("prog ", ['-h', '--help'], validators[0]),
            ("prog ", ['bus', 'car', '-h', '--help'], validators[1]),
            ("prog bu", ['bus '], validators[1]),
            ("prog bus ", ['apple', 'orange', '-h', '--help'], validators[1]),
            ("prog bus appl", ['apple '], validators[2]),
            ("prog bus cappl", [''], validators[2]),
            ("prog bus pple ", ['-h', '--help'], validators[2]),
            )

        for cmd, output, validator in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=validator) ), set(output))
if __name__ == '__main__':
    unittest.main()
