# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

import os, sys

class ChoicesCompleter(object):
    def __init__(self, choices=[]):
        self.choices = choices

    def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

def EnvironCompleter(prefix, **kwargs):
    return (v for v in os.environ if v.startswith(prefix))
