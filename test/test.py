#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import shutil
import sys
from tempfile import TemporaryFile, mkdtemp

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from argcomplete import (
    autocomplete,
    CompletionFinder,
    split_line,
)
from argcomplete.compat import USING_PYTHON2, str, sys_encoding, ensure_str, ensure_bytes

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

IFS = "\013"


class TempDir(object):
    """
    Temporary directory for testing FilesCompletion

    Usage:

        with TempDir(prefix="temp_fc") as t:
            print("tempdir", t)
            # you are not chdir-ed to the temporary directory
            # everything created here will be deleted
    """
    def __init__(self, suffix="", prefix="tmpdir", dir=None):
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
        os.environ["_ARGCOMPLETE"] = "yes"
        os.environ["_ARC_DEBUG"] = "yes"
        os.environ["IFS"] = IFS

    def tearDown(self):
        pass

    def run_completer(self, parser, command, point=None, **kwargs):
        command = ensure_str(command)
        if point is None:
            # Adjust point for wide chars
            point = str(len(command.encode(sys_encoding)))
        with TemporaryFile() as t:
            os.environ["COMP_LINE"] = ensure_bytes(command) if USING_PYTHON2 else command
            os.environ["COMP_POINT"] = point
            os.environ["_ARGCOMPLETE_COMP_WORDBREAKS"] = '"\'@><=;|&(:'
            self.assertRaises(SystemExit, autocomplete, parser, output_stream=t,
                              exit_method=sys.exit, **kwargs)
            t.seek(0)
            return t.read().decode(sys_encoding).split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        self.assertEquals(set(completions), set(["-h", "--help", "--foo", "--bar"]))

        completions = self.run_completer(p, "prog -")
        self.assertEquals(set(completions), set(["-h", "--help", "--foo", "--bar"]))

        completions = self.run_completer(p, "prog ", always_complete_options=False)
        self.assertEquals(set(completions), set([""]))

        completions = self.run_completer(p, "prog -", always_complete_options=False)
        self.assertEquals(set(completions), set(["-h", "--help", "--foo", "--bar"]))

    def test_choices(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--ship", choices=["submarine", b"speedboat"])
            return parser

        expected_outputs = (
            ("prog ", ["--ship", "-h", "--help"]),
            ("prog --shi", ["--ship "]),
            ("prog --ship ", ["submarine", "speedboat"]),
            ("prog --ship s", ["submarine", "speedboat"]),
            ("prog --ship su", ["submarine "])
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_non_str_choices(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("x", type=int, choices=[4, 8, 15, 16, 23, 42])
            return parser

        expected_outputs = (
            ("prog ", ["4", "8", "15", "16", "23", "42", "-h", "--help"]),
            ("prog 1", ["15", "16"]),
            ("prog 2", ["23 "]),
            ("prog 4", ["4", "42"]),
            ("prog 4 ", ["-h", "--help"])
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_action_activation(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("var", choices=["bus", "car"])
            parser.add_argument("value", choices=["orange", "apple"])
            return parser

        expected_outputs = (
            ("prog ", ["bus", "car", "-h", "--help"]),
            ("prog bu", ["bus "]),
            ("prog bus ", ["apple", "orange", "-h", "--help"]),
            ("prog bus appl", ["apple "]),
            ("prog bus apple ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_action_activation_with_subparser(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("name", nargs=2, choices=["a", "b", "c"])
            subparsers = parser.add_subparsers(title="subcommands", metavar="subcommand")
            subparser_build = subparsers.add_parser("build")
            subparser_build.add_argument("var", choices=["bus", "car"])
            subparser_build.add_argument("--profile", nargs=1)
            return parser

        expected_outputs = (
            ("prog ", ["a", "b", "c", "-h", "--help"]),
            ("prog b", ["b "]),
            ("prog b ", ["a", "b", "c", "-h", "--help"]),
            ("prog c b ", ["build", "-h", "--help"]),
            ("prog c b bu", ["build "]),
            ("prog c b build ", ["bus", "car", "--profile", "-h", "--help"]),
            ("prog c b build ca", ["car "]),
            ("prog c b build car ", ["--profile", "-h", "--help"]),
            ("prog build car ", ["-h", "--help"]),
            ("prog a build car ", ["-h", "--help"]),
            )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_completers(self):
        def c_url(prefix, parsed_args, **kwargs):
            return ["http://url1", "http://url2"]

        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--url").completer = c_url
            parser.add_argument("--email", nargs=3, choices=["a@b.c", "a@b.d", "ab@c.d", "bcd@e.f", "bce@f.g"])
            return parser

        expected_outputs = (
            ("prog --url ", ["http\\://url1", "http\\://url2"]),
            ("prog --url \"", ['"http://url1', '"http://url2']),
            ("prog --url \"http://url1\" --email ", ["a\\@b.c", "a\\@b.d", "ab\\@c.d", "bcd\\@e.f", "bce\\@f.g"]),
            ("prog --url \"http://url1\" --email a", ["a\\@b.c", "a\\@b.d", "ab\\@c.d"]),
            ("prog --url \"http://url1\" --email \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"a@", ['"a@b.c', '"a@b.d']),
            ("prog --url \"http://url1\" --email \"a@b.c\" \"a@b.d\" \"ab@c.d\" ", ["--url", "--email", "-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_file_completion(self):
        # setup and teardown should probably be in class
        from argcomplete.completers import FilesCompleter
        with TempDir(prefix="test_dir_fc", dir="."):
            fc = FilesCompleter()
            os.makedirs(os.path.join("abcdef", "klm"))
            self.assertEqual(fc("a"), ["abcdef/"])
            os.makedirs(os.path.join("abcaha", "klm"))
            with open("abcxyz", "w") as fp:
                fp.write("test")
            self.assertEqual(set(fc("a")), set(["abcdef/", "abcaha/", "abcxyz"]))

    def test_directory_completion(self):
        from argcomplete.completers import DirectoriesCompleter
        completer = DirectoriesCompleter()
        c = lambda prefix: set(completer(prefix))
        with TempDir(prefix="test_dir", dir="."):
            # Create some temporary dirs and files (files must be ignored)
            os.makedirs(os.path.join("abc", "baz"))
            os.makedirs(os.path.join("abb", "baz"))
            os.makedirs(os.path.join("abc", "faz"))
            os.makedirs(os.path.join("def", "baz"))
            with open("abc1", "w") as fp1:
                with open("def1", "w") as fp2:
                    fp1.write("A test")
                    fp2.write("Another test")
            # Test completions
            self.assertEqual(c("a"), set(["abb/", "abc/"]))
            self.assertEqual(c("ab"), set(["abc/", "abb/"]))
            self.assertEqual(c("abc"), set(["abc/"]))
            self.assertEqual(c("abc/"), set(["abc/baz/", "abc/faz/"]))
            self.assertEqual(c("d"), set(["def/"]))
            self.assertEqual(c("def/"), set(["def/baz/"]))
            self.assertEqual(c("e"), set([]))
            self.assertEqual(c("def/k"), set([]))
        return

    def test_subparsers(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--age", type=int)
            sub = parser.add_subparsers()
            eggs = sub.add_parser("eggs")
            eggs.add_argument("type", choices=["on a boat", "with a goat", "in the rain", "on a train"])
            spam = sub.add_parser("spam")
            spam.add_argument("type", choices=["ham", "iberico"])
            return parser

        expected_outputs = (
            ("prog ", ["--help", "eggs", "-h", "spam", "--age"]),
            ("prog --age 1 eggs", ["eggs "]),
            ("prog --age 2 eggs ", ["on a train", "with a goat", "on a boat", "in the rain", "--help", "-h"]),
            ("prog eggs ", ["on a train", "with a goat", "on a boat", "in the rain", "--help", "-h"]),
            ("prog eggs \"on a", ['\"on a train', '\"on a boat']),
            ("prog eggs on\\ a", ["on a train", "on a boat"]),
            ("prog spam ", ["iberico", "ham", "--help", "-h"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=["-h"])), set(output) - set(["-h"]))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=["-h", "--help"])),
                             set(output) - set(["-h", "--help"]))

    def test_non_ascii(self):
        def make_parser():
            _str = ensure_bytes if USING_PYTHON2 else str
            parser = ArgumentParser()
            # Python 2 argparse only works with byte strings or ascii unicode strings.
            # Python 3 argparse only works with unicode strings.
            parser.add_argument(_str("--книга"), choices=[
                _str("Трудно быть богом"),
                _str("Парень из преисподней"),
                _str("Понедельник начинается в субботу"),
            ])
            return parser

        expected_outputs = (
            ("prog ", ["--книга", "-h", "--help"]),
            ("prog --книга ", ["Трудно быть богом", "Парень из преисподней", "Понедельник начинается в субботу"]),
            ("prog --книга П", ["Парень из преисподней", "Понедельник начинается в субботу"]),
            ("prog --книга Пу", [""]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)),
                             set(output))

    def test_custom_validator(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("var", choices=["bus", "car"])
            parser.add_argument("value", choices=["orange", "apple"])
            return parser

        expected_outputs = (
            ("prog ", ["-h", "--help"]),
            ("prog bu", [""]),
            ("prog bus ", ["-h", "--help"]),
            ("prog bus appl", [""]),
            ("prog bus apple ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(
                set(self.run_completer(make_parser(), cmd, validator=lambda x, y: False)),
                set(output)
            )

    def test_different_validators(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("var", choices=["bus", "car"])
            parser.add_argument("value", choices=["orange", "apple"])
            return parser

        validators = (
            lambda x, y: False,
            lambda x, y: True,
            lambda x, y: x.startswith(y),
        )

        expected_outputs = (
            ("prog ", ["-h", "--help"], validators[0]),
            ("prog ", ["bus", "car", "-h", "--help"], validators[1]),
            ("prog bu", ["bus "], validators[1]),
            ("prog bus ", ["apple", "orange", "-h", "--help"], validators[1]),
            ("prog bus appl", ["apple "], validators[2]),
            ("prog bus cappl", [""], validators[2]),
            ("prog bus pple ", ["-h", "--help"], validators[2]),
        )

        for cmd, output, validator in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=validator)), set(output))

    def test_readline_entry_point(self):
        def get_readline_completions(completer, text):
            completions = []
            for i in range(9999):
                completion = completer.rl_complete(text, i)
                if completion is None:
                    break
                completions.append(completion)
            return completions

        parser = ArgumentParser()
        parser.add_argument("rover", choices=["sojourner", "spirit", "opportunity", "curiosity"])
        parser.add_argument("antenna", choices=["low gain", "high gain"])
        completer = CompletionFinder(parser)
        self.assertEqual(get_readline_completions(completer, ""),
                         ["-h", "--help", "sojourner", "spirit", "opportunity", "curiosity"])
        self.assertEqual(get_readline_completions(completer, "s"), ["sojourner", "spirit"])
        self.assertEqual(get_readline_completions(completer, "x"), [])

    def test_display_completions(self):
        parser = ArgumentParser()
        parser.add_argument("rover",
                            choices=["sojourner", "spirit", "opportunity", "curiosity"],
                            help="help for rover ")
        parser.add_argument("antenna", choices=["low gain", "high gain"], help="help for antenna")
        sub = parser.add_subparsers()
        p = sub.add_parser("list")
        p.add_argument("-o", "--oh", help="ttt")
        p.add_argument("-c", "--ch", help="ccc")
        sub2 = p.add_subparsers()
        sub2.add_parser("cat", help="list cat")
        sub2.add_parser("dog", help="list dog")

        completer = CompletionFinder(parser)

        completer.rl_complete("", 0)
        disp = completer.get_display_completions()
        self.assertEqual("help for rover ", disp.get("spirit", ""))
        self.assertEqual("help for rover ", disp.get("sojourner", ""))
        self.assertEqual("", disp.get("low gain", ""))

        completer.rl_complete('opportunity "low gain" list ', 0)
        disp = completer.get_display_completions()
        self.assertEqual("ttt", disp.get("-o --oh", ""))
        self.assertEqual("list cat", disp.get("cat", ""))

        completer.rl_complete("opportunity low\\ gain list --", 0)
        disp = completer.get_display_completions()
        self.assertEqual("ttt", disp.get("--oh", ""))
        self.assertEqual("ccc", disp.get("--ch", ""))

    @unittest.expectedFailure
    def test_nargs_one_or_more(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("h1", choices=["c", "d"])
            parser.add_argument("var", choices=["bus", "car"], nargs="+")
            parser.add_argument("value", choices=["orange", "apple"])
            return parser

        expected_outputs = (
            ("prog ", ["c", "d", "-h", "--help"]),
            ("prog c bu", ["bus "]),
            ("prog c bus ", ["bus", "car", "apple", "orange", "-h", "--help"]),
            ("prog c bus car ", ["bus", "car", "apple", "orange", "-h", "--help"]),
            ("prog c bus appl", ["apple "]),
            ("prog c bus apple ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))


class TestArgcompleteREPL(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run_completer(self, parser, completer, command, point=None, **kwargs):
        cword_prequote, cword_prefix, cword_suffix, comp_words, first_colon_pos = split_line(command)

        comp_words.insert(0, sys.argv[0])

        completions = completer._get_completions(
            comp_words, cword_prefix, cword_prequote, first_colon_pos)

        return completions

    def test_repl_multiple_complete(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        c = CompletionFinder(p, always_complete_options=True)

        completions = self.run_completer(p, c, "prog ")
        assert(set(completions) == set(["-h", "--help", "--foo", "--bar"]))

        completions = self.run_completer(p, c, "prog --")
        assert(set(completions) == set(["--help", "--foo", "--bar"]))

    def test_repl_parse_after_complete(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        c = CompletionFinder(p, always_complete_options=True)

        completions = self.run_completer(p, c, "prog ")
        assert(set(completions) == set(["-h", "--help", "--foo", "--bar"]))

        args = p.parse_args(["--foo", "spam"])
        assert(args.foo == "spam")

    def test_repl_subcommand(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        s = p.add_subparsers()
        s.add_parser("list")
        s.add_parser("set")
        show = s.add_parser("show")

        def abc():
            pass

        show.add_argument("--test")
        ss = show.add_subparsers()
        de = ss.add_parser("depth")
        de.set_defaults(func=abc)

        c = CompletionFinder(p, always_complete_options=True)

        expected_outputs = (
            ("", ["-h", "--help", "--foo", "--bar", "list", "show", "set"]),
            ("li", ["list "]),
            ("s", ["show", "set"]),
            ("show ", ["--test", "depth", "-h", "--help"]),
            ("show d", ["depth "]),
            ("show depth ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(p, c, cmd)), set(output))

    @unittest.expectedFailure
    def test_repl_reuse_parser_with_positional(self):
        p = ArgumentParser()
        p.add_argument("foo", choices=["aa", "bb", "cc"])
        p.add_argument("bar", choices=["d", "e"])

        c = CompletionFinder(p, always_complete_options=True)

        self.assertEqual(set(self.run_completer(p, c, "")),
                         set(["-h", "--help", "aa", "bb", "cc"]))

        self.assertEqual(set(self.run_completer(p, c, "aa ")),
                         set(["-h", "--help", "d", "e"]))

        self.assertEqual(set(self.run_completer(p, c, "")),
                         set(["-h", "--help", "aa", "bb", "cc"]))

if __name__ == "__main__":
    unittest.main()
