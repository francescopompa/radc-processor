import socket
import sys
import time

# Do Arguments

def readout(s, buffer):
    count = 0
    total_data = 0
    start_time = time.time()

    while True:
        recv_data_volume = s.recv_into(buffer, 1400)
        # data = s.recv(1400)
        # print(data)
        # file.write(data)

        count += 1
        total_data += recv_data_volume
        run_time = time.time() - start_time
        total_rate = total_data / run_time

        print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate}B/s)",
            end="\r",
            # file=sys.stdout, # Necessary`?`
            flush = True
        )

        # Exit condition -> Subprocess?

def read_to_file(s):
    with open("testreadoutfile.bin", "wb") as file:
        readout(s, file)

def read_to_stdout(s):
    readout(s, sys.stdout)



def manage_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # print(socket.__dir__())
    host = ""
    port = 50007

    s.bind((host, port))
    s.listen()
    conn, addr = s.accept()
    with conn:
        print("Connected by", addr)
        read_to_file(s)

    s.shutdown(socket.SHUT_RD)
    s.close()


if __name__ == "__main__":
    manage_socket()
