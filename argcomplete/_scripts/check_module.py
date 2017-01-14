import imp
import os
import sys


def find(spec):
    module = None
    for name in spec.split('.'):
        f, module, _ = imp.find_module(name, module and [module])
        if f is not None:
            f.close()
    if f is None:
        module = os.path.join(module, '__main__.py')
    return module


if __name__ == '__main__':
    with open(find(sys.argv[1])) as f:
        head = f.read(1024)
    if 'PYTHON_ARGCOMPLETE_OK' not in head:
        raise Exception('marker not found')
