# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

# mypy: implicit-reexport=True

from __future__ import annotations

from . import completers
from .completers import ChoicesCompleter, DirectoriesCompleter, EnvironCompleter, FilesCompleter, SuppressCompleter
from .exceptions import ArgcompleteException
from .finders import CompletionFinder, ExclusiveCompletionFinder, safe_actions
from .io import debug, mute_stderr, warn
from .lexers import split_line
from .packages._argparse import get_num_consumed_args
from .shell_integration import shellcode

autocomplete: CompletionFinder = CompletionFinder()
autocomplete.__doc__ = """ Use this to access argcomplete. See :meth:`argcomplete.CompletionFinder.__call__()`. """
