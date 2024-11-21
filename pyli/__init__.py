#  Copyright (c) <2014> <thenoviceoof>
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

import logging
import sys
from pyli.main import main

__version__ = (2, 0, 1)

# Any sane person would use argparse; however, we want to accept
# arbitrary switches, so unfortunately argparse is not an option.

HELP_MSG = """
pyli is a utility to make using python in conjunction with other CLI tools easier
 - attempts to auto import unbound variables
 - populate special variables (lines, line, contents) with structured
   data from stdin
 - print the last line automatically (if not None)
 - provides command line options as variables (other than those listed
   below)

Special switches include:
 -v, -vv, --debug  Outputs debug information useful when developing pyli.
 --help            Outputs this message.
 -pp, --pprint     Uses pprint.pprint() instead of python's builtin print.
 --version         Outputs the current version of pyli.

Check out https://github.com/thenoviceoof/pyli for more details!
"""


# TODO: add a --debug-out switch to provide an alternative for debug
# info than stderr.
def script_entry_point():
    if len(sys.argv) == 1 or "--help" in sys.argv:
        print(HELP_MSG.format(sys.argv[0]))
    elif "--version" in sys.argv:
        version_string = ".".join(str(v) for v in __version__)
        print(version_string)
    else:
        args = sys.argv[1:]
        debug = logging.ERROR
        pprint = False
        # strip out any switches
        if "-v" in args:
            args.remove("-v")
            debug = logging.WARNING
        if "-vv" in args:
            args.remove("-vv")
            debug = logging.INFO
        if "--debug" in args:
            args.remove("--debug")
            debug = logging.DEBUG
        if "--pprint" in args:
            args.remove("--pprint")
            pprint = True
        if "-pp" in args:
            args.remove("-pp")
            pprint = True
        # pass everything else as a variable
        commands = []
        kwargs: dict[str, str | bool] = {}
        while args:
            if args[0][0] == "-":
                if "=" in args[0]:
                    name, val = args[0].split("=", 1)
                    name = name.lstrip("-")
                    kwargs[name] = val
                    args = args[1:]
                elif len(args) > 1 and args[1][0] != "-":
                    name, val = args[:2]
                    name = name.lstrip("-")
                    kwargs[name] = val
                    args = args[2:]
                else:
                    # treat as a boolean switch
                    name = args[0].strip("-")
                    kwargs[name] = True
                    args = args[1:]
            else:
                commands.append(args[0])
                args = args[1:]

        program = "\n".join(commands)
        main(program, debug=debug, pprint_opt=pprint, variables=kwargs)
