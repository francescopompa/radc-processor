import socket
import sys
import os
import time
import multiprocessing as mp




class Receiver():

    def __init__(self,
        target_file="testreadoutfile.bin",
        host="", port=50007,
        chunk_max_events=None, chunk_max_volume=None, chunk_max_time=None,
        split=False
        ) -> None:
        self.target_file = target_file
        self.host = host
        self.port = port

        # self.chunk_size_bytes = chunk_size
        self.chunk_max_events = chunk_max_events # Event number
        self.chunk_max_volume = chunk_max_volume # Bytes
        self.chunk_max_time = chunk_max_time # seconds
        self.current_chunk = 0
        self.chunk_suffix_length = 3
        self.__chunk_count_offset = 0
        self.__chunk_volume_offset = 0
        self.__chunk_time_offset = 0

        self.__do_split = split
        self.current_split = 1
        self.split_suffix_length = 4
        self.__split_size = 1420

        self.__do_readout = False
        self.__sock = None
        self.__data_queue = None
        self.__update_queue = None
        self.__p_writers = []   # Stores writer processes
        self.__p_readout = None # Stores readout process
        self.__p_update = None  # Stores output updating process

        self.results = {}

        if all([max is None for max in [self.chunk_max_events, self.chunk_max_volume, self.chunk_max_time]]):
            # raise ValueError(f"Need at least one chunk-size limit.")
            print("Warning: No Chunking set.")

        if self.__do_split is True:
            self.target_file = f"{self.target_file}.wfm.{self.current_split:0{self.split_suffix_length}}"

    def __del__(self):
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type,exc_value, exc_traceback):
        self.stop()

    def __getstate__(self):
        # SOURCE: https://stackoverflow.com/questions/62830911/typeerror-cannot-pickle-weakref-object
        # capture what is normally pickled
        state = self.__dict__.copy()

        # remove unpicklable/problematic variables
        state['_Receiver__p_writers'] = []
        state['_Receiver__p_readout'] = None
        state['_Receiver__p_update'] = None

        return state


    def start(self):
        # mp.set_start_method('spawn')

        self.__start_socket()

        self.__do_readout = True

        # pipe_rec, pipe_send = mp.Pipe(duplex=False)
        self.__data_queue = mp.Queue() # maxsize is 2147483647
        self.__update_queue = mp.Queue() # maxsize is 2147483647

        # p_readout = mp.Process(target=self._read_to_file)#, args=(pipe_send))
        self.__update = mp.Process(target=self.update_received_data)#, args=(pipe_rec))
        self.__update.start()

        self.__p_readout = self.__new_readout_process()

        # conn, addr = self.__sock.accept()
        # with conn:
        #     print("Connected by", addr)
        #     # self._read_to_file()
        #     # p_readout.start()
        #     p_readout = self.__new_readout_process()

        # self.stop()

    def stop(self):
        print(mp.active_children())
        self.__do_readout = False

        # if pipe_send is not None:
        #     pipe_send.close()
        for p in self.__readouts:
            # p.stop()
            p.join()

        if self.__queue is not None:
            self.__queue.close()

        if self.__sock is not None:
            self.__sock.shutdown(socket.SHUT_RD)
            self.__sock.close()

        while self.__update is not None and self.__update.is_alive():
            pass

        print(mp.active_children())
        return self.results


    def check_chunk_condition(self, count=0, total_data=0, run_time=0):

        if self.__do_split is True:
            self.__change_target_file(mode="split")
            return True

        chunk_count = (count - self.__chunk_count_offset)
        chunk_volume = (total_data - self.__chunk_volume_offset)
        chunk_time = (run_time - self.__chunk_time_offset)

        if (
            (self.chunk_max_events is not None and chunk_count >= self.chunk_max_events) or
            (self.chunk_max_volume is not None and chunk_volume >= self.chunk_max_volume) or
            (self.chunk_max_time is not None and chunk_time >= self.chunk_max_time)
            ):
            # End of a chunk
            self.__change_target_file(mode="chunk")

            self.__chunk_count_offset += chunk_count
            self.__chunk_volume_offset += chunk_volume
            self.__chunk_time_offset += chunk_time
            return True

        return False

    def __change_target_file(self, mode=None, new_target=None):
        old_readout = self.__readouts.pop(0) # first item -> oldest

        if mode == "split":
            self.current_split += 1
            new_target = f"{self.target_file}.wfm.{self.current_split:0{self.split_suffix_length}}"
        elif mode == "chunk":
            self.current_chunk += 1
            new_target = f"{self.target_file}.chunk.{self.current_chunk:0{self.chunk_suffix_length}}"
        elif new_target is not None:
            pass
        else:
            raise ValueError(f"Enter new target for {self.target_file}.")

        new_readout = self.__new_readout_process(filename=new_target)
        old_readout.stop()


    def __new_readout_process(self, target=None, **kwargs):
        if target is None:
            target = self._readout

        print("new readout process", kwargs)
        p = mp.Process(target=target, args=(kwargs))
        self.__readouts.append(p)
        p.start()
        print(mp.active_children())
        return p

    def __start_socket(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind((self.host, self.port))
        # self.__sock.listen()

        print(f"Started socket at {self.__sock.getsockname()} to {self.__sock.getpeername()}.")
        return self.__sock

    def _read_to_file(self, filename=None):
        if filename is None:
            filename = self.target_file

        with open(filename, "wb") as file:
            self.__readout(file)

    def __read_to_stdout(self):
        self.__readout(sys.stdout)


    # def __old_readout(self, buffer):

    #     while self.__do_readout is True:
    #         recv_data_volume = self.__sock.recv_into(buffer, self.__split_size)
    #         self.__queue.put(recv_data_volume, block=False)
    #     else:
    #         self.stop()

    def _readout(self):

        while self.__do_readout is True:
            data = self.__sock.recv(self.__split_size)
            self.__data_queue.put_nowait(data)
            self.__update_queue.put_nowait(len(data))
        else:
            self.stop()

    # def __readout_with_split(self):
    #     file_count = 0
    #     while self.__do_readout is True:
    #         filename = f"{self.target_file}.wfm.{file_count:0{self.split_suffix_length}}"
    #         with open(filename, "wb") as file:
    #             recv_data_volume = self.__sock.recv_into(file, self.__split_size)
    #             # pipe_send.send(recv_data_volume)
    #             self.__queue.put(recv_data_volume, block=False)
    #             file_count += 1
    #     else:
    #         self.stop()


    def update_received_data(self):
        count = 0
        total_data = 0
        start_time = time.time()

        while self.__do_readout is True or self.__queue.empty() is False:

            # recv_data_volume = pipe_rec.recv() # Blocks until reception
            recv_data_volume = self.__queue.get()

            count += 1
            total_data += recv_data_volume
            run_time = time.time() - start_time

            self.check_chunk_condition(count, total_data, run_time)

            total_rate = total_data / run_time

            print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate}B/s) Chunks: {self.current_chunk}, Splits:{self.current_split}",
                end="\r",
                # file=sys.stdout, # Necessary?
                flush = True
            )
        else:
            if self.__queue.empty() is True:
                self.results = {
                    "received_packages": count,
                    "received_bytes": total_data,
                    "reception_time": run_time,
                    "produced_chunks": self.current_chunk + 1,
                    "produced_splits": self.current_split * self.__do_split,
                    "default_target_file": self.target_file,
                    "used_splitting": self.__do_split,
                    "host": self.host,
                    "port": self.port,
                }
                self.__update.stop()
            else:
                self.update_received_data()







