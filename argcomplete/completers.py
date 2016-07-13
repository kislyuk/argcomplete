# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import subprocess
from .compat import str, sys_encoding

def _call(*args, **kwargs):
    try:
        return subprocess.check_output(*args, **kwargs).decode(sys_encoding).splitlines()
    except subprocess.CalledProcessError:
        return []

class ChoicesCompleter(object):
    def __init__(self, choices):
        self._choices = None

        if callable(choices):
            self._load_choices = (lambda self:
                                  setattr(self, 'choices', choices()))
        else:
            self.choices = choices

    def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

    @property
    def choices(self):
        if self._choices is None:
            self._load_choices(self)

        return self._choices

    @choices.setter
    def choices(self, iterable):
        """
        Initialize the choices with items from the given iterable.

        This also normalizes them to neat strings.
        """
        self._choices = []
        for choice in iterable:
            if isinstance(choice, bytes):
                choice = choice.decode(sys_encoding)
            if not isinstance(choice, str):
                choice = str(choice)
            self._choices.append(choice)

def EnvironCompleter(prefix, **kwargs):
    return (v for v in os.environ if v.startswith(prefix))

class FilesCompleter(object):
    """
    File completer class, optionally takes a list of allowed extensions
    """

    def __init__(self, allowednames=(), directories=True):
        # Fix if someone passes in a string instead of a list
        if isinstance(allowednames, (str, bytes)):
            allowednames = [allowednames]

        self.allowednames = [x.lstrip("*").lstrip(".") for x in allowednames]
        self.directories = directories

    def __call__(self, prefix, **kwargs):
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

class _FilteredFilesCompleter(object):
    def __init__(self, predicate):
        """
        Create the completer

        A predicate accepts as its only argument a candidate path and either
        accepts it or rejects it.
        """
        assert predicate, "Expected a callable predicate"
        self.predicate = predicate

    def __call__(self, prefix, **kwargs):
        """
        Provide completions on prefix
        """
        target_dir = os.path.dirname(prefix)
        try:
            names = os.listdir(target_dir or ".")
        except:
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
    def __init__(self):
        _FilteredFilesCompleter.__init__(self, predicate=os.path.isdir)
