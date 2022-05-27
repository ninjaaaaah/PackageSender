import math
import time
import requests
import socket
import argparse
import hashlib

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
    return args


class colors:
    ACK = '\033[92m'
    NON = '\033[93m'
    ERR = '\033[91m'
    END = '\033[0m'


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

    def sendPackage(self):
        data = open(f"{self.PID}.txt", "r").read()
        sent = 0
        initsize = 1
        size = initsize
        rate = 0
        seq = 0
        last = 0
        optimal = 0
        elapsed = 0
        cons = 0
        prev = None

        print(f"Transaction ID: {self.TID} | DATA: {len(data)}")

        self.sock.settimeout(15)
        while True:
            if sent >= len(data):
                break

            if size == 0:
                break

            seqID = f"{seq}".zfill(7)
            isLast = 1 if sent + size >= len(data) else 0

            packet = f"ID{self.PID}SN{seqID}TXN{self.TID}LAST{isLast}{data[sent:sent+size]}"
            print(f" {seqID} | SIZE {size}:") if prev != seq else None

            self.sock.sendto(
                packet.encode(), (self.IP_ADDRESS, self.SENDER_PORT_NO))

            t0 = time.time()

            if rate != 0:
                self.sock.settimeout(rate)

            try:
                reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)

            except KeyboardInterrupt:
                print("\n  OPTIMAL VALUE FOUND ")
                optimal = last
                size = last

            except:
                t1 = time.time()
                duration = t1 - t0
                if last != 0 and last != initsize:
                    optimal = last
                    size = optimal
                else:
                    size = int(size * 0.9)

                optimal = last
                size = last

                print(
                    f"{colors.NON}  NON | DUR: {duration:5.2f} | COM: {sent}/{len(data)}{colors.END}")
                elapsed += duration
                cons += 1
                if cons == 3:
                    break
                prev = seq

            else:
                cons = 0
                t1 = time.time()

                duration = t1 - t0

                if rate == 0:
                    rate = math.floor(duration) + 1

                ack = reply.decode()

                if self.verifyAck(seqID, ack, packet):
                    print(
                        f"{colors.ACK}  ACK | DUR: {duration:5.2f} | COM: {sent+size}/{len(data)}{colors.END}")
                else:
                    print(
                        f"{colors.ERR}  ERR | DUR: {duration:5.2f} | COM: {sent+size}/{len(data)}{colors.END}")

                sent += size
                if optimal == 0:
                    last = size
                    size = max(math.ceil((len(data)-sent) /
                                         ((90-elapsed) / rate)), size)
                prev = seq
                seq += 1
                elapsed += duration

        color = colors.ACK if elapsed < 95 else colors.NON if elapsed < 100 else colors.ERR
        print(
            f"Transaction ID: {self.TID} | DATA: {len(data)} | TIME: {color}{elapsed:.2f}{colors.END}")

    def verifyAck(self, seqID, ack, packet):
        md5 = self.compute_checksum(packet)
        correct = f"ACK{seqID}TXN{self.TID}MD5{md5}"
        return ack == correct

    def compute_checksum(self, packet):
        return hashlib.md5(packet.encode('utf-8')).hexdigest()


args = parseArguments()
sender = Sender(args)
sender.sendIntentMessage()
if sender.TID != "Existing alive transaction":
    sender.downloadPackage()
    sender.sendPackage()
else:
    print("Existing alive transaction")
