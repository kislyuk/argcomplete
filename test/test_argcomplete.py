#!/usr/bin/env python
# -*- coding: utf-8 -*-
import locale
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argparse import ArgumentParser
from argcomplete import *

IFS = '\013'

class TestArgcomplete:

    def run_completer(self, parser, command, point=None,
                      tmpdir=None, monkeypatch=None):
        with open('testfile', 'wb+') as t:
            if monkeypatch is not None:
                monkeypatch.setenv('_ARGCOMPLETE', "yes")
                monkeypatch.setenv('_ARC_DEBUG', "yes")
                monkeypatch.setenv('IFS', IFS)
                #os.environ['COMP_LINE'] = command.encode(locale.getpreferredencoding())
                monkeypatch.setenv('COMP_LINE', command)
                monkeypatch.setenv('COMP_POINT', point if point else str(len(command)))
                monkeypatch.setenv('COMP_WORDBREAKS', '"\'@><=;|&(:')
            with pytest.raises(SystemExit):
                autocomplete(parser, output_stream=t,
                              exit_method=sys.exit)
            t.seek(0)
            return t.read().decode(locale.getpreferredencoding()).split(IFS)

    def test_basic_completion(self, tmpdir, monkeypatch):
        p = ArgumentParser()
        p.add_argument("--foo")
        p.add_argument("--bar")

        completions = self.run_completer(p, "prog ", tmpdir=tmpdir,
                                         monkeypatch=monkeypatch)
        assert(set(completions) == set(['-h', '--help', '--foo', '--bar']))

    def test_completers(self, tmpdir, monkeypatch):
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
            assert set(self.run_completer(make_parser(), cmd,
                                          tmpdir=tmpdir,
                                          monkeypatch=monkeypatch),
                       ) == set(output)

    def test_file_completion(self, tmpdir):
        # setup and teardown should probably be in class
        from argcomplete.completers import FilesCompleter
        tmpdir.chdir()
        fc = FilesCompleter()
        os.makedirs(os.path.join('abcdef', 'klm'))
        assert fc('a') == ['abcdef/']
        os.makedirs(os.path.join('abcaha', 'klm'))
        with open('abcxyz', 'w') as fp:
            fp.write('test')
        assert set(fc('a')) == set(['abcdef/', 'abcaha/', 'abcxyz'])

    def test_subparsers(self, tmpdir, monkeypatch):
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
            assert set(self.run_completer(make_parser(), cmd,
                                          tmpdir=tmpdir,
                                          monkeypatch=monkeypatch)
                       ) == set(output)

        @pytest.mark.skipif(sys.version_info >= (2, 6))
        #currently works on either 2 or 3, but not both
        def test_non_ascii(self, tmpdir, monkeypatch):
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
                assert set(self.run_completer(make_parser(), cmd,
                                          tmpdir=tmpdir,
                                          monkeypatch=monkeypatch)
                           ) == set(output)

if __name__ == '__main__':
    pytest.main()
