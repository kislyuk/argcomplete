import os, sys

def EnvironCompleter(text):
    return (v for v in os.environ if v.startswith(text))
