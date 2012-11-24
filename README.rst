argcomplete - Bash completion for argparse
==========================================

Argcomplete provides easy and extensible automatic tab completion of arguments and options for your Python script.

It makes two assumptions:

* You're using bash as your shell
* You're using argparse to manage your command line options

Argcomplete is particularly useful if your program has lots of options or subparsers, and if you can suggest
completions for your argument/option values (for example, if the user is browsing resources over the network).

Installation
------------
::

    pip install argcomplete

Synopsis
--------

Python code (e.g. ``my-awesome-script.py``)::

    import argcomplete, argparse
    parser = argparse.ArgumentParser()
    ...
    argcomplete.autocomplete(parser)
    parser.parse()
    ...

Shellcode (to be put in e.g. ``.bashrc``)::

    eval "$(register-python-argcomplete my-awesome-script.py)"

argcomplete.autocomplete(*parser*)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This method is the entry point to the module. It must be called **after** ArgumentParser construction is complete, but
**before** the ``ArgumentParser.parse()`` method is called. The method looks for an environment variable that the
completion hook shellcode sets, and if it's there, collects completions, prints them to standard output, and exits.
Otherwise, it returns to the caller immediately.

Specifying completers
---------------------
You can specify custom completion functions for your options and arguments. Completers are called with the
following keyword arguments:

* ``prefix``: The prefix text of the last word before the cursor on the command line. All returned completions should begin with this prefix.
* ``action``: The ``argparse.Action`` instance that this completer was called for.
* ``parser``: The ``argparse.ArgumentParser`` instance that the action was taken by.

Completers should return their completions as a list of strings. An example completer for names of environment
variables might look like this::

    def EnvironCompleter(prefix, **kwargs):
        return (v for v in os.environ if v.startswith(prefix))

If you specify the ``choices`` keyword for an argparse option or argument (and don't specify a completer), it will be
used for completions. 

A completer that is initialized with a set of all possible choices of values for its action might look like this::

    class ChoicesCompleter(object):
        def __init__(self, choices=[]):
            self.choices = choices

        def __call__(self, prefix, **kwargs):
        return (c for c in self.choices if c.startswith(prefix))

To specify a completer for an argument or option, set the ``completer`` attribute of its associated action. An easy
way to do this at definition time is::

    from argcomplete.completers import EnvironCompleter

    parser = argparse.ArgumentParser()
    parser.add_argument("--env-var1").completer = EnvironCompleter
    parser.add_argument("--env-var2").completer = EnvironCompleter
    argcomplete.autocomplete(parser)

The following two ways to specify a static set of choices are equivalent for completion purposes::

    from argcomplete.completers import ChoicesCompleter

    parser.add_argument("--protocol", choices=('http', 'https', 'ssh', 'rsync', 'wss'))
    parser.add_argument("--proto").completer=ChoicesCompleter(('http', 'https', 'ssh', 'rsync', 'wss'))


Acknowledgments
---------------

Inspired and informed by the optcomplete_ module by Martin Blais.

.. _optcomplete: http://pypi.python.org/pypi/optcomplete

Links
-----

* `Home page <https://github.com/kislyuk/argcomplete>`_
* `Docs <https://argcomplete.readthedocs.org/en/latest/>`_
* `On pypi <http://pypi.python.org/pypi/argcomplete>`_
