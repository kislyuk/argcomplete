# Copyright 2012-2013, Andrey Kislyuk and argcomplete contributors.
# Licensed under the Apache License. See https://github.com/kislyuk/argcomplete for more info.

import os

class ChoicesCompleter(object):
    def __init__(self, choices=[]):
        self.choices = choices

    def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

def EnvironCompleter(prefix, **kwargs):
    return (v for v in os.environ if v.startswith(prefix))

class FilesCompleter(object):
    'File completer class, optionally takes a list of allowed extensions'
    def __init__(self,allowednames=()):
        self.allowednames = [x.lstrip('*').lstrip('.') for x in allowednames]

    def __call__(self, prefix, **kwargs):
        completion = []
        try:
            if self.allowednames:
                for x in self.allowednames:
                    completion += subprocess.check_output(['bash', '-c', "compgen -A file -X '!*.{0}' -- '{1}'".format(x,prefix)]).decode().splitlines()
            else:
                completion += subprocess.check_output(['bash', '-c', "compgen -A file -- '{p}'".format(p=prefix)]).decode().splitlines()
        except subprocess.CalledProcessError:
            pass
        return completion

