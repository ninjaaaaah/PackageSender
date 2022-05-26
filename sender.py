import time
import requests
import socket
import argparse
import hashlib
import signal

PID = "95b59f86"
SENDER_PORT = 6716


def parseArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str,
                        help="File to send", default=f"{PID}.txt")
    parser.add_argument("-a", "--address", type=str,
                        help="Server IP address",  default="10.0.7.141")
    parser.add_argument("-s", "--receiver_port", type=int,
                        help="Port number used by the receiver", default=SENDER_PORT)
    parser.add_argument("-c", "--sender_port", type=int,
                        help="Port number used by the sender", default=9000)
    parser.add_argument("-i", "--id", type=str,
                        help="Unique Identifier", default=PID)
    args = parser.parse_args()
    print(args)
    return args


class Sender:
    def __init__(self, args) -> None:
        self.PID = PID
        self.SENDER_PORT = SENDER_PORT
        self.FILE_NAME = args.file
        self.SENDER_PORT_NO = args.sender_port
        self.RECEIVER_PORT_NO = args.receiver_port
        self.IP_ADDRESS = args.address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.RECEIVER_PORT_NO))

    # Downloading the payload
    def downloadPackage(self):
        URL = f"http://3.0.248.41:5000/get_data?student_id={self.PID}"
        response = requests.get(URL)
        open(self.FILE_NAME, "wb").write(response.content)

    # Sending an Intent Message
    def sendIntentMessage(self):
        intent = f"ID{self.PID}".encode()
        self.sock.sendto(intent, (self.IP_ADDRESS, self.SENDER_PORT_NO))
        data, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
        self.TID = data.decode()
        print(f"Transaction ID: {self.TID}")

    def sendPackage(self):
        data = open(f"{self.PID}.txt", "r").read()
        sent = 0
        size = 1
        rate = 0
        streak = 0

        while True:
            if sent == len(data):
                break

            seq = f"{sent}".zfill(7)
            isLast = 1 if sent + size == len(data) else 0

            packet = f"ID{self.PID}SN{seq}TXN{self.TID}LAST{isLast}{data[sent:sent+size]}"
            print(packet)

            self.sock.sendto(
                packet.encode(), (self.IP_ADDRESS, self.SENDER_PORT_NO))

            t0 = time.time()

            if rate != 0:
                self.sock.settimeout(rate+1)

            try:
                reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
            except:
                streak += 1
                if streak == 3:
                    size = int(size/2)
                    streak = 0
                continue

            t1 = time.time()
            if rate == 0:
                rate = t1-t0

            ack = reply.decode()

            if self.verifyAck(seq, ack, packet):
                sent += size
                size *= 2

    def verifyAck(self, seq, ack, packet):

        md5 = self.compute_checksum(packet)
        correct = f"ACK{seq}TXN{self.TID}MD5{md5}"

        print(ack == correct)

        if ack == correct:
            print(f"ACK {seq}")
            return True

        return False

    def compute_checksum(self, packet):
        return hashlib.md5(packet.encode('utf-8')).hexdigest()


args = parseArguments()
sender = Sender(args)
sender.downloadPackage()
sender.sendIntentMessage()
if sender.TID != "Existing alive transaction":
    sender.sendPackage()
