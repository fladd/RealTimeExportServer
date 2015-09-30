"""Real-time export server.

A simple TCP server to which a single client can connect to in order to export
real-time pixel data from a Siemens MR scanner.

"""

__author__ = 'Florian Krause <krause@brainvoyager.com>'
__version__ = '0.1.0'
__date__ = '2015-10-28'


import socket
import errno
import sys
if sys.platform == 'win32':
    from time import clock as time
else:
    from time import time as time


class TcpServer:
    """A class implementing a TCP network server for a single client."""

    def __init__(self, port, default_package_size=1024, start_listening=True):
        """Create a TcpServer.

        Parameters:
        -----------
        port : int
            The port to connect to.
        default_package_size : int
            The default size of the packages to be received.
        start_listening : bool
            If True, start listening on port immediately.

        """

        self._port = port
        self._default_package_size = default_package_size
        self._socket = None
        self._is_connected = False
        if start_listening:
            self.listen()

    _getter_exception_message = "Cannot set {0} if connected!"

    @property
    def port(self):
        """Getter for port."""

        return self._port

    @port.setter
    def port(self, value):
        """Setter for port."""

        if self._is_connected:
            raise AttributeError(
                TcpServer._getter_exception_message.format("port"))
        else:
            self._port = value

    @property
    def default_package_size(self):
        """Getter for default_package_size."""

        return self._default_package_size

    @default_package_size.setter
    def default_package_size(self, value):
        """Setter for default_package_size."""

        if self._is_connected:
            raise AttributeError(
                TcpServer._getter_exception_message.format(
                    "default_package_size"))
        else:
            self._default_package_size = value

    @property
    def is_connected(self):
        """Getter for is_connected."""

        return self._is_connected

    def listen(self):
        """Listen for a connection on port."""

        if not self._is_connected:
            if True:
                self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._socket.bind(('', self._port))
                self._socket.listen(1)
                print "Listening on port {0}...".format(self._port)
                self._client = self._socket.accept()
                print "...{0} connected!".format(self._client[1])
                self._is_connected = True
            else:# socket.error:
                raise RuntimeError(
                    "Listening on port {0} failed!".format(self._port))

    def send(self, data):
        """Send data.

        Parameters:
        -----------
        data : str
            The data to be sent.

        """

        self._socket.sendall(data)

    def wait(self, n_bytes, package_size=None, duration=None):
        """Wait for data.

        Will read packages of data with size package_size until data is read.
        If neccessary, last package will be smaller than package_size.

        Parameters:
        -----------
        n_bytes : int
            Number of bytes to wait for.
        package_size : int, optional
            The size of the package to be received, optional.
            If not set, the default package size will be used.
            If n_bytes < package_size, package_size = n_bytes
        duration: int, optional
            The duration to wait in milliseconds.

        Returns:
        --------
        data : str
            The received data.
        rt : int
            The time it took to receive the data in milliseconds.

        """

        start = time()
        data = None
        rt = None

        if package_size is None:
            package_size = self._default_package_size
        if n_bytes < package_size:
            package_size = n_bytes
        while True:
            try:
                if data is None:
                    data = self._client[0].recv(package_size)
                while len(data) < n_bytes:
                    if n_bytes - len(data) >= package_size:
                        data = data + self._client[0].recv(package_size)
                    else:
                        data = data + self._client[0].recv(n_bytes - len(data))
                    if duration:
                        if int((time() - start) * 1000) >= duration:
                            data = None
                            rt = None
                            break
                rt = int((time() - start) * 1000)
                break
            except socket.error, e:
                pass

            if duration:
                if int((time() - start) * 1000) >= duration:
                    data = None
                    rt = None
                    break

        return data, rt


    def clear(self):
        """Read the stream empty."""

        try:
            self._socket.recv(1024000000000)
        except:
            pass

    def close(self):
        """Close the connection to the server."""

        if self._is_connected:
            self._client[0].close()
            self._client = None
            self._is_connected = False


if __name__ == "__main__":

    import struct


    s = TcpServer(667)

    header_number = 0
    data_number = 1
    while True:
        header_size = struct.unpack('<I', s.wait(4)[0])[0]
        print header_number, "Header size", header_size, "bytes"
        data_size =  struct.unpack('<I', s.wait(4)[0])[0]
        print data_number, "Data size", data_size, "bytes"
        if header_size > 0:
            header = s.wait(header_size)
            print header_number, "Header", "read in", header[1], "ms"
            header_number += 1
            if data_size == 0:
                # Big header --> create file
                start = header[0].find('ParamLong."MeasUID"')
                if start == -1:
                    mid = "NoMID"
                else:
                    end = header[0].find('\n', start)
                    mid = "".join([x for x in header[0][start:end] if x.isdigit()])
                start = header[0].find('"tProtocolName"')
                if start == -1:
                    prt = "NoProtocolName"
                else:
                    end = header[0].find('\n', start)
                    prt = header[0][start+len('"tProtocolName"')+1:end].strip(' {}"')
                f = open("meas_MID{0}_{1}.dat".format(mid, prt), 'w')
                f.write(header[0])
                f.write("\n")
            else:
                data = s.wait(data_size)
                print data_number, "Data", "read in", data[1], "ms"
                data_number += 1
                try:
                    # Write data to file
                    f.write(data[0])
                    f.write("\n")
                except:
                    raise IOError("Data could not be written!")
        elif header_size == 0 & data_size == 0:
            # Send back zeroes and close connection
            print "Sending closing confirmation..."
            try:
                s.send(struct.pack('<I', header_size))
                s.send(struct.pack('<I', data_size))
            except socket.error, e:
                print e
            s.close()
            f.close()
            print "Connection closed!"
            break
