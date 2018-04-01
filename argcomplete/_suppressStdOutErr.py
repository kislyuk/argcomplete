import os
import sys

_DEBUG = "_ARC_DEBUG" in os.environ

def main():
    pyScript = sys.argv[1]
    with open(pyScript) as f:
        # check if required marker is present
        head = f.read(1024)
        f.seek(0)
        if 'PYTHON_ARGCOMPLETE_OK' not in head:
            raise Exception('marker not found')
        else:
            # redirect stdout and stderr to devnull if we are not debugging
            if not _DEBUG:
                sys.stdout = open(os.devnull, 'w')
            sys.stderr = sys.stdout
            exec(f.read())

if __name__ == '__main__':
    main()
