'''
:mod:`argcomplete`
==================

Argcomplete provides easy and extensible automatic tab completion of arguments and options for your Python script.

It makes two assumptions:

* You're using bash as your shell
* You're using argparse to manage your command line options

Argcomplete is particularly useful if your program has lots of options or subparsers, and if you can suggest
completions for your argument/option values (for example, if the user is browsing resources over the network).

Synopsis
--------

Python code (e.g. my-awesome-script.py)::

    import argcomplete, argparse
    parser = argparse.ArgumentParser()
    ...
    argcomplete.autocomplete(parser)
    parser.parse()

Shellcode (e.g. .bashrc)::

    eval "$(register-python-argcomplete my-awesome-script.py)"

Specifying completers
---------------------

You can specify custom completion functions for your options and arguments. Completers are called with one argument,
the prefix text that all completions should match. Completers should return their completions as a list of strings.
An example completer for names of environment variables might look like this::

    def EnvironCompleter(text):
        return (v for v in os.environ if v.startswith(text))

To specify a completer for an argument or option, set the "completer" attribute of its associated action. An easy
way to do this at definition time is::

    from argcomplete.completers import EnvironCompleter

    parser = argparse.ArgumentParser()
    parser.add_argument("--env-var1").completer = EnvironCompleter
    parser.add_argument("--env-var2").completer = EnvironCompleter
    argcomplete.autocomplete(parser)

'''

class DefaultCompleter(object):
    def __init__(self):
        pass

    def __call__(self, text):
        return []

import os, sys, argparse, shlex, pipes, contextlib
from . import completers

#if '_DEBUG' in os.environ:
debug_stream = sys.stderr
#else:
debug_stream = open('/dev/null', 'w')

BASH_FILE_COMPLETION_FALLBACK = 79
BASH_DIR_COMPLETION_FALLBACK = 80

@contextlib.contextmanager
def mute_stdout():
    stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    yield
    sys.stdout = stdout

@contextlib.contextmanager
def mute_stderr():
    stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    yield
    sys.stderr = stderr

def ArgcompleteException(Exception):
    pass

def split_line(line, point):
    lexer = shlex.shlex(line)
    lexer.whitespace_split = True
    words = []

    def split_word(word):
        # TODO: make this less ugly
        point_in_word = len(word) + point - lexer.instream.tell()
        if isinstance(lexer.state, basestring) and lexer.state in lexer.whitespace:
            point_in_word += 1
        if point_in_word > len(word):
            print >>debug_stream, "In trailing whitespace"
            words.append(word)
            word = ''
        prefix, suffix = word[:point_in_word], word[point_in_word:]
        return prefix, suffix, words

    while True:
        try:
            word = lexer.get_token()
            if word == lexer.eof:
                raise ArgcompleteException("Unexpected end of input")
            if lexer.instream.tell() >= point:
                print >>debug_stream, "word", word, "split", split_word(word)
                return split_word(word)
            words.append(word)
        except ValueError as e:
            print >>debug_stream, "word", lexer.token, "split", split_word(lexer.token)
            if lexer.instream.tell() >= point:
                return split_word(lexer.token)
            else:
                raise ArgcompleteException("unexpected state? TODO")

def autocomplete(argument_parser, always_complete_options=True):
    if '_ARGCOMPLETE' not in os.environ:
        # not an argument completion invocation
        return

    # print >> debug_stream, ""
    # for v in 'COMP_CWORD', 'COMP_LINE', 'COMP_POINT', 'COMP_TYPE', 'COMP_KEY', 'COMP_WORDBREAKS', 'COMP_WORDS':
    #     print >> debug_stream, v, os.environ[v]

    ifs = os.environ.get('IFS', ' ')
    comp_line = os.environ['COMP_LINE']
    comp_point = int(os.environ['COMP_POINT'])
    cword_prefix, cword_suffix, comp_words = split_line(comp_line, comp_point)
    print >>debug_stream, "\nPREFIX: '{p}'".format(p=cword_prefix), "\nSUFFIX: '{s}'".format(s=cword_suffix), "\nWORDS:", comp_words

    active_parsers = [argument_parser]
    visited_actions = []

    '''
    Since argparse doesn't support much introspection, we monkey-patch it to replace all actions with hooks that
    let us have the parser figure out which subparsers need to be activated (then recursively monkey-patch those).
    We save all active ArgumentParsers to extract all their possible option values later.
    '''
    def patchArgumentParser(parser):
        for action in parser._actions:
            # TODO: accomplish this with super
            class IntrospectAction(action.__class__):
                def __call__(self, parser, namespace, values, option_string=None):
                    print >>debug_stream, 'Action stub called on', self
                    print >>debug_stream, '\targs:', parser, namespace, values, option_string
                    print >>debug_stream, '\torig class:', self._orig_class
                    print >>debug_stream, '\torig callable:', self._orig_callable

                    visited_actions.append(self)

                    if self._orig_class == argparse._SubParsersAction:
                        print >>debug_stream, 'orig class is a subparsers action: patching and running it'
                        active_subparser = self._name_parser_map[values[0]]
                        patchArgumentParser(active_subparser)
                        active_parsers.append(active_subparser)
                        self._orig_callable(parser, namespace, values, option_string=option_string)
            if getattr(action, "_orig_class", None):
                raise ArgcompleteException("unexpected condition")
            action._orig_class = action.__class__
            action._orig_callable = action.__call__
            action.__class__ = IntrospectAction

    patchArgumentParser(argument_parser)

    try:
        print >> debug_stream, "invoking parser with", comp_words[1:]
        with mute_stderr():
            a = argument_parser.parse_known_args(comp_words[1:])
        print >> debug_stream, "parsed args:", a
    except BaseException as e:
        print >> debug_stream, "\nexception", type(e), str(e), "while parsing args"

    print >>debug_stream, "\nActive parsers:", active_parsers
    print >>debug_stream, "Visited actions:", visited_actions
    completions = []

    # Subcommand and options completion
    for parser in active_parsers:
        for action in parser._actions:
            print >>debug_stream, "Examining", action
            if isinstance(action, argparse._SubParsersAction):
                subparser_activated = False
                for subparser in action._name_parser_map.values():
                    if subparser in active_parsers:
                        subparser_activated = True
                if not subparser_activated:
                    completions += [subcmd for subcmd in action.choices.keys() if subcmd.startswith(cword_prefix)]
            elif always_complete_options or (len(cword_prefix) > 0 and cword_prefix[0] in parser.prefix_chars):
                completions += [option for option in action.option_strings if option.startswith(cword_prefix)]

            if len(comp_words) > 0 and comp_words[-1] in action.option_strings:
                print >>debug_stream, "Activating completion for", action
                completer = getattr(action, 'completer', DefaultCompleter())
                print >>debug_stream, "Completions:", completer(cword_prefix)
                completions += completer(cword_prefix)

    continuation_chars = '=/:'
    # If there's only one completion, and it doesn't end with a continuation char, add a space
    if len(completions) == 1 and completions[0][-1] not in continuation_chars:
        completions[0] += ' '

#    print >>debug_stream, "\nReturning completions:", [pipes.quote(c) for c in completions]
#    print ifs.join([pipes.quote(c) for c in completions])
#    print ifs.join([escape_completion_name_str(c) for c in completions])

    print >>debug_stream, "\nReturning completions:", completions
    print ifs.join(completions)
    exit()

    # COMP_CWORD
    # COMP_LINE
    # COMP_POINT
    # COMP_TYPE
    # COMP_KEY
    # COMP_WORDBREAKS
    # COMP_WORDS
    # ifs = os.environ.get('IFS')
    # cwords = os.environ['COMP_WORDS'].split(ifs)
    # cline = os.environ['COMP_LINE']
    # cpoint = int(os.environ['COMP_POINT'])
    # cword = int(os.environ['COMP_CWORD'])
