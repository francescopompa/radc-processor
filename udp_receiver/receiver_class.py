import socket
import sys
import os
import time
import multiprocessing as mp
import signal

#
# Todo:
# - Migrate to threading and queue modules? (more lightweight and IO focused)
#

class Receiver():

    def __init__(self,
        target_file="testreadoutfile.bin",
        host="", port=50007,
        chunk_max_events=None, chunk_max_volume=None, chunk_max_time=None,
        overwrite=True,
        split=False,
        duration=None,
        ) -> None:
        self.target_file = target_file
        self.do_overwrite = overwrite
        self.host = host
        self.port = port
        self._duration = duration


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
        if self.__do_readout is True:
            self.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type,exc_value, exc_traceback):
        if self.__do_readout is True:
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

    def _signal_handler(self, signal, frame):
        print("")
        print("Catched Keyboard Interrupt")
        self.stop()


    def start(self, duration=None):
        self.__start(duration=duration)

        # signal.signal(signal.SIGINT, self._signal_handler)
        # forever = mp.Event()
        # forever.wait()

    def __start(self, duration=None):
        # mp.set_start_method('spawn')

        self.__start_socket()
        self.__do_readout = True

        self.__data_queue = mp.Queue() # maxsize is 2147483647
        self.__update_queue = mp.Queue() # maxsize is 2147483647

        self.__p_update = mp.Process(name="p_update", target=self._update_received_data)#, args=(pipe_rec))
        self.__p_update.start()

        self.__p_readout = mp.Process(name="p_readout", target=self._readout)
        self.__p_readout.start()

        self.__new_writer_process()


        duration = duration if duration is not None else self._duration if self._duration is not None else None
        if duration is not None:
            time.sleep(duration)
            print("Reached end of timer")
            print("Reached end of timer")
            print("Reached end of timer")
            self.stop()


    def stop(self):
        # print(mp.active_children())
        self.__do_readout = False

        while self.__data_queue.empty() is False or self.__update_queue.empty() is False:
            # print("Waiting for queues to be emptied...")
            time.sleep(1)

        if self.__sock is not None:
            # print("Shutting down socket")
            self.__sock.shutdown(socket.SHUT_RD)
            self.__sock.close()

        for p in mp.active_children():
            # print(f"Terminating {p}")
            p.terminate()
            p.join()

        if self.__update_queue is not None:
            # print("Closing update queue")
            self.__update_queue.close()
        if self.__data_queue is not None:
            # print("Closing data queue")
            self.__data_queue.close()

        if len(mp.active_children()) > 0:
            print(mp.active_children())
        else:
            print("Receiver: Subprocesses, queues and sockets closed succesfullly.")

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
        old_writer = self.__p_writers.pop(0) # first item -> oldest

        if mode == "split":
            self.current_split += 1
            new_target = f"{self.target_file}.wfm.{self.current_split:0{self.split_suffix_length}}"
        elif mode == "chunk":
            self.current_chunk += 1
            new_target = f"{self.target_file}.chunk.{self.current_chunk:0{self.chunk_suffix_length}}"
        elif mode == "overwrite":
            old_target = new_target
            target_folder = os.path.dirname(os.path.abspath(old_target))
            suffixes = []
            with os.scandir(target_folder) as sd:
                for entry in sd:
                    if entry.startswith(old_target) and entry.is_file():
                        try:
                            suffixes.append(int(entry.split('.')[-1]))
                        except:
                            continue
            if max(suffixes) > 0:
                new_target = f"old_target.{max(suffixes)}"
            else:
                new_target = "old_target.1"

        elif new_target is not None:
            pass
        else:
            raise ValueError(f"Enter new target for {self.target_file}.")

        old_writer.stop()
        self.__new_writer_process(filename=new_target)

        return new_target


    def __new_writer_process(self, target=None, **kwargs):
        if target is None:
            target = self._write_to_file

        print("new readout process", kwargs)
        p = mp.Process(name=f"p_writer_{len(self.__p_writers    )}",target=target, args=(kwargs))
        self.__p_writers.append(p)
        p.start()
        print(mp.active_children())
        return p

    def __start_socket(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind((self.host, self.port))
        # self.__sock.listen()

        # print(f"Started socket at {self.__sock.getsockname()} to {self.__sock.getpeername()}.")
        print(f"Started UDP socket at {self.__sock.getsockname()}.")
        return self.__sock

    def _write_to_file(self, filename=None):
        if filename is None:
            filename = self.target_file

        if self.do_overwrite is False and  os.exists(filename):
            filename = self.__change_target_file(mode="overwrite", new_target=filename)

        with open(filename, "wb") as file:
            while self.__do_readout is True or self.__data_queue.empty() is False:
                file.write(self.__data_queue.get())

    def __read_to_stdout(self):
        self.__readout(sys.stdout)

    def _readout(self):
        while self.__do_readout is True:
            data = self.__sock.recv(self.__split_size)
            self.__data_queue.put_nowait(data)
            self.__update_queue.put_nowait(len(data))
        # else:
        #     self.stop()


    def _update_received_data(self):
        count = 0
        total_data = 0
        start_time = time.time()

        print(f"Waiting for packages.")

        while self.__do_readout is True or self.__update_queue.empty() is False:

            # recv_data_volume = pipe_rec.recv() # Blocks until reception
            recv_data_volume = self.__update_queue.get()

            count += 1
            total_data += recv_data_volume
            run_time = time.time() - start_time

            self.check_chunk_condition(count, total_data, run_time)

            total_rate = total_data / run_time

            print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate:.2}B/s) Chunks: {self.current_chunk}, Splits:{self.current_split}",
                end="\r",
                # file=sys.stdout, # Necessary?
                flush = True
            )
        else:
            if self.__update_queue.empty() is True:
                print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate:.2}B/s) Chunks: {self.current_chunk}, Splits:{self.current_split-1}")
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
                self.__p_update.stop()
            else:
                self.update_received_data()







