import sys
from slow_control import Control


def print_usage():
    print("""Create a slow_control instance from command line arguments and
commands it from STDIN.

Usage:
    python -m slow_control [key=value | [N]]*

For now the interactive mode is not implemented. 
To exit press CTRL-C.
""")

def parse_stdin(line, control):
    if line[0] == "switch":
        if len(line)==2:
            control.switch_file(filename=line[1])
        else:
            print("Missing name or path to new file. Ignoring.")
    elif line[0] == "exit":
        print(line)
        exit()
    elif line[0] in ["h", "-h", "help", "--help"]:
        print_usage()
    else:
        print("Unknown command given. Please retry. Print help with \"help\".")
    print(line)


def parse_arguments(args):
    argsdict = {}
    for arg in args:
        keyval = arg.split('=')
        if len(keyval) == 2:
            argsdict[keyval[0]] = int(keyval[1]) if keyval[1].isdigit() else keyval[1]
        elif keyval[0].isdigit():
            argsdict["duration"] = int(keyval[0])
        else:
            print(f"Wrong argument {arg} given.")
            print_usage()

    print("Parsed args:", argsdict)
    return argsdict



def main(argsdict=None):
    
    print_usage()
    # print(sys.argv)
    argsdict = argsdict or parse_arguments(sys.argv[1:])    # First argument is the script name
    with Control(**argsdict) as c:
        # print(rec.__dict__)
        while True:
            line = sys.stdin.readline().rstrip('\n').split(' ')
            parse_stdin(line, c)


if __name__ == "__main__":
    main()