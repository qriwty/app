import zmq


class StreamReceiver:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        self.context = zmq.Context()
        self.socket = None

        self.connect()

    def connect(self):
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(f"tcp://{self.host}:{self.port}")
        except Exception as error:
            print(f"Failed to connect to the server: {error}")

    def request_data(self):
        try:
            self.socket.send_string("get_data")
        except Exception as error:
            print(f"Failed to send data request: {error}")

    def receive_data(self):
        try:
            data = self.socket.recv_json()
            return data
        except Exception as error:
            print(f"Failed to receive data: {error}")

    def get_data(self):
        self.request_data()

        return self.receive_data()

    def close(self):
        if self.socket:
            self.socket.close()
            print("Socket closed")
        if self.context:
            self.context.term()
            print("ZeroMQ context terminated")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
