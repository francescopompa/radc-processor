import multiprocessing as mp
from multiprocessing import Process
import subprocess
import os
import time

def info(title):
    print("")
    print(title)
    print("module name:", __name__)
    print("parent process:", os.getppid())
    print("process id:", os.getpid())

def f(name):
    info("function f")
    print("hello", name)
    while True:
        time.sleep(5)
        print("I'm alive")

def sub():
    info("function sub")
    command = "PowerShell".split(' ')
    command = "PowerShell Start-Process python".split(' ')
    command = "python".split(' ')

    subprocess.run(command)

    while True:
        time.sleep(5)
        print("I'm Alive    ")



if __name__ == "__main__":
    mp.set_start_method('spawn')
    info("main line")

    # This creates multiple new processes:
    # - The function
    # - The subprocess-PowerShell instance
    # - Whatever the new PowerShell does (e.g. start a new window)
    # p = Process(target=f, args=('bob',))
    # p = Process(target=sub)
    # p.start()
    # p.join()

    # This creates less new processes:
    # - The subprocess instance
    # - Whatever the subprocess starts
    sub()
