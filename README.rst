Warning: under development. Some things are a bit messy.

argcomplete
===========

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
