

import ast
import inspect
from os import listdir

path = "./"
IMPORT_REGEX = r"^(from (\S*|\.)+ import (\S*|.)+|import (\S*|\.)+)$"


def is_import(txt: str) -> bool:
    try:
        tree = ast.parse(txt)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return True
    except SyntaxError:
        return False
    return False

def find_pypi_module(module: str) -> None:
    pass

def main() -> None:
    for i in listdir(path):
        # i is str, not moduleType
        if inspect.ismodule(i):
            with open(path + i) as f:
                for line in f:
                    if not is_import(line):
                        continue
                    # find module from pipy
                    find_pypi_module(line)
                    # add to list of "is this correct"
                    # add to requirements



if __name__ == "__main__":
    main()
