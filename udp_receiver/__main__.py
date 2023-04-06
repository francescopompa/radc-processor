

import sys
import time
from receiver_class import Receiver

#
# Todo:
# Lock __main__ in try/except to catch keyboard interrupt?
#
def print_usage():
    print("""Creates a Receiver-instance from command line arguments and
commands it from STDIN.

Usage:
    python udp_receiver [key=value | [N]]*

The command line arguments must be key=value pairs, with key being a
valid argument name of the Receiver()-class constructor.
If an argument is a single number N, it is interpreted as duration=N.

A command must end with a linebreak character (\\n).
The receiver can be commanded using the following commands:
    start [N]:  Receiver.start(duration=N)
                Starts readout for the receiver, indefinitely.
                N is optional and limits the readout time to N seconds.
    stop:       Receiver.stop()
                Stops readout for the receiver.
    catch:      Receiver.catch_board()
                Sends a dummy write to the board to set it's target port.
    help:       Print this help message.
    exit:       Closes receiver and exits Programm.
""")

def parse_stdin(line, rec):
    if line[0] == "start":
        rec.start(duration=int(line[1]) if len(line)==2 else None)
        print(line)
    elif line[0] == "stop":
        rec.stop()
        print(line)
    elif line[0] == "catch":
        rec.catch_board()
        print(line)
    elif line[0] == "exit":
        print(line)
        # automatically closes the Receiver (see __del__() and __exit__()).
        exit()
    elif line[0] in ["h", "-h", "help", "--help"]:
        print_usage()

def parse_arguments(args):
    argsdict = {}
    for arg in args:
        keyval = arg.split('=')
        if len(keyval) == 2:
            argsdict[keyval[0]] = int(keyval[1]) if keyval[1].isdigit() else keyval[1]
        elif keyval[0].isdigit():
            argsdict["duration"] = int(keyval[0])
        else:
            print_usage()

    print("Parsed args:", argsdict)
    return argsdict

def main(runtime=None):
    print_usage()
    # print(sys.argv)
    argsdict = parse_arguments(sys.argv)
    with Receiver(**argsdict) as rec:
        # print(rec.__dict__)
        while True:
            line = sys.stdin.readline().rstrip('\n').split(' ')
            parse_stdin(line, rec)



if __name__ == "__main__":
    main()