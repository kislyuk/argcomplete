#!/usr/bin/env python
import argparse
import contextlib
import os
import os.path
import re
import shutil
import subprocess
import sys
import unittest
import unittest.util
from io import StringIO
from tempfile import NamedTemporaryFile, TemporaryFile, mkdtemp

import pexpect
from pexpect.replwrap import PEXPECT_CONTINUATION_PROMPT, PEXPECT_PROMPT, REPLWrapper

TEST_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.dirname(TEST_DIR)
sys.path.insert(0, BASE_DIR)

from argparse import SUPPRESS, ArgumentParser  # noqa: E402

import argcomplete  # noqa: E402
import argcomplete.io  # noqa: E402
from argcomplete import (  # noqa: E402
    CompletionFinder,
    ExclusiveCompletionFinder,
    _check_module,
    autocomplete,
    shellcode,
    warn,
)
from argcomplete.completers import DirectoriesCompleter, FilesCompleter, SuppressCompleter  # noqa: E402
from argcomplete.lexers import split_line  # noqa: E402

# Default max length is insufficient for troubleshooting.
unittest.util._MAX_LENGTH = 1000

IFS = "\013"
COMP_WORDBREAKS = " \t\n\"'><=;|&(:"

BASH_VERSION = subprocess.check_output(["bash", "-c", "echo $BASH_VERSION"]).decode()
BASH_MAJOR_VERSION = int(BASH_VERSION.split(".")[0])


class ArgcompleteREPLWrapper(REPLWrapper):
    def run_command(self, command, **kwargs):
        if "\n" in command:
            raise Exception("newlines not supported in REPL input")
        res = super().run_command(command, **kwargs)
        if self.child.command.split("/")[-1] == "zsh":
            if "\n" not in res:
                raise Exception("Expected to see a newline in command response")
            echo_cmd, actual_res = res.split("\n", 1)
            res_without_ansi_seqs = re.sub(r"\x1b\[0m.+\x1b\[J", "", actual_res)
            # Unsure why some environments produce trailing null characters,
            # but they break tests and trimming them seems to be harmless.
            # https://github.com/kislyuk/argcomplete/issues/447
            res_without_null_chars = res_without_ansi_seqs.rstrip("\x00")
            return res_without_null_chars
        else:
            return res


def _repl_sh(command, args, non_printable_insert):
    os.environ["PS1"] = "$"
    os.environ["TERM"] = ""
    child = pexpect.spawn(command, args, echo=False, encoding="utf-8")
    ps1 = PEXPECT_PROMPT[:5] + non_printable_insert + PEXPECT_PROMPT[5:]
    ps2 = PEXPECT_CONTINUATION_PROMPT[:5] + non_printable_insert + PEXPECT_CONTINUATION_PROMPT[5:]
    prompt_change = f"PS1='{ps1}' PS2='{ps2}' PROMPT_COMMAND=''"
    return ArgcompleteREPLWrapper(child, "\\$", prompt_change, extra_init_cmd="export PAGER=cat")


def bash_repl(command="bash"):
    bashrc = os.path.join(os.path.dirname(pexpect.__file__), "bashrc.sh")
    sh = _repl_sh(command, ["--rcfile", bashrc], non_printable_insert="\\[\\]")
    return sh


def zsh_repl(command="zsh"):
    sh = _repl_sh(command, ["--no-rcs", "--no-globalrcs", "-V"], non_printable_insert="%(!..)")
    # Require two tabs to print all options (some tests rely on this).
    sh.run_command("setopt BASH_AUTO_LIST")
    return sh


def setUpModule():
    os.environ["INPUTRC"] = os.path.join(os.path.dirname(__file__), "inputrc")


class TempDir:
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
        self._os_environ = os.environ
        os.environ = os.environ.copy()
        os.environ["_ARGCOMPLETE"] = "1"
        os.environ["_ARC_DEBUG"] = "yes"
        os.environ["IFS"] = IFS
        os.environ["_ARGCOMPLETE_COMP_WORDBREAKS"] = COMP_WORDBREAKS
        os.environ["_ARGCOMPLETE_SHELL"] = "bash"

    def tearDown(self):
        os.environ = self._os_environ

    def run_completer(self, parser, command, point=None, completer=autocomplete, shell="bash", **kwargs):
        if point is None:
            point = str(len(command))
        with TemporaryFile(mode="w+") as t:
            os.environ["COMP_LINE"] = command
            os.environ["COMP_POINT"] = point
            os.environ["_ARGCOMPLETE_SHELL"] = shell
            with self.assertRaises(SystemExit) as cm:
                completer(parser, output_stream=t, exit_method=sys.exit, **kwargs)
            if cm.exception.code != 0:
                raise Exception("Unexpected exit code %d" % cm.exception.code)
            t.seek(0)
            return t.read().split(IFS)

    def test_basic_completion(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ")
        self.assertEqual(set(completions), set(["-h", "--help", "--foo", "--bar"]))

        completions = self.run_completer(p, "prog -")
        self.assertEqual(set(completions), set(["-h", "--help", "--foo", "--bar"]))

        completions = self.run_completer(p, "prog ", always_complete_options=False)
        self.assertEqual(set(completions), set([""]))

        completions = self.run_completer(p, "prog -", always_complete_options=False)
        self.assertEqual(set(completions), set(["-h", "--help", "--foo", "--bar"]))

    def test_choices(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--ship", choices=["submarine", "speedboat"])
            return parser

        expected_outputs = (
            ("prog ", ["--ship", "-h", "--help"]),
            ("prog --shi", ["--ship "]),
            ("prog --ship ", ["submarine", "speedboat"]),
            ("prog --ship s", ["submarine", "speedboat"]),
            ("prog --ship su", ["submarine "]),
            ("prog --ship=", ["submarine", "speedboat"]),
            ("prog --ship=s", ["submarine", "speedboat"]),
            ("prog --ship=su", ["submarine "]),
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
            ("prog 4 ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_suppress_args(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--foo")
            parser.add_argument("--bar", help=SUPPRESS)
            return parser

        expected_outputs = (("prog ", ["--foo", "-h", "--help"]), ("prog --b", [""]))

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

        expected_outputs = (("prog ", ["--foo", "--bar", "-h", "--help"]), ("prog --b", ["--bar "]))

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, print_suppressed=True)), set(output))

    def test_suppress_completer(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--foo")
            arg = parser.add_argument("--bar")
            arg.completer = SuppressCompleter()
            return parser

        expected_outputs = (("prog ", ["--foo", "-h", "--help"]), ("prog --b", [""]))

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

        expected_outputs = (("prog ", ["--foo", "--bar", "-h", "--help"]), ("prog --b", ["--bar "]))

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, print_suppressed=True)), set(output))

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
        self.completions = ["http://url1", "http://url2"]

        def c_url(prefix, parsed_args, **kwargs):
            return self.completions

        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--url").completer = c_url
            parser.add_argument("--email", nargs=3, choices=["a@b.c", "a@b.d", "ab@c.d", "bcd@e.f", "bce@f.g"])
            return parser

        expected_outputs = (
            ("prog --url ", ["http://url1", "http://url2"]),
            ('prog --url "', ["http://url1", "http://url2"]),
            ('prog --url "http://url1" --email ', ["a@b.c", "a@b.d", "ab@c.d", "bcd@e.f", "bce@f.g"]),
            ('prog --url "http://url1" --email a', ["a@b.c", "a@b.d", "ab@c.d"]),
            ('prog --url "http://url1" --email "a@', ["a@b.c", "a@b.d"]),
            ('prog --url "http://url1" --email "a@b.c" "a@b.d" "a@', ["a@b.c", "a@b.d"]),
            ('prog --url "http://url1" --email "a@b.c" "a@b.d" "ab@c.d" ', ["--url", "--email", "-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

        self.completions = {"http://url1": "foo", "http://url2": "bar"}
        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))
        zsh_expected_outputs = (
            ("prog --url ", ["http\\://url1:foo", "http\\://url2:bar"]),
            ('prog --url "', ["http\\://url1:foo", "http\\://url2:bar"]),
            ('prog --url "http://url1" --email ', ["a@b.c:", "a@b.d:", "ab@c.d:", "bcd@e.f:", "bce@f.g:"]),
            ('prog --url "http://url1" --email a', ["a@b.c:", "a@b.d:", "ab@c.d:"]),
            ('prog --url "http://url1" --email "a@', ["a@b.c:", "a@b.d:"]),
            ('prog --url "http://url1" --email "a@b.c" "a@b.d" "a@', ["a@b.c:", "a@b.d:"]),
            (
                'prog --url "http://url1" --email "a@b.c" "a@b.d" "ab@c.d" ',
                ["--url:", "--email:", "-h:show this help message and exit", "--help:show this help message and exit"],
            ),
        )
        for cmd, output in zsh_expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd, shell="zsh")), set(output))

    def test_subparser_completers(self):
        def c_depends_on_positional_arg1(prefix, parsed_args, **kwargs):
            return [parsed_args.arg1]

        def c_depends_on_optional_arg5(prefix, parsed_args, **kwargs):
            return [parsed_args.arg5]

        def make_parser():
            parser = ArgumentParser()
            subparsers = parser.add_subparsers()
            subparser = subparsers.add_parser("subcommand")
            subparser.add_argument("arg1")
            subparser.add_argument("arg2").completer = c_depends_on_positional_arg1
            subparser.add_argument("arg3").completer = c_depends_on_optional_arg5
            subparser.add_argument("--arg4").completer = c_depends_on_optional_arg5
            subparser.add_argument("--arg5")
            return parser

        expected_outputs = (
            ("prog subcommand val1 ", ["val1", "--arg4", "--arg5", "-h", "--help"]),
            ("prog subcommand val1 val2 --arg5 val5 ", ["val5", "--arg4", "--arg5", "-h", "--help"]),
            ("prog subcommand val1 val2 --arg5 val6 --arg4 v", ["val6 "]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_file_completion(self):
        # setup and teardown should probably be in class
        with TempDir(prefix="test_dir_fc", dir="."):
            fc = FilesCompleter()
            os.makedirs(os.path.join("abcdefж", "klm"))
            self.assertEqual(fc("a"), ["abcdefж/"])
            os.makedirs(os.path.join("abcaha", "klm"))
            with open("abcxyz", "w") as fp:
                fp.write("test")
            self.assertEqual(set(fc("a")), set(["abcdefж/", "abcaha/", "abcxyz"]))

    def test_filescompleter_filetype_integration(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--r", type=argparse.FileType("r"))
            parser.add_argument("--w", type=argparse.FileType("w"))
            return parser

        with TempDir(prefix="test_dir_fc2", dir="."):
            os.makedirs(os.path.join("abcdefж", "klm"))
            os.makedirs(os.path.join("abcaha", "klm"))
            with open("abcxyz", "w") as fh, open("abcdefж/klm/test", "w") as fh2:
                fh.write("test")
                fh2.write("test")

            expected_outputs = (
                ("prog subcommand --r ", ["abcxyz", "abcdefж/", "abcaha/"]),
                ("prog subcommand --w abcdefж/klm/t", ["abcdefж/klm/test "]),
            )

            for cmd, output in expected_outputs:
                self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_directory_completion(self):
        completer = DirectoriesCompleter()

        def c(prefix):
            return set(completer(prefix))

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

    def test_default_completer(self):
        def make_parser():
            parser = ArgumentParser(add_help=False)
            parser.add_argument("--one")
            parser.add_argument("--many", nargs="+")
            return parser

        with TempDir(prefix="test_dir_dc", dir="."):
            os.mkdir("test")

            expected_outputs = (
                ("prog --one ", ["test/"]),
                ("prog --many ", ["test/"]),
                ("prog --many test/ ", ["test/", "--one", "--many"]),
            )

            for cmd, output in expected_outputs:
                self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

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
            (
                "prog --age 2 eggs ",
                [r"on\ a\ train", r"with\ a\ goat", r"on\ a\ boat", r"in\ the\ rain", "--help", "-h"],
            ),
            ("prog eggs ", [r"on\ a\ train", r"with\ a\ goat", r"on\ a\ boat", r"in\ the\ rain", "--help", "-h"]),
            ('prog eggs "on a', ["on a train", "on a boat"]),
            ("prog eggs on\\ a", [r"on\ a\ train", r"on\ a\ boat"]),
            ("prog spam ", ["iberico", "ham", "--help", "-h"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))
            self.assertEqual(set(self.run_completer(make_parser(), cmd, exclude=["-h"])), set(output) - set(["-h"]))
            self.assertEqual(
                set(self.run_completer(make_parser(), cmd, exclude=["-h", "--help"])),
                set(output) - set(["-h", "--help"]),
            )

    def test_non_ascii(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument(
                "--книга",
                choices=[
                    "Трудно быть богом",
                    "Парень из преисподней",
                    "Понедельник начинается в субботу",
                ],
            )
            return parser

        expected_outputs = (
            ("prog ", ["--книга", "-h", "--help"]),
            (
                "prog --книга ",
                [r"Трудно\ быть\ богом", r"Парень\ из\ преисподней", r"Понедельник\ начинается\ в\ субботу"],
            ),
            ("prog --книга П", [r"Парень\ из\ преисподней", r"Понедельник\ начинается\ в\ субботу"]),
            ("prog --книга Пу", [""]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

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
            self.assertEqual(set(self.run_completer(make_parser(), cmd, validator=lambda x, y: False)), set(output))

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
            ("prog bu", ["bus", "car"], validators[1]),
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
        self.assertEqual(
            get_readline_completions(completer, ""), ["-h", "--help", "sojourner", "spirit", "opportunity", "curiosity"]
        )
        self.assertEqual(get_readline_completions(completer, "s"), ["sojourner", "spirit"])
        self.assertEqual(get_readline_completions(completer, "x"), [])

    def test_display_completions(self):
        parser = ArgumentParser()
        parser.add_argument(
            "rover", choices=["sojourner", "spirit", "opportunity", "curiosity"], help="help for rover "
        )
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

    def test_display_completions_with_aliases(self):
        parser = ArgumentParser()
        parser.add_subparsers().add_parser("a", aliases=["b", "c"], help="abc help")

        # empty
        completer = CompletionFinder(parser)
        completer.rl_complete("", 0)
        disp = completer.get_display_completions()
        self.assertEqual(
            {
                "a": "abc help",
                "b": "abc help",
                "c": "abc help",
                "-h": "show this help message and exit",
                "--help": "show this help message and exit",
            },
            disp,
        )

        # a
        completer = CompletionFinder(parser)
        completer.rl_complete("a", 0)
        disp = completer.get_display_completions()
        self.assertEqual({"a": "abc help"}, disp)

        # b
        completer = CompletionFinder(parser)
        completer.rl_complete("b", 0)
        disp = completer.get_display_completions()
        self.assertEqual({"b": "abc help"}, disp)

        # c
        completer = CompletionFinder(parser)
        completer.rl_complete("c", 0)
        disp = completer.get_display_completions()
        self.assertEqual({"c": "abc help"}, disp)

    def test_nargs_one_or_more(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("h1", choices=["c", "d"])
            parser.add_argument("var", choices=["bus", "car"], nargs="+")
            parser.add_argument("value", choices=["orange", "apple"])
            parser.add_argument("end", choices=["end"])
            return parser

        expected_outputs = (
            ("prog ", ["c", "d", "-h", "--help"]),
            ("prog c ", ["bus", "car", "-h", "--help"]),
            ("prog c bu", ["bus "]),
            ("prog c bus ", ["bus", "car", "apple", "orange", "-h", "--help"]),
            ("prog c bus car ", ["bus", "car", "apple", "orange", "-h", "--help"]),
            ("prog c bus appl", ["apple "]),
            # No way to know which completers to run past this point.
            ("prog c bus apple ", ["bus", "car", "apple", "orange", "end", "-h", "--help"]),
            ("prog c bus car apple ", ["bus", "car", "apple", "orange", "end", "-h", "--help"]),
            ("prog c bus car apple end ", ["bus", "car", "apple", "orange", "end", "-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_nargs_zero_or_more(self):
        def make_parser():
            parser = ArgumentParser()
            # default="foo" is necessary to stop argparse trying to validate []
            parser.add_argument("foo", choices=["foo"], nargs="*", default="foo")
            parser.add_argument("bar", choices=["bar"])
            return parser

        expected_outputs = (
            ("prog ", ["foo", "bar", "-h", "--help"]),
            ("prog foo ", ["foo", "bar", "-h", "--help"]),
            ("prog foo bar ", ["foo", "bar", "-h", "--help"]),
            ("prog foo foo bar ", ["foo", "bar", "-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_nargs_optional(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("foo", choices=["foo"], nargs="?")
            parser.add_argument("bar", choices=["bar"])
            return parser

        expected_outputs = (
            ("prog ", ["foo", "bar", "-h", "--help"]),
            ("prog foo ", ["foo", "bar", "-h", "--help"]),
            ("prog foo bar ", ["-h", "--help"]),
            ("prog bar ", ["foo", "bar", "-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_optional_nargs(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--foo", choices=["foo1", "foo2"], nargs=2)
            parser.add_argument("--bar", choices=["bar1", "bar2"], nargs="?")
            parser.add_argument("--baz", choices=["baz1", "baz2"], nargs="*")
            parser.add_argument("--qux", choices=["qux1", "qux2"], nargs="+")
            parser.add_argument("--foobar", choices=["pos", "--opt"], nargs=argparse.REMAINDER)
            return parser

        options = ["--foo", "--bar", "--baz", "--qux", "--foobar", "-h", "--help"]

        expected_outputs = (
            ("prog ", options),
            ("prog --foo ", ["foo1", "foo2"]),
            ("prog --foo foo1 ", ["foo1", "foo2"]),
            ("prog --foo foo1 foo2 ", options),
            ("prog --bar ", ["bar1", "bar2"] + options),
            ("prog --bar bar1 ", options),
            ("prog --baz ", ["baz1", "baz2"] + options),
            ("prog --baz baz1 ", ["baz1", "baz2"] + options),
            ("prog --qux ", ["qux1", "qux2"]),
            ("prog --qux qux1 ", ["qux1", "qux2"] + options),
            ("prog --foobar ", ["pos", "--opt"]),
            ("prog --foobar pos ", ["pos", "--opt"]),
            ("prog --foobar --", ["--opt "]),
            ("prog --foobar --opt ", ["pos", "--opt"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_positional_remainder(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--foo", choices=["foo1", "foo2"])
            parser.add_argument("remainder", choices=["pos", "--opt"], nargs=argparse.REMAINDER)
            return parser

        options = ["--foo", "-h", "--help"]

        expected_outputs = (
            ("prog ", ["pos", "--opt"] + options),
            ("prog --foo foo1 ", ["pos", "--opt"] + options),
            ("prog pos ", ["pos", "--opt"]),
            ("prog -- ", ["pos", "--opt"]),
            ("prog -- --opt ", ["pos", "--opt"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_skipped_completer(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--foo", choices=["--bar"])
        self.assertEqual(self.run_completer(parser, "prog --foo --"), ["--foo "])

    def test_optional_long_short_filtering(self):
        def make_parser():
            parser = ArgumentParser()
            parser.add_argument("--foo")
            parser.add_argument("-b", "--bar")
            parser.add_argument("--baz", "--xyz")
            parser.add_argument("-t")
            parser.add_argument("-z", "--zzz")
            parser.add_argument("-x")
            return parser

        long_opts = "--foo --bar --baz --xyz --zzz --help -x -t".split()
        short_opts = "-b -t -x -z -h --foo --baz --xyz".split()
        expected_outputs = (
            ("prog ", {"long": long_opts, "short": short_opts, True: long_opts + short_opts, False: [""]}),
            ("prog --foo", {"long": ["--foo "], "short": ["--foo "], True: ["--foo "], False: ["--foo "]}),
            (
                "prog --b",
                {
                    "long": ["--bar", "--baz"],
                    "short": ["--bar", "--baz"],
                    True: ["--bar", "--baz"],
                    False: ["--bar", "--baz"],
                },
            ),
            ("prog -z -x", {"long": ["-x "], "short": ["-x "], True: ["-x "], False: ["-x "]}),
        )
        for cmd, outputs in expected_outputs:
            for always_complete_options, output in outputs.items():
                result = self.run_completer(make_parser(), cmd, always_complete_options=always_complete_options)
                self.assertEqual(set(result), set(output))

    def test_exclusive(self):
        def make_parser():
            parser = ArgumentParser(add_help=False)
            parser.add_argument("--foo", action="store_true")
            group = parser.add_mutually_exclusive_group()
            group.add_argument("--bar", action="store_true")
            group.add_argument("--no-bar", action="store_true")
            return parser

        expected_outputs = (
            ("prog ", ["--foo", "--bar", "--no-bar"]),
            ("prog --foo ", ["--foo", "--bar", "--no-bar"]),
            ("prog --bar ", ["--foo", "--bar"]),
            ("prog --foo --no-bar ", ["--foo", "--no-bar"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_mixed_optional_positional(self):
        def make_parser():
            parser = ArgumentParser(add_help=False)
            parser.add_argument("name", choices=["name1", "name2"])
            group = parser.add_mutually_exclusive_group()
            group.add_argument("--get", action="store_true")
            group.add_argument("--set", action="store_true")
            return parser

        expected_outputs = (
            ("prog ", ["--get", "--set", "name1", "name2"]),
            ("prog --", ["--get", "--set"]),
            ("prog -- ", ["name1", "name2"]),
            ("prog --get ", ["--get", "name1", "name2"]),
            ("prog --get name1 ", ["--get "]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(make_parser(), cmd)), set(output))

    def test_append_space(self):
        def make_parser():
            parser = ArgumentParser(add_help=False)
            parser.add_argument("foo", choices=["bar"])
            return parser

        self.assertEqual(self.run_completer(make_parser(), "prog "), ["bar "])
        self.assertEqual(self.run_completer(make_parser(), "prog ", append_space=False), ["bar"])

    def test_exclusive_class(self):
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--foo", dest="types", action="append_const", const=str)
        parser.add_argument("--bar", dest="types", action="append", choices=["bar1", "bar2"])
        parser.add_argument("--baz", choices=["baz1", "baz2"])
        parser.add_argument("--no-bar", action="store_true")

        completer = ExclusiveCompletionFinder(parser, always_complete_options=True)

        expected_outputs = (
            ("prog ", ["--foo", "--bar", "--baz", "--no-bar"]),
            ("prog --baz ", ["baz1", "baz2"]),
            ("prog --baz baz1 ", ["--foo", "--bar", "--no-bar"]),
            ("prog --foo --no-bar ", ["--foo", "--bar", "--baz"]),
            ("prog --foo --bar bar1 ", ["--foo", "--bar", "--baz", "--no-bar"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(parser, cmd, completer=completer)), set(output))

    def test_escape_special_chars(self):
        def make_parser():
            parser = ArgumentParser(add_help=False)
            parser.add_argument("-1", choices=["bar<$>baz"])
            parser.add_argument("-2", choices=[r"\* "])
            parser.add_argument("-3", choices=["\"'"])
            return parser

        self.assertEqual(set(self.run_completer(make_parser(), "prog -1 ")), {r"bar\<\$\>baz "})
        self.assertEqual(set(self.run_completer(make_parser(), "prog -2 ")), {r"\\\*\  "})
        self.assertEqual(set(self.run_completer(make_parser(), "prog -3 ")), {r"\"\' "})
        self.assertEqual(set(self.run_completer(make_parser(), 'prog -3 "')), {r"\"'"})
        self.assertEqual(set(self.run_completer(make_parser(), "prog -3 '")), {"\"'\\''"})

        self.assertEqual(set(self.run_completer(make_parser(), "prog -1 ", shell="tcsh")), {"bar<$>baz "})
        # The trailing space won't actually work correctly in tcsh.
        self.assertEqual(set(self.run_completer(make_parser(), "prog -2 ", shell="tcsh")), {r"\*  "})
        self.assertEqual(set(self.run_completer(make_parser(), "prog -3 ", shell="tcsh")), {"\"' "})
        self.assertEqual(set(self.run_completer(make_parser(), 'prog -3 "', shell="tcsh")), {"\"'"})
        self.assertEqual(set(self.run_completer(make_parser(), "prog -3 '", shell="tcsh")), {"\"'"})

    def test_shellcode_utility(self):
        with NamedTemporaryFile() as fh:
            sc = shellcode(["prog"], use_defaults=True, shell="bash", complete_arguments=None)
            fh.write(sc.encode())
            fh.flush()
            subprocess.check_call(["bash", "-n", fh.name])
        with NamedTemporaryFile() as fh:
            sc = shellcode(["prog", "prog2"], use_defaults=False, shell="bash", complete_arguments=["-o", "nospace"])
            fh.write(sc.encode())
            fh.flush()
            subprocess.check_call(["bash", "-n", fh.name])
        with NamedTemporaryFile() as fh:
            sc = shellcode(
                ["prog"],
                use_defaults=True,
                shell="bash",
                complete_arguments=None,
                argcomplete_script="~/.bash_completion.d/prog.py",
            )
            fh.write(sc.encode())
            fh.flush()
            subprocess.check_call(["bash", "-n", fh.name])
        sc = shellcode(["prog"], use_defaults=False, shell="tcsh", complete_arguments=["-o", "nospace"])
        sc = shellcode(["prog"], use_defaults=False, shell="woosh", complete_arguments=["-o", "nospace"])
        sc = shellcode(["prog"], shell="fish")
        sc = shellcode(["prog"], shell="fish", argcomplete_script="~/.bash_completion.d/prog.py")

    def test_option_help(self):
        os.environ["_ARGCOMPLETE_DFS"] = "\t"
        os.environ["_ARGCOMPLETE_SUPPRESS_SPACE"] = "1"

        p = ArgumentParser()
        p.add_argument("--foo", help="foo" + IFS + "help")
        p.add_argument("--bar", "--bar2", help="bar help")

        subparsers = p.add_subparsers()
        subparsers.add_parser("subcommand", help="subcommand help")
        subparsers.add_parser("subcommand 2", help="subcommand 2 help")

        completions = self.run_completer(p, "prog --f", shell="fish")
        self.assertEqual(set(completions), {"--foo\tfoo help"})

        completions = self.run_completer(p, "prog --b", shell="fish")
        self.assertEqual(set(completions), {"--bar\tbar help", "--bar2\tbar help"})

        completions = self.run_completer(p, "prog sub", shell="fish")
        self.assertEqual(set(completions), {"subcommand\tsubcommand help", "subcommand 2\tsubcommand 2 help"})

        os.environ["_ARGCOMPLETE_DFS"] = "invalid"
        self.assertRaises(Exception, self.run_completer, p, "prog --b", shell="fish")


class TestArgcompleteREPL(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def run_completer(self, parser, completer, command, point=None, **kwargs):
        cword_prequote, cword_prefix, cword_suffix, comp_words, first_colon_pos = split_line(command)

        completions = completer._get_completions(comp_words, cword_prefix, cword_prequote, first_colon_pos)

        return completions

    def test_repl_multiple_complete(self):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        c = CompletionFinder(p, always_complete_options=True)

        completions = self.run_completer(p, c, "prog ")
        assert set(completions) == set(["-h", "--help", "--foo", "--bar"])

        completions = self.run_completer(p, c, "prog --")
        assert set(completions) == set(["--help", "--foo", "--bar"])

    def test_repl_parse_after_complete(self):
        p = ArgumentParser()
        p.add_argument("--foo", required=True)
        p.add_argument("bar", choices=["bar"])

        c = CompletionFinder(p, always_complete_options=True)

        completions = self.run_completer(p, c, "prog ")
        assert set(completions) == set(["-h", "--help", "--foo", "bar"])

        args = p.parse_args(["--foo", "spam", "bar"])
        assert args.foo == "spam"
        assert args.bar == "bar"

        # Both options are required - check the parser still enforces this.
        with self.assertRaises(SystemExit):
            p.parse_args(["--foo", "spam"])
        with self.assertRaises(SystemExit):
            p.parse_args(["bar"])

    def test_repl_subparser_parse_after_complete(self):
        p = ArgumentParser()
        sp = p.add_subparsers().add_parser("foo")
        sp.add_argument("bar", choices=["bar"])

        c = CompletionFinder(p, always_complete_options=True)

        completions = self.run_completer(p, c, "prog foo ")
        assert set(completions) == set(["-h", "--help", "bar"])

        args = p.parse_args(["foo", "bar"])
        assert args.bar == "bar"

        # "bar" is required - check the parser still enforces this.
        with self.assertRaises(SystemExit):
            p.parse_args(["foo"])

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
            ("prog ", ["-h", "--help", "--foo", "--bar", "list", "show", "set"]),
            ("prog li", ["list "]),
            ("prog s", ["show", "set"]),
            ("prog show ", ["--test", "depth", "-h", "--help"]),
            ("prog show d", ["depth "]),
            ("prog show depth ", ["-h", "--help"]),
        )

        for cmd, output in expected_outputs:
            self.assertEqual(set(self.run_completer(p, c, cmd)), set(output))

    def test_repl_reuse_parser_with_positional(self):
        p = ArgumentParser()
        p.add_argument("foo", choices=["aa", "bb", "cc"])
        p.add_argument("bar", choices=["d", "e"])

        c = CompletionFinder(p, always_complete_options=True)

        self.assertEqual(set(self.run_completer(p, c, "prog ")), set(["-h", "--help", "aa", "bb", "cc"]))

        self.assertEqual(set(self.run_completer(p, c, "prog aa ")), set(["-h", "--help", "d", "e"]))

        self.assertEqual(set(self.run_completer(p, c, "prog ")), set(["-h", "--help", "aa", "bb", "cc"]))


class TestSplitLine(unittest.TestCase):
    def setUp(self):
        self._os_environ = os.environ
        os.environ = os.environ.copy()
        os.environ["_ARGCOMPLETE_COMP_WORDBREAKS"] = COMP_WORDBREAKS

    def tearDown(self):
        os.environ = self._os_environ

    def prefix(self, line):
        return split_line(line)[1]

    def wordbreak(self, line):
        return split_line(line)[4]

    def test_simple(self):
        self.assertEqual(self.prefix("a b c"), "c")

    def test_escaped_special(self):
        self.assertEqual(self.prefix(r"a\$b"), "a$b")
        self.assertEqual(self.prefix(r"a\`b"), "a`b")

    def test_unescaped_special(self):
        self.assertEqual(self.prefix("a$b"), "a$b")
        self.assertEqual(self.prefix("a`b"), "a`b")

    @unittest.expectedFailure
    def test_escaped_special_in_double_quotes(self):
        self.assertEqual(self.prefix(r'"a\$b'), "a$b")
        self.assertEqual(self.prefix(r'"a\`b'), "a`b")

    def test_punctuation(self):
        self.assertEqual(self.prefix("a,"), "a,")

    def test_last_wordbreak_pos(self):
        self.assertEqual(self.wordbreak("a"), None)
        self.assertEqual(self.wordbreak("a :b"), 0)
        self.assertEqual(self.wordbreak("a b:c"), 1)
        self.assertEqual(self.wordbreak("a b:c=d"), 3)
        self.assertEqual(self.wordbreak("a b:c=d "), None)
        self.assertEqual(self.wordbreak("a b:c=d e"), None)
        self.assertEqual(self.wordbreak('":b'), None)
        self.assertEqual(self.wordbreak('"b:c'), None)
        self.assertEqual(self.wordbreak('"b:c=d'), None)
        self.assertEqual(self.wordbreak('"b:c=d"'), None)
        self.assertEqual(self.wordbreak('"b:c=d" '), None)


class TestCheckModule(unittest.TestCase):
    def setUp(self):
        self.dir = TempDir(prefix="test_dir_module", dir=".")
        self.dir.__enter__()
        # There is some odd bug that seems to only come up in Python 3.4 where
        # using "." in sys.path sometimes won't find modules, so we'll use the
        # full path each time.
        sys.path.insert(0, os.getcwd())

    def tearDown(self):
        sys.path.pop(0)
        self.dir.__exit__()

    def test_module(self):
        self._mkfile("module.py")
        path = _check_module.find("module")
        self.assertEqual(path, os.path.abspath("module.py"))
        self.assertNotIn("module", sys.modules)

    def test_package(self):
        os.mkdir("package")
        self._mkfile("package/__init__.py")
        self._mkfile("package/module.py")
        path = _check_module.find("package.module")
        self.assertEqual(path, os.path.abspath("package/module.py"))
        self.assertNotIn("package", sys.modules)
        self.assertNotIn("package.module", sys.modules)

    def test_subpackage(self):
        os.mkdir("package")
        self._mkfile("package/__init__.py")
        os.mkdir("package/subpackage")
        self._mkfile("package/subpackage/__init__.py")
        self._mkfile("package/subpackage/module.py")
        path = _check_module.find("package.subpackage.module")
        self.assertEqual(path, os.path.abspath("package/subpackage/module.py"))
        self.assertNotIn("package", sys.modules)
        self.assertNotIn("package.subpackage", sys.modules)
        self.assertNotIn("package.subpackage.module", sys.modules)

    def test_package_main(self):
        os.mkdir("package")
        self._mkfile("package/__init__.py")
        self._mkfile("package/__main__.py")
        path = _check_module.find("package")
        self.assertEqual(path, os.path.abspath("package/__main__.py"))
        self.assertNotIn("package", sys.modules)

    def test_not_package(self):
        self._mkfile("module.py")
        with self.assertRaisesRegex(Exception, "module is not a package"):
            _check_module.find("module.bad")
        self.assertNotIn("module", sys.modules)

    def _mkfile(self, path):
        open(path, "w").close()


class TestShellBase:
    """
    Contains tests which should work in any shell using argcomplete.

    Tests use the test program in this directory named ``prog``.
    All commands are expected to input one of the valid choices
    which is then printed and collected by the shell wrapper.

    Any tabs in the input line simulate the user pressing tab.
    For example, ``self.sh.run_command('prog basic "b\tr\t')`` will
    simulate having the user:

    1. Type ``prog basic "b``
    2. Push tab, which returns ``['bar', 'baz']``, filling in ``a``
    3. Type ``r``
    4. Push tab, which returns ``['bar']``, filling in ``" ``
    5. Push enter, submitting ``prog basic "bar" ``

    The end result should be ``bar`` being printed to the screen.
    """

    sh = None
    expected_failures = []
    skipped = []

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        for name in cls.expected_failures:
            test = getattr(cls, name)

            @unittest.expectedFailure
            def wrapped(self, test=test):
                test(self)

            setattr(cls, name, wrapped)
        for name in cls.skipped:
            test = getattr(cls, name)

            @unittest.skip("skip")
            def wrapped(self, test=test):
                pass

            setattr(cls, name, wrapped)
        super().setUpClass(*args, **kwargs)

    def setUp(self):
        raise NotImplementedError

    def tearDown(self):
        with self.assertRaises((pexpect.EOF, OSError)):
            self.sh.run_command("exit")

    def test_simple_completion(self):
        self.assertEqual(self.sh.run_command("prog basic f\t"), "foo\r\n")

    def test_partial_completion(self):
        self.assertEqual(self.sh.run_command("prog basic b\tr"), "bar\r\n")

    def test_single_quoted_completion(self):
        self.assertEqual(self.sh.run_command("prog basic 'f\t"), "foo\r\n")

    def test_double_quoted_completion(self):
        self.assertEqual(self.sh.run_command('prog basic "f\t'), "foo\r\n")

    def test_unquoted_space(self):
        self.assertEqual(self.sh.run_command("prog space f\t"), "foo bar\r\n")

    def test_quoted_space(self):
        self.assertEqual(self.sh.run_command('prog space "f\t'), "foo bar\r\n")

    def test_continuation(self):
        # This produces 'prog basic foo --', and '--' is ignored.
        self.assertEqual(self.sh.run_command("prog basic f\t--"), "foo\r\n")
        # These do not insert a space, so the '--' is part of the token.
        self.assertEqual(self.sh.run_command("prog cont f\t--"), "foo=--\r\n")
        self.assertEqual(self.sh.run_command("prog cont bar\t--"), "bar/--\r\n")
        self.assertEqual(self.sh.run_command("prog cont baz\t--"), "baz:--\r\n")

    def test_quoted_exact(self):
        self.assertEqual(self.sh.run_command('prog basic "f\t--'), "foo\r\n")

    def test_special_characters(self):
        self.assertEqual(self.sh.run_command("prog spec d\tf"), "d$e$f\r\n")
        self.assertEqual(self.sh.run_command("prog spec x\t"), "x!x\r\n")
        self.assertEqual(self.sh.run_command("prog spec y\t"), "y\\y\r\n")

    def test_special_characters_single_quoted(self):
        self.assertEqual(self.sh.run_command("prog spec 'd\tf'"), "d$e$f\r\n")

    def test_special_characters_double_quoted(self):
        self.assertEqual(self.sh.run_command('prog spec "d\tf"'), "d$e$f\r\n")

    def test_parse_special_characters(self):
        self.assertEqual(self.sh.run_command("prog spec d$e$\tf"), "d$e$f\r\n")
        self.assertEqual(self.sh.run_command("prog spec d$e\tf"), "d$e$f\r\n")
        self.assertEqual(self.sh.run_command("prog spec 'd$e\tf\t"), "d$e$f\r\n")

    def test_parse_special_characters_dollar(self):
        # First tab expands to 'd\$e\$'; completion works with 'd$' but not 'd\$'.
        self.assertEqual(self.sh.run_command('prog spec "d$e\tf\t'), "d$e$f\r\n")

    def test_exclamation_in_double_quotes(self):
        # Exclamation marks cannot be properly escaped within double quotes.
        # 'a!b' == "a"\!"b"
        self.assertEqual(self.sh.run_command('prog spec "x\t'), "x!x\r\n")

    def test_quotes(self):
        self.assertEqual(self.sh.run_command("prog quote 1\t"), "1'1\r\n")
        self.assertEqual(self.sh.run_command("prog quote 2\t"), '2"2\r\n')

    def test_single_quotes_in_double_quotes(self):
        self.assertEqual(self.sh.run_command('prog quote "1\t'), "1'1\r\n")

    def test_single_quotes_in_single_quotes(self):
        # Single quotes cannot be escaped within single quotes.
        # "a'b" == 'a'\''b'
        self.assertEqual(self.sh.run_command("prog quote '1\t"), "1'1\r\n")

    def test_wordbreak_chars(self):
        self.assertEqual(self.sh.run_command("prog break a\tc"), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command("prog break a:b:\tc"), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command("prog break a:b\tc"), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command("prog break 'a\tc'"), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command("prog break 'a:b\tc\t"), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command('prog break "a\tc"'), "a:b:c\r\n")
        self.assertEqual(self.sh.run_command('prog break "a:b\tc\t'), "a:b:c\r\n")

    def test_completion_environment(self):
        self.assertEqual(self.sh.run_command("prog env o\t"), "ok\r\n")

    def test_comp_point(self):
        # Use environment variable to change how prog behaves
        self.assertEqual(self.sh.run_command("export POINT=1"), "")
        self.assertEqual(self.sh.run_command("prog point hi\t"), "13\r\n")
        self.assertEqual(self.sh.run_command("prog point hi \t"), "14\r\n")
        self.assertEqual(self.sh.run_command("prog point 你好嘚瑟\t"), "15\r\n")
        self.assertEqual(self.sh.run_command("prog point 你好嘚瑟 \t"), "16\r\n")


class TestBashZshBase(TestShellBase):
    maxDiff = None

    init_cmd = None
    # 'dummy' argument unused; checks multi-command registration works
    # by passing 'prog' as the second argument.
    install_cmd = 'eval "$(register-python-argcomplete dummy prog)"'

    def setUp(self):
        sh = self.repl_provider()
        output = sh.run_command("echo ready")
        self.assertEqual(output, "ready\r\n")
        path = ":".join([os.path.join(BASE_DIR, "scripts"), TEST_DIR, "$PATH"])
        sh.run_command("export PATH={0}".format(path))
        sh.run_command("export PYTHONPATH={0}".format(BASE_DIR))
        if self.init_cmd is not None:
            output = sh.run_command(self.init_cmd)
            self.assertEqual(output, "")
        if self.install_cmd is not None:
            output = sh.run_command(self.install_cmd)
            self.assertEqual(output, "")
        # Register a dummy completion with an external argcomplete script
        # to ensure this doesn't overwrite our previous registration.
        output = sh.run_command('eval "$(register-python-argcomplete dummy --external-argcomplete-script dummy)"')
        self.assertEqual(output, "")
        self.sh = sh


class TestBash(TestBashZshBase, unittest.TestCase):
    expected_failures = [
        "test_parse_special_characters_dollar",
        "test_exclamation_in_double_quotes",
    ]
    if BASH_MAJOR_VERSION < 4:
        # This requires compopt which is not available in 3.x.
        expected_failures.append("test_quoted_exact")

    def repl_provider(self):
        return bash_repl()

    def test_one_space_after_exact(self):
        """Test exactly one space is appended after an exact match."""
        # Actual command run is 'echo "prog basic foo "'.
        result = self.sh.run_command('prog basic f\t"\1echo "')
        self.assertEqual(result, "prog basic foo \r\n")

    def test_debug_output(self):
        self.assertEqual(self.sh.run_command("prog debug f\t"), "foo\r\n")
        self.sh.run_command("export _ARC_DEBUG=1")
        output = self.sh.run_command("prog debug f\t")
        self.assertIn("PYTHON_ARGCOMPLETE_STDOUT\r\n", output)
        self.assertIn("PYTHON_ARGCOMPLETE_STDERR\r\n", output)
        self.assertTrue(output.endswith("foo\r\n"))

    def test_temp_file(self):
        self.sh.run_command("export ARGCOMPLETE_USE_TEMPFILES=1")
        self.assertEqual(self.sh.run_command("prog basic f\t"), "foo\r\n")
        # Confirm we used a temp file by searching for the debug message.
        self.sh.run_command("export _ARC_DEBUG=1")
        output = self.sh.run_command("prog basic f\t")
        self.assertIn("Using output file ", output)

    def test_nounset(self):
        self.sh.run_command("set -o nounset")
        self.test_simple_completion()


class TestZsh(TestBashZshBase, unittest.TestCase):
    init_cmd = "autoload compinit; compinit -u"

    skipped = [
        "test_parse_special_characters",
        "test_parse_special_characters_dollar",
        "test_comp_point",  # FIXME
        "test_completion_environment",  # FIXME
    ]

    def repl_provider(self):
        return zsh_repl()


class TestBashZshGlobalBase(TestBashZshBase):
    install_cmd = 'eval "$(activate-global-python-argcomplete --dest=-)"'

    def test_redirection_completion(self):
        with TempDir(prefix="test_dir_py", dir="."):
            self.sh.run_command("cd " + os.getcwd())
            self.sh.run_command("echo failure > ./foo.txt")
            self.sh.run_command("echo success > ./foo.\t")
            with open("foo.txt") as f:
                msg = f.read()
            self.assertEqual(msg, "success\n")

    def test_python_completion(self):
        self.sh.run_command("cd " + TEST_DIR)
        self.assertEqual(self.sh.run_command("python3 ./prog basic f\t"), "foo\r\n")

    def test_python_filename_completion(self):
        self.sh.run_command("cd " + TEST_DIR)
        self.assertEqual(self.sh.run_command("python3 ./pro\tbasic f\t"), "foo\r\n")

    def test_python_stuck(self):
        self.sh.run_command("cd " + TEST_DIR)
        self.sh.run_command("python3 ./stuck no\t-input")

    def test_python_not_executable(self):
        """Test completing a script that cannot be run directly."""
        prog = os.path.join(TEST_DIR, "prog")
        with TempDir(prefix="test_dir_py", dir="."):
            shutil.copy(prog, ".")
            self.sh.run_command("cd " + os.getcwd())
            self.sh.run_command("chmod -x ./prog")
            # Ensure prog is no longer able to be run as "./prog".
            self.assertIn("<<126>>", self.sh.run_command('./prog; echo "<<$?>>"'))
            # Ensure completion still functions when run via python.
            self.assertEqual(self.sh.run_command("python3 ./prog basic f\t"), "foo\r\n")

    def test_python_module(self):
        """Test completing a module run with python -m."""
        prog = os.path.join(TEST_DIR, "prog")
        with TempDir(prefix="test_dir_py", dir="."):
            os.mkdir("package")
            open("package/__init__.py", "w").close()
            shutil.copy(prog, "package/prog.py")
            self.sh.run_command("cd " + os.getcwd())
            self.assertEqual(self.sh.run_command("python3 -m package.prog basic f\t"), "foo\r\n")

    def _test_console_script(self, package=False, wheel=False):
        with TempDir(prefix="test_dir_py", dir="."):
            self.sh.run_command("cd " + os.getcwd())
            self.sh.run_command("export PATH=$PATH:./bin")
            self.sh.run_command("export PYTHONPATH=.:$PYTHONPATH")
            test_package = os.path.join(TEST_DIR, "test_package")
            command = "pip install {} --target .".format(test_package)
            if not wheel:
                command += " --no-binary :all:"
            install_output = self.sh.run_command(command)
            self.assertEqual(self.sh.run_command("echo $?"), "0\r\n", install_output)
            command = "test-module"
            if package:
                command = "test-package"
            command += " a\t"
            self.assertEqual(self.sh.run_command(command), "arg\r\n")

    def test_console_script_module(self):
        """Test completing a console_script for a module."""
        self._test_console_script()

    def test_console_script_package(self):
        """Test completing a console_script for a package."""
        self._test_console_script(package=True)

    def test_console_script_module_wheel(self):
        """Test completing a console_script for a module from a wheel."""
        self._test_console_script(wheel=True)

    def test_console_script_package_wheel(self):
        """Test completing a console_script for a package from a wheel."""
        self._test_console_script(package=True, wheel=True)


@unittest.skipIf(BASH_MAJOR_VERSION < 4, "complete -D not supported")
class TestBashGlobal(TestBash, TestBashZshGlobalBase):
    pass


class TestZshGlobalExplicit(TestZsh, TestBashZshGlobalBase):
    pass


class TestZshGlobalImplicit(TestZsh, TestBashZshGlobalBase):
    # In zsh, the file is typically not sourced directly;
    # it is added to fpath and autoloaded by the completion system.
    zsh_fpath = os.path.join(os.path.abspath(os.path.dirname(argcomplete.__file__)), "bash_completion.d")
    init_cmd = f'fpath=( {zsh_fpath} "${{fpath[@]}}" ); autoload compinit; compinit -u'
    install_cmd = None


class Shell:
    def __init__(self, shell):
        self.child = pexpect.spawn(shell, encoding="utf-8")

    def run_command(self, command):
        try:
            self.child.sendline(r"echo -n \#\#\#; {0}; echo -n \#\#\#".format(command))
            self.child.expect_exact("###", timeout=5)
            self.child.expect_exact("###", timeout=5)
            return self.child.before
        finally:
            # Send Ctrl+C in case we get stuck.
            self.child.sendline("\x03")


class Warn(unittest.TestCase):
    def test_warn(self):
        @contextlib.contextmanager
        def redirect_debug_stream(stream):
            debug_stream = argcomplete.io.debug_stream
            argcomplete.io.debug_stream = stream
            try:
                yield
            finally:
                argcomplete.io.debug_stream = debug_stream

        test_stream = StringIO()
        with redirect_debug_stream(test_stream):
            warn("My hands are tied")

        self.assertEqual("\nMy hands are tied\n", test_stream.getvalue())


if __name__ == "__main__":
    unittest.main()
