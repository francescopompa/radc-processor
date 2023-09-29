from import_helper import *


def hold(message=""):
    if message != "" and not message.endswith(" "):
        message += " "
    uinput = input(f"{message}Press [ENTER] to continue.")
    if uinput in ["\n", ""]:
        return uinput
    else:
        hold(message)