import pathlib
import sys
from pathlib import Path

import correction as cr

if __name__ == "__main__":
    args = sys.argv
    # args[0] = current file
    # args[1] = function name
    # args[2:] = function args : (*unpacked)

    settings = args[1]
    c = cr.Correction(settings)

    files = args[2:]
    p = pathlib.Path(files[0])
    p = p.parent.joinpath("output");
    p.mkdir(parents=True, exist_ok=True)
    for file_in_path in files:
        path_in_object = Path(file_in_path)
        file_out_name = path_in_object.stem + "_" + path_in_object.suffix
        path_out_object = Path(path_in_object.parent, "output")
        path_out_object = Path(path_out_object, file_out_name)
        print ("Converting " + str(path_in_object.resolve()) + " to " + str(path_out_object.resolve()) + "\n")
        c.parse_file(str(path_in_object.resolve()), str(path_out_object.resolve()))

