import os
import sys

from pkg_resources import iter_entry_points

from ._check_module import ArgcompleteMarkerNotFound, find


def main():
    # Argument is the full path to the console script.
    script_path = sys.argv[1]

    # Find the module and function names that correspond to this
    # assuming it as actually a console script.
    name = os.path.basename(script_path)
    entry_points = list(iter_entry_points('console_scripts', name))
    if not entry_points:
        raise ArgcompleteMarkerNotFound('no entry point found matching script')
    [entry_point] = entry_points
    module_name = entry_point.module_name
    function_name = entry_point.attrs[0]

    # Check this looks like the script we really expected.
    with open(script_path) as f:
        script = f.read()
    if 'from {} import {}'.format(module_name, function_name) not in script:
        raise ArgcompleteMarkerNotFound('does not appear to be a console script')
    if 'sys.exit({}())'.format(function_name) not in script:
        raise ArgcompleteMarkerNotFound('does not appear to be a console script')

    # Look for the argcomplete marker in the script it imports.
    with open(find(module_name, return_package=True)) as f:
        head = f.read(1024)
    if 'PYTHON_ARGCOMPLETE_OK' not in head:
        raise ArgcompleteMarkerNotFound('marker not found')


if __name__ == '__main__':
    try:
        main()
    except ArgcompleteMarkerNotFound as e:
        sys.exit(e)
