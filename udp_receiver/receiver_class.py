import socket
import sys
import os
import time
import threading as thr
import queue
import signal
import json

RADC_HEADER_SIZE=16
RADC_PKG_HEADER_SIZE=4

#
# Todo: Move logging from print to logger/stderr or to sys.stdout.write()?
# Todo: Implement sanity check every X packages (completeness of data, shape of data)
# Todo: Set target file at each measurement start, requiring no exit between takes.
# Todo: Increment file-number correctly when avoiding overwriting
#

class Receiver():

    def __init__(self,
        host="192.168.1.200",
        port=4000,
        target_root="C:/Users/utrfh/WS22-23 (MA) Masterarbeit/RADC_testData",
        target_dir=time.strftime("%Y-%m-%d"),
        target_file=f"{time.strftime('%Y-%m-%d_%H-%M-%S')}_readout.bin",
        chunk_max_events=None, chunk_max_volume=None, chunk_max_time=None,
        overwrite=False,
        split=False,
        duration=None,
        timeout=5,
        tracelength=700,
        keep_alive_time=300, # 5 min
        ) -> None:

        self.target_dir = os.path.join(target_root, target_dir)
        self.target_file = target_file + "" if target_file.endswith(".bin") else "_readout.bin"
        self.do_overwrite = overwrite
        self.host = host    # IP-Adress of the DQ Board
        self.port = port    # Target port through which the board sends data.
                            # Must be identical to the content of register "UdpPort"
        self._duration = duration
        self._keep_alive_time = keep_alive_time # Length of the shortest timeout
                                                # involved in the network connection

        self.files_written = []
        self.__suffixes = [0]

        self.chunk_max_events = chunk_max_events # Event number
        self.chunk_max_volume = chunk_max_volume # Bytes
        self.chunk_max_time = chunk_max_time # seconds
        self.current_chunk = 0
        self.chunk_suffix_length = 3
        self.__chunk_count_offset = 0
        self.__chunk_volume_offset = 0
        self.__chunk_time_offset = 0

        self.__do_split = split
        self.current_split = 0
        self.split_suffix_length = 4
        self.__split_size = 2*tracelength + RADC_HEADER_SIZE + RADC_PKG_HEADER_SIZE

        self.__do_readout = False
        self.__sock = None
        self.__data_queue = None
        self.__update_queue = None
        self.__t_writers = []   # Stores writer threads
        self.__t_readout = None # Stores readout thread
        self.__t_update = None  # Stores output updating thread
        self.__t_keep_alive = None # Stores keep-alive thread

        self.results = {}

        socket.setdefaulttimeout(timeout)

        if all([max is None for max in [self.chunk_max_events, self.chunk_max_volume, self.chunk_max_time]]):
            print("Warning: No Chunking set.")

        # if self.__do_split is True:
        #     self.target_file = f"{self.target_file}.wfm.{self.current_split:0{self.split_suffix_length}}"


    def __del__(self):
        if self.__do_readout is True:
            self.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.__do_readout is True:
            self.stop()

    def __getstate__(self):
        """Shadowed method to prepare state for pickling."""
        # SOURCE: https://stackoverflow.com/questions/62830911/typeerror-cannot-pickle-weakref-object
        # capture what is normally pickled
        state = self.__dict__.copy()

        # remove unpicklable/problematic variables (thread objects)
        state['_Receiver__t_writers'] = []
        state['_Receiver__t_readout'] = None
        state['_Receiver__t_update'] = None
        state['_Receiver__t_keep_alive'] = None

        return state


    def __signal_handler(self, signal, frame):
        """Shadowed method to catch keyboard interrupt signal."""
        print("")
        print("Receiver caught Keyboard Interrupt: stopping...")
        self.stop()

    def start(self, duration=None):
        """Start routine of the receiver instance.
        Opens a socket using (host, port) parameters and starts threads
        listening to the socket, writing the received data to file and
        printing the received data volume.
        Can be interrupted with .stop(), SIGINT (CTRL+C), deleting the
        instance object, or by leaving a context manager.
        If you pass a duration, the receiver will .stop() itself after
        `duration` seconds have passed.
        """
        if self.__do_readout is True:
            print("Receiver is already running.")
            return

        duration = (duration if duration is not None else
                    self._duration if self._duration is not None else
                    None)
        print(f"Starting receiver{' for {} seconds'.format(duration) if duration is not None else ''}.")

        signal.signal(signal.SIGINT, self.__signal_handler)

        self.__do_readout = True
        self.__start_socket()

        self.__data_queue = queue.Queue() # maxsize is 2147483647
        self.__update_queue = queue.Queue() # maxsize is 2147483647

        recv_event = thr.Event()
        self.__t_keep_alive = thr.Thread(
            name="t_keep_alive",
            target=self._keep_alive,
            kwargs=({"recv_event": recv_event})
            )
        self.__t_keep_alive.start()

        self.__t_update = thr.Thread(name="t_update", target=self._update_received_data)#, args=(pipe_rec))
        self.__t_update.start()

        self.__t_readout = thr.Thread(
            name="t_readout",
            target=self._readout,
            kwargs=({"recv_event": recv_event})
            )
        self.__t_readout.start()

        self.__new_writer_thread() # filename=filename)

        if duration is not None:
            time.sleep(duration)
            print("Reached end of timer")
            self.stop()


    def stop(self):
        """Shutdown routine of the reveicer instance.
        Closes all threads, queues and sockets.
        """
        #
        # Alternative idea: Use this function to send a last package to the
        #   readout and queues in order to avoid try/excepts, timeouts and nesting...
        # socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto("".encode(), ("localhost", self.port))
        # (Commit seppuku)
        #

        if self.__do_readout is False:
            print("Receiver has already stopped, or was never started.")
            return self.results

        print(thr.enumerate())
        self.__do_readout = False

        if self.__data_queue is not None:
            # print("Closing data queue")
            self.__data_queue.join()
        if self.__update_queue is not None:
            # print("Closing update queue")
            self.__update_queue.join()

        for t in thr.enumerate():
            if t.name in ["MainThread", "QueueFeederThread"]:
                continue
            # print(f"Terminating {t}")
            t.join()

        if self.__sock is not None:
            # print("Shutting down socket")
            self.__sock.shutdown(socket.SHUT_RD)
            self.__sock.close()

        thr_list =[t for t in thr.enumerate() if t != thr.main_thread()]
        if len(thr_list) > 0:
            print(thr.enumerate())
        else:
            print("Receiver: threads, queues and sockets all closed succesfullly.")

        return self.results

    def dump_results(self):
        filename = os.path.join(self.target_dir, self.target_file.replace("_readout.bin", "_results.json"))

        if self.do_overwrite is False and  os.path.exists(filename):
            filename = self.__do_not_overwrite_file(old_target=filename)

        with open(filename, 'a', encoding="utf-8") as file:
            json.dump(self.results, file, indent=4)
        print(f"Dumped results to {filename}")


    def __start_socket(self):
        """Shadowed function to create a new UDP socket bound to the
        given host and port."""
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(("", 0))
        self.__sock.connect((self.host, self.port))

        self.catch_board()

        print(f"Started UDP socket at {self.__sock.getsockname()} listening to {self.__sock.getpeername()}.")
        return self.__sock

    def state(self):
        return self.results, self.__dict__

    def catch_board(self):
        """Dummy write to the RADC board to inform it of the target laptop-port
        to send data to.
        """
        if self.__do_readout is True:
            self.__sock.send('W_00000001 00000000\r'.encode())
        else:
            print("Skipped catch command: socket is currently closed. Please start receiver first.")

    def switch_file(self, filename):
        if not os.path.isabs(filename):
            filename = os.path.join(self.target_dir, filename)
        self.__switch_target_file(new_target=filename)

    def _keep_alive(self, recv_event=thr.Event()):
        """The task for the keep-alive thread.
        It ensures that timeouts some OSes or devices may have, are not
        triggered.
        If no data was received after 0.8*_keep_alive_time seconds,
        it repeats the dummy write.
        This is handled by the recv_event set by the _readout() thread.
        """
        if self._keep_alive_time is None:
            return
        else:
            timeout=self._keep_alive_time * 0.8
            last_time = time.time()

        while self.__do_readout is True:
            if recv_event.wait(timeout=socket.getdefaulttimeout()):
                # Using the _keep_alive_time as timeout causes the thread
                # to idle that long on close, which is annoying.
                recv_event.clear()  # Acknowledge that data was received.
                last_time = time.time()
            else:
                if time.time() - last_time > timeout:
                    print(f"Keep-Alive detected no data the in last {timeout} seconds.")
                    self.catch_board()
                    last_time = time.time()


    def _readout(self, recv_event=thr.Event()):
        """The task function for the readout-thread.
        It appends received datagrams to the data queue, and appends
        their length to the update queue."""

        while self.__do_readout is True:
            try:
                data = self.__sock.recv(self.__split_size)
                if len(data) > 0:
                    self.__data_queue.put_nowait(data)
                    self.__update_queue.put_nowait(len(data))
                    recv_event.set()    # Signal that data was received.
            except TimeoutError:
                pass
        else:
            print("Stopped readout")

    def __new_writer_thread(self, target=None, **kwargs):
        """Shadowed function to create a new thread writing to a file."""
        if target is None:
            target = self._write_to_file

        print("new writer thread", kwargs)
        stop_event = thr.Event()
        kwargs["stop_event"] = stop_event
        t = thr.Thread(name=f"p_writer_{len(self.__t_writers)}",target=target, kwargs=kwargs)
        self.__t_writers.append((t, stop_event))
        t.start()
        # print(thr.enumerate())
        return t

    def _write_to_file(self, filename=None, stop_event=thr.Event()):
        """The task function for the writer-threads.
        It gets binary data from the data queue and writes it to the
        current target file.
        If the stop_event is set, the function closes the file.
        When a file gets closed it's name is appended to .files_written."""
        if filename is None:
            filename = os.path.join(self.target_dir, self.target_file)

        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

        if self.do_overwrite is False and  os.path.exists(filename):
            filename = self.__do_not_overwrite_file(old_target=filename)

        timeout = socket.getdefaulttimeout()

        with open(filename, "wb") as file:
            while self.__do_readout is True or self.__data_queue.empty() is False:
                if stop_event.is_set():
                    break
                try:
                    file.write(self.__data_queue.get(block=True, timeout=timeout))
                    self.__data_queue.task_done()
                except queue.Empty:
                    pass

        # if os.path.getsize(filename) > 0:
        self.files_written.append(filename)
        print(f"Writer has closed {filename}")
        # else:
        #     os.remove(filename)
        #     print(f"Writer has not written to {filename}: no data to write.")

    # def _write_to_stdout(self):
        # self.__readout(sys.stdout)
        # pass

    def _update_received_data(self,
        count = 0,
        total_data = 0,
        start_time = time.time(),
        ):
        """The task function for the update-thread.
        It gets the byte-length from the update queue and uses that to
        update the counters and print the received data volume."""

        run_time = 0
        total_rate = 0.
        timeout = socket.getdefaulttimeout()
        print(f"Waiting for packages...")

        while self.__do_readout is True or self.__update_queue.empty() is False:
            try:
                recv_data_volume = self.__update_queue.get(block=True, timeout=timeout)

                count += 1
                total_data += recv_data_volume
                run_time = time.time() - start_time

                self._check_chunk_condition(count, total_data, run_time)

                total_rate = total_data / run_time

                print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate:.2}B/s) Chunks: {self.current_chunk}, Splits:{self.current_split}",
                    end="\r",
                    # file=sys.stdout, # Necessary?
                    flush = True
                )
                self.__update_queue.task_done()
            except queue.Empty:
                pass
        # else:
        if self.__update_queue.empty() is True:
            print("Summary:")
            print(f"Received: {count} packages in {int(run_time)}s for {total_data} Bytes in total. ({total_rate:.2}B/s) Chunks: {self.current_chunk}, Splits:{self.current_split}")
            self.results = {
                "received_packages": count,
                "received_bytes": total_data,
                "reception_time": run_time,
                "duration": self._duration,

                "host": self.host,
                "port": self.port,
                "receiving_socket": self.__sock.getsockname(),
                "timeout": socket.getdefaulttimeout(),

                "default_target_file": self.target_file,
                "target_dir": self.target_dir,
                "used_splitting": self.__do_split,
                "produced_chunks": self.current_chunk + 1,
                "produced_splits": self.current_split * self.__do_split,
                "files_written": self.files_written,
                # "class_params": self.__dict__(),
            }
            self.dump_results()
        else:
            self._update_received_data(count=count, total_data=total_data, start_time=start_time)


    def _check_chunk_condition(self, count=0, total_data=0, run_time=0):
        """Function called by the update thread to check if a new chunk
        is needed (switching file) to minimize data loss in case of
        forceful interruption and easying the backup process."""

        if self.__do_split is True:
            self.__switch_target_file(mode="split")
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
            self.__switch_target_file(mode="chunk")

            self.__chunk_count_offset += chunk_count
            self.__chunk_volume_offset += chunk_volume
            self.__chunk_time_offset += chunk_time
            return True

        return False

    def __switch_target_file(self, mode=None, new_target=None):
        """Shadowed function to switch to a new file and start a
        corresponding writer-thread.
        Mode `split` appends the suffix `.wfm.<count>` to the filename.
        Mode `chunk` appends the suffix `.chunk.<count>` to the filename.
        Mode `overwrite` appends the suffix `.<count>` to the filename."""
        old_writer, stop_event = self.__t_writers.pop(0) # first item -> oldest

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

        stop_event.set()
        old_writer.join()
        self.__new_writer_thread(filename=new_target)

        return new_target

    def __do_not_overwrite_file(self, old_target):
        # "overwrite" is called by a writer-thread which cannot join() itself.
        target_folder = os.path.dirname(os.path.abspath(old_target))
        suffixes = self.__suffixes
        with os.scandir(target_folder) as sd:
            for entry in sd:
                if entry.path.startswith(old_target) and entry.is_file():
                    try:
                        suffixes.append(int(entry.split('.')[-1]))
                    except:
                        continue
        if max(suffixes) > 0:
            new_suffix = max(suffixes)+1
            suffixes.append(new_suffix)
            new_target = f"{old_target}.{new_suffix}"
            self.__suffixes = suffixes
        else:
            new_target = f"{old_target}.1"
        print(f"Replaced {old_target} with {new_target} to avoid overwrite. ({self.__suffixes})")
        return new_target







