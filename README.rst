argcomplete - Bash completion for argparse
==========================================
Argcomplete provides easy and extensible automatic tab completion of arguments for your Python script.

It makes two assumptions:

* You're using bash as your shell
* You're using argparse to manage your command line arguments/options

Argcomplete is particularly useful if your program has lots of options or subparsers, and if yor program can dynamically
generate completions for your argument/option values (for example, if the user is browsing resources over the network).

Installation
------------
::

    pip install argcomplete
    activate-global-python-argcomplete

See `Activating global completion`_ below if the second step reports an error.

Synopsis
--------
Python code (e.g. ``my-awesome-script.py``)::

    #!/usr/bin/env python
    # PYTHON_ARGCOMPLETE_OK
    import argcomplete, argparse
    parser = argparse.ArgumentParser()
    ...
    argcomplete.autocomplete(parser)
    args = parser.parse_args()
    ...

Shellcode (only necessary if global completion is not activated - see `Activating global completion`_ below), to be put in e.g. ``.bashrc``::

    eval "$(register-python-argcomplete my-awesome-script.py)"

argcomplete.autocomplete(*parser*)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This method is the entry point to the module. It must be called **after** ArgumentParser construction is complete, but
**before** the ``ArgumentParser.parse_args()`` method is called. The method looks for an environment variable that the
completion hook shellcode sets, and if it's there, collects completions, prints them to the output stream (fd 8 by
default), and exits. Otherwise, it returns to the caller immediately.

.. admonition:: Side effects

 Argcomplete gets completions by running your program. It intercepts the execution flow at the moment
 ``argcomplete.autocomplete()`` is called. After sending completions, it exits using ``exit_method``. This means if
 your program has any side effects that happen before ``argcomplete`` is called, those side effects will happen every
 time the user presses ``<TAB>`` (although anything your program prints to stdout or stderr will be suppressed). For
 this reason it's best to construct the argument parser and call ``argcomplete.autocomplete()`` as early as
 possible in your execution flow.

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

To specify a completer for an argument or option, set the ``completer`` attribute of its associated action. An easy
way to do this at definition time is::

    from argcomplete.completers import EnvironCompleter

    parser = argparse.ArgumentParser()
    parser.add_argument("--env-var1").completer = EnvironCompleter
    parser.add_argument("--env-var2").completer = EnvironCompleter
    argcomplete.autocomplete(parser)

If you specify the ``choices`` keyword for an argparse option or argument (and don't specify a completer), it will be
used for completions. 

A completer that is initialized with a set of all possible choices of values for its action might look like this::

    class ChoicesCompleter(object):
        def __init__(self, choices=[]):
            self.choices = choices

        def __call__(self, prefix, **kwargs):
            return (c for c in self.choices if c.startswith(prefix))

The following two ways to specify a static set of choices are equivalent for completion purposes::

    from argcomplete.completers import ChoicesCompleter

    parser.add_argument("--protocol", choices=('http', 'https', 'ssh', 'rsync', 'wss'))
    parser.add_argument("--proto").completer=ChoicesCompleter(('http', 'https', 'ssh', 'rsync', 'wss'))

Activating global completion
----------------------------
The script ``activate-global-python-argcomplete`` will try to install the file
``etc/bash_completion.d/python-argcomplete.sh`` (`see on GitHub`_) into an appropriate location on your system
(``/etc/bash_completion.d/`` or ``~/.bash_completion.d/``). If it
fails, but you know the correct location of your bash completion scripts directory, you can specify it with ``--dest``::

    activate-global-python-argcomplete --dest=/path/to/bash_completion.d

Otherwise, you can redirect its shellcode output into a file::

    activate-global-python-argcomplete --dest=- > file

The file's contents should then be sourced in e.g. ``~/.bashrc``.

In global completion mode, bash will look for
the string **PYTHON_ARGCOMPLETE_OK** in the first 1024 bytes of any executable that it's running completion for, and if
it's found, follow the rest of the argcomplete protocol as described above. This frees you from the requirement to
register each argcomplete-capable executable separately.

.. note:: Global completion requires bash support for ``complete -D``, which was introduced in bash 4.2. On older systems, you will need to update bash to use this feature. Check the version of the running copy of bash with ``echo $BASH_VERSION``.

.. _`see on GitHub`: https://github.com/kislyuk/argcomplete/tree/master/etc/bash_completion.d/python-argcomplete.sh

Acknowledgments
---------------
Inspired and informed by the optcomplete_ module by Martin Blais.

.. _optcomplete: http://pypi.python.org/pypi/optcomplete

Links
-----
* `Project home page (GitHub) <https://github.com/kislyuk/argcomplete>`_
* `Documentation (Read the Docs) <https://argcomplete.readthedocs.org/en/latest/>`_
* `Package distribution (PyPI) <http://pypi.python.org/pypi/argcomplete>`_

Bugs
~~~~
Please report bugs, issues, feature requests, etc. on `GitHub <https://github.com/kislyuk/argcomplete/issues>`_.

.. image:: https://secure.travis-ci.org/kislyuk/argcomplete.png
        :target: https://secure.travis-ci.org/kislyuk/argcomplete
