# Copyright 2012-2023, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

import argparse
import os
import subprocess
from collections.abc import Iterable
from typing import Any, Callable, List, Union


def _call(*args, **kwargs) -> List[str]:
    # TODO: replace "universal_newlines" with "text" once 3.6 support is dropped
    kwargs["universal_newlines"] = True
    try:
        return subprocess.check_output(*args, **kwargs).splitlines()
    except subprocess.CalledProcessError:
        return []


class BaseCompleter:
    """
    This is the base class that all argcomplete completers should subclass.
    """

    def __call__(
        self, *, prefix: str, action: argparse.Action, parser: argparse.ArgumentParser, parsed_args: argparse.Namespace
    ) -> Iterable[str]:
        raise NotImplementedError("This method should be implemented by a subclass.")


class ChoicesCompleter(BaseCompleter):
    def __init__(self, choices: Iterable[Any]):
        self.choices = choices

    def _convert(self, choice: Any) -> str:
        if not isinstance(choice, str):
            return str(choice)
        return choice

    def __call__(self, **kwargs) -> Iterable[str]:
        return (self._convert(c) for c in self.choices)


EnvironCompleter = ChoicesCompleter(os.environ)


class FilesCompleter(BaseCompleter):
    """
    File completer class, optionally takes a list of allowed extensions
    """

    def __init__(self, allowednames: Union[str, Iterable[str]] = (), directories: bool = True):
        # Fix if someone passes in a string instead of a list
        if isinstance(allowednames, str):
            allowednames = [allowednames]

        self.allowednames = [x.lstrip("*").lstrip(".") for x in allowednames]
        self.directories = directories

    def __call__(self, *, prefix: str, **kwargs) -> Iterable[str]:
        completion = []
        if self.allowednames:
            if self.directories:
                files = _call(["bash", "-c", "compgen -A directory -- '{p}'".format(p=prefix)])
                completion += [f + "/" for f in files]
            for x in self.allowednames:
                completion += _call(["bash", "-c", "compgen -A file -X '!*.{0}' -- '{p}'".format(x, p=prefix)])
        else:
            completion += _call(["bash", "-c", "compgen -A file -- '{p}'".format(p=prefix)])
            anticomp = _call(["bash", "-c", "compgen -A directory -- '{p}'".format(p=prefix)])
            completion = list(set(completion) - set(anticomp))

            if self.directories:
                completion += [f + "/" for f in anticomp]
        return completion


class _FilteredFilesCompleter(BaseCompleter):
    def __init__(self, predicate: Callable[[str], bool]):
        """
        Create the completer

        A predicate accepts as its only argument a candidate path and either
        accepts it or rejects it.
        """
        self.predicate = predicate

    def __call__(self, *, prefix: str, **kwargs) -> Iterable[str]:
        """
        Provide completions on prefix
        """
        target_dir = os.path.dirname(prefix)
        try:
            names = os.listdir(target_dir or ".")
        except Exception:
            return  # empty iterator
        incomplete_part = os.path.basename(prefix)
        # Iterate on target_dir entries and filter on given predicate
        for name in names:
            if not name.startswith(incomplete_part):
                continue
            candidate = os.path.join(target_dir, name)
            if not self.predicate(candidate):
                continue
            yield candidate + "/" if os.path.isdir(candidate) else candidate


class DirectoriesCompleter(_FilteredFilesCompleter):
    def __init__(self) -> None:
        _FilteredFilesCompleter.__init__(self, predicate=os.path.isdir)


class SuppressCompleter(BaseCompleter):
    """
    A completer used to suppress the completion of specific arguments
    """

    def __init__(self) -> None:
        pass

    def suppress(self) -> bool:
        """
        Decide if the completion should be suppressed
        """
        return True
