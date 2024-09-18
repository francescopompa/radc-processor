


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
    start [duration]:   Receiver.start(duration=None)
                Starts readout for the receiver, indefinitely.
                If duration is given, it limits the readout time to
                `duration` seconds.
    stop:       Receiver.stop()
                Stops readout for the receiver.
    catch:      Receiver.catch_board()
                Sends a dummy write to the board to set it's target port.
    switch file:    Receiver.switch_file(file)
                Closes the current file and starts writing to file instead.
                file must be provided!
    trigger [number]:   Receiver.trigger(number=1)
                Release `number` software-trigger signals to receive the
                current (noise) waveforms without pulse detection.
    help:       Print this help message.
    exit:       Closes receiver and exits Programm.
""")

def parse_stdin(line, rec):
    if line[0] == "start":
        rec.start(duration=int(line[1]) if len(line)==2 else None)
    elif line[0] == "stop":
        rec.stop()
    elif line[0] == "catch":
        rec.catch_board()
    elif line[0] == "switch":
        if len(line)==2:
            rec.switch_file(filename=line[1])
        else:
            print("Missing name or path to new file. Ignoring.")
    elif line[0] == "status":
        print(rec.state())
    elif line[0] == "trigger":
        number = int(line[1]) if len(line) > 1 else 1
        print(rec.trigger(number=number))
    elif line[0] == "exit":
        print(line)
        # automatically closes the Receiver (see __del__() and __exit__()).
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
    import sys
    from udp_receiver.receiver_class import Receiver

    print_usage()
    # print(sys.argv)
    argsdict = argsdict or parse_arguments(sys.argv[1:])    # First argument is the script name
    with Receiver(**argsdict) as rec:
        if argsdict.pop('start') == 'True':
            rec.start(argsdict.get('duration',None))
        # print(rec.__dict__)
        while True:
            line = sys.stdin.readline().rstrip('\n').split(' ')
            parse_stdin(line, rec)


if __name__ == "__main__":
    main()