import sys
import getopt
import collections
import PySimpleGUI

import communication


class TcpPingPongWindow():
    def __init__(self, port_number):
        multiline = PySimpleGUI.Multiline(key="-Multiline-",
                                          disabled=True,
                                          expand_x=True,
                                          expand_y=True)
        textbox = PySimpleGUI.Text(text=f"Communicating on port {port_number}:",
                                   expand_x=True)
        layout = [[textbox],
                  [multiline]]

        self._window = PySimpleGUI.Window(title="TCP Ping Pong",
                                         layout=layout,
                                         resizable=True)
        self._window.Finalize()
        self._window.set_min_size((400, 300))

        self._message_deque = collections.deque(maxlen=64)
        self._channel = communication.TcpPingPong(port_number=port_number,
                                                  message_deque=self._message_deque)

        try:
            while True:
                event, _ = self._window.Read(timeout=100)
                if event == PySimpleGUI.TIMEOUT_KEY:
                    while self._message_deque:
                        multiline.print(self._message_deque.pop())
                elif event == PySimpleGUI.WIN_CLOSED:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self._channel.shut_down()
            self._window.close()


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

    TcpPingPongWindow(port_number=port_number)
