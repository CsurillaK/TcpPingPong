import socket
import traceback
import threading
import collections
import struct
import time
import datetime
import random
import typing
import getopt
import sys


def _format_exception(exception: Exception) -> list[str]:
    return traceback.format_exception(type(exception),
                                      exception,
                                      exception.__traceback__)

def _verify_message_deque(message_deque: typing.Optional[collections.deque]):
    if message_deque is not None:
        message_deque.append(None)
        _ = message_deque.pop()

def _handle_message(message: str, message_deque: typing.Optional[collections.deque] = None):
    message = f"{datetime.datetime.now().strftime('[%H:%M:%S]')} {message}"
    if message_deque is None:
        print(message)
    else:
        try:
            message_deque.appendleft(message)
        except:
            pass

class Context(typing.NamedTuple):
    shut_down_flag: threading.Event
    address: tuple[str, int]
    timeout: float
    message_deque: typing.Optional[collections.deque]

class TcpPingPong():
    LOCALHOST = "127.0.0.1"
    TIMEOUT = 0.5

    def __init__(self, port_number: int, message_deque: typing.Optional[collections.deque] = None):
        _verify_message_deque(message_deque)

        self._shut_down_flag = threading.Event()
        # context = collections.namedtuple("Context", ["shut_down_flag", "address", "timeout", "message_deque"])
        self._worker = threading.Thread(target=TcpPingPong._handle_communication,
                                        args=(Context(shut_down_flag=self._shut_down_flag,
                                                      address=(self.LOCALHOST, port_number),
                                                      timeout=self.TIMEOUT,
                                                      message_deque=message_deque),))

        self._worker.start()

    def shut_down(self):
        self._shut_down_flag.set()
        self._worker.join()

    def __del__(self):
        self.shut_down()

    @staticmethod
    def _handle_communication(context: Context):
        while not context.shut_down_flag.is_set():
            socket_ = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            socket_.settimeout(context.timeout)
            try:
                is_server = False
                try:
                    socket_.bind(context.address)
                    is_server = True
                except OSError as exception:
                    pass # port has already been bound

                if is_server:
                    TcpPingPong._act_as_server(socket_, context)
                else:
                    TcpPingPong._act_as_client(socket_, context)
            except Exception as exception:
                print("Uncaught exception occurred:")
                for line in _format_exception(exception):
                    print(line)
                break
            finally:
                try:
                    socket_.shutdown(socket.SHUT_RDWR)
                    socket_.close()
                except:
                    pass

    @staticmethod
    def _act_as_server(socket_: socket.socket, context: Context):
        socket_.listen(1)
        while not context.shut_down_flag.is_set():
            # Accept loop
            while True:
                if context.shut_down_flag.is_set():
                    return
                try:
                    connection_socket, _ = socket_.accept()
                    break
                except socket.timeout:
                    pass

            # Connection is established
            connection_socket.settimeout(context.timeout)
            try:
                while True:
                    # Recv loop
                    data = None
                    while True:
                        if context.shut_down_flag.is_set():
                            return
                        try:
                            data = connection_socket.recv(4)
                            break
                        except socket.timeout:
                            pass

                    if len(data) != 4:
                        raise ConnectionError() # peer was likely not closed gracefully

                    data = struct.unpack("!i", data)[0]
                    _handle_message(f"Received value {data}.", context.message_deque)

                    time.sleep(random.random()*2)

                    if context.shut_down_flag.is_set():
                        return

                    #Send
                    data += 1
                    connection_socket.send(struct.pack("!i", data))

            except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
                # recv() and send() fails on closed peer socket
                continue # start over from accept()
            finally:
                connection_socket.shutdown(socket.SHUT_RDWR)
                connection_socket.close()

    @staticmethod
    def _act_as_client(socket_: socket.socket, context: Context):
        try:
            # Connect
            socket_.connect(context.address)

            # Do an initial kick-off send
            socket_.send(struct.pack("!i", 0))

            # Message loop
            while True:
                # Recv loop
                data = None
                while True:
                    if context.shut_down_flag.is_set():
                        return
                    try:
                        data = socket_.recv(4)
                        break
                    except socket.timeout:
                        pass

                if len(data) != 4:
                    raise ConnectionError() # peer was likely not closed gracefully

                data = struct.unpack("!i", data)[0]
                _handle_message(f"Received value {data}.", context.message_deque)

                time.sleep(random.random()*2)

                if context.shut_down_flag.is_set():
                    return

                # Send
                data += 1
                socket_.send(struct.pack("!i", data))

        except socket.timeout:
            return # connect() times out, port is in bad shape
        except ConnectionRefusedError:
            # connect() fails on port not bound
            return # start over from bind(), maybe server was shut down, or there are more than two applications running
        except (ConnectionError, ConnectionResetError, ConnectionAbortedError):
            # recv() and send() fails on closed client socket
            return #start over from bind(), maybe server was shut down
        # finally:
        #     socket_.close() # client socket is closed in outer loop

if __name__ == "__main__":
    port_number = 5555

    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:", ["Port="])
    except getopt.GetoptError:
        print("graphics.py [--Port 5555]")
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-p", "--Port"):
            try:
                port_number = int(arg)
            except ValueError:
                print(f"Port argument must be an integer instead of '{arg}'.")
                sys.exit(2)

    o = TcpPingPong(port_number=port_number)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        o.shut_down()