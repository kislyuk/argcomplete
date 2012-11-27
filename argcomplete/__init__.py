import os, sys, argparse, shlex, pipes, contextlib, subprocess
from . import completers
from .my_argparse import IntrospectiveArgumentParser

if '_ARC_DEBUG' in os.environ:
    try:
        debug_stream = os.fdopen(9, 'wb')
    except:
        debug_stream = sys.stderr
else:
    debug_stream = open(os.devnull, 'w')

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

class ArgcompleteException(Exception):
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
                print >>debug_stream, "word", word, "split"
                return split_word(word)
            words.append(word)
        except ValueError as e:
            print >>debug_stream, "word", lexer.token, "split (lexer stopped)"
            if lexer.instream.tell() >= point:
                return split_word(lexer.token)
            else:
                raise ArgcompleteException("unexpected state? TODO")

def autocomplete(argument_parser, always_complete_options=True, output_stream=None):
    '''
    :param argument_parser: The argument parser to autocomplete on
    :type argument_parser: :class:`argparse.ArgumentParser`
    :param always_complete_options: Specifies whether or not to autocomplete options even if an option string opening character (normally ``-``) has not been entered.
    :type always_complete_options: boolean
    '''

    if '_ARGCOMPLETE' not in os.environ:
        # not an argument completion invocation
        return

    if output_stream is None:
        try:
            output_stream = os.fdopen(8, 'wb')
        except:
            print >>debug_stream, "Unable to open fd 8 for writing, quitting"
            os._exit(1)

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
    Since argparse doesn't support much introspection, we monkey-patch it to replace the parse_known_args method and
    all actions with hooks that tell us which action was last taken or about to be taken, and let us have the parser
    figure out which subparsers need to be activated (then recursively monkey-patch those).
    This way we never execute the original actions, in case they have any side effects.
    We save all active ArgumentParsers to extract all their possible option names later.
    '''
    def patchArgumentParser(parser):
        parser.__class__ = IntrospectiveArgumentParser
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

    print >>debug_stream, "Active parsers:", active_parsers
    print >>debug_stream, "Visited actions:", visited_actions
    completions = []

    # Subcommand and options completion
    for parser in active_parsers:
        print >>debug_stream, "Examining parser", parser
        for action in parser._actions:
            print >>debug_stream, "Examining action", action
            if isinstance(action, argparse._SubParsersAction):
                subparser_activated = False
                for subparser in action._name_parser_map.values():
                    if subparser in active_parsers:
                        subparser_activated = True
                if not subparser_activated:
                    completions += [subcmd for subcmd in action.choices.keys() if subcmd.startswith(cword_prefix)]
            elif always_complete_options or (len(cword_prefix) > 0 and cword_prefix[0] in parser.prefix_chars):
                completions += [option for option in action.option_strings if option.startswith(cword_prefix)]

        print >>debug_stream, "Active actions (L={l}): {a}".format(l=len(parser.active_actions), a=parser.active_actions)

        for active_action in parser.active_actions:
            print >>debug_stream, "Activating completion for", active_action, active_action._orig_class
            #completer = getattr(active_action, 'completer', DefaultCompleter())
            completer = getattr(active_action, 'completer', None)

            if completer is None and active_action.choices is not None:
                if not isinstance(active_action, argparse._SubParsersAction):
                    completer = completers.ChoicesCompleter(active_action.choices)

            if completer:
                print >>debug_stream, "Completions:", list(completer(prefix=cword_prefix, parser=parser, action=active_action))
                completions += [c for c in completer(prefix=cword_prefix,
                                                     parser=parser,
                                                     action=active_action) if c.startswith(cword_prefix)]
            elif not isinstance(active_action, argparse._SubParsersAction):
                print >>debug_stream, "Completer not available, falling back"
                try:
                    # TODO: what happens if completions contain newlines? How do I make compgen use IFS?
                    completions += subprocess.check_output("compgen -A file '{p}'".format(p=cword_prefix),
                                                           shell=True).splitlines()
                except subprocess.CalledProcessError:
                    pass

    # De-duplicate completions
    seen = set()
    completions = [c for c in completions if c not in seen and not seen.add(c)]

    continuation_chars = '=/:'
    # If there's only one completion, and it doesn't end with a continuation char, add a space
    if len(completions) == 1 and completions[0][-1] not in continuation_chars:
        completions[0] += ' '

    # print >>debug_stream, "\nReturning completions:", [pipes.quote(c) for c in completions]
    # print ifs.join([pipes.quote(c) for c in completions])
    # print ifs.join([escape_completion_name_str(c) for c in completions])

    print >>debug_stream, "\nReturning completions:", completions
    output_stream.write(ifs.join(completions))
    output_stream.flush()
    # os.fsync(output_stream.fileno()) - this raises an error, why?
    debug_stream.flush()
    # os.fsync(debug_stream.fileno())

    if '_ARC_DEBUG' in os.environ:
        exit()
    else:
        # Avoid firing any atexits
        os._exit(0)

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
