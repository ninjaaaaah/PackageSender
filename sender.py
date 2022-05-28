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
    parser.add_argument("-t", "--testcases", type=int,
                        help="Number of Testcases", default=1)
    args = parser.parse_args()
    return args


class colors:
    TOP = '\033[95m'
    ACK = '\033[92m'
    NON = '\033[93m'
    ERR = '\033[91m'
    END = '\033[0m'
    INF = '\033[94m'
    EMP = '\033[1m'


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
        self.timer = time.time()
        intent = f"ID{self.PID}".encode()
        self.sock.sendto(intent, (self.IP_ADDRESS, self.SENDER_PORT_NO))
        data, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
        self.TID = data.decode()

    def sendPackage(self):
        self.file = open(f"{self.PID}.txt", "r")
        data = self.file.read()
        sent = 0
        size = 1
        rate = 0
        seq = 0
        last = 0
        limit = len(data)
        elapsed = 0
        cons = 0
        done = False
        target = 90
        status = None
        output = ""
        eta = 0

        print(
            f"TID: {colors.INF}{colors.EMP}{self.TID}{colors.END} | DATA: {len(data)}")

        self.sock.settimeout(15)
        while True:
            if time.time() - self.timer > 120:
                break

            if sent >= len(data):
                done = True
                break

            seqID = f"{seq}".zfill(7)
            isLast = 1 if sent + size >= len(data) else 0

            packet = f"ID{self.PID}SN{seqID}TXN{self.TID}LAST{isLast}{data[sent:sent+size]}"

            self.sock.sendto(
                packet.encode(), (self.IP_ADDRESS, self.SENDER_PORT_NO))

            print(f"[ {colors.TOP}{seqID}{colors.END} ] ")

            t0 = time.time()
            try:
                reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
                cons = 0

                ack = reply.decode()

                rate = (seq*rate + time.time() - t0) / \
                    (seq + 1) if rate != 0 else time.time() - t0
                if rate != 0:
                    self.sock.settimeout(rate+1)

                eta = elapsed + ((len(data) - sent) / size) * rate

                if self.verifyAck(seqID, ack, packet):
                    output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ACK}ACK | ETA: {eta:5.2f}s | LEN: {size:2} | LIM: {limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {rate:5.2f} | COM: {sent+size}/{len(data)}{colors.END}"
                else:
                    output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ERR}ERR | ETA: {eta:5.2f}s | LEN: {size:2} | LIM: {limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {rate:5.2f} | COM: {sent+size}/{len(data)}{colors.END}"

                target = target if elapsed < target else 120
                sent += size

                last = size
                size = max(math.ceil((len(data)-sent) /
                                     math.ceil((target-elapsed) / math.floor(rate+1))), last)
                size = size if size < limit else (last+limit) // 2
                seq += 1

                limit = size if size != last else len(data)

            except socket.timeout:
                try:
                    reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
                except socket.timeout:

                    eta = elapsed + rate + ((len(data) - sent) / size) * rate
                    limit = size if size != last else len(data)

                    output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.NON}NON | ETA: {eta:5.2f}s | LEN: {size:2} | LIM: {limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {rate:5.2f} | COM: {sent}/{len(data)}{colors.END}"

                    size = max(min(int(size * 0.5), size-1), last)

                    cons += 1
                    if cons == 5:
                        break

            finally:

                elapsed = time.time() - self.timer
                print("\033[A                             \033[A")
                print(output)
                open(f"transactions/{self.TID}.log", "a").write(f"{output}\n")

        elapsed = time.time() - self.timer
        color = colors.ACK if elapsed < 95 else colors.NON if elapsed < 100 else colors.ERR
        status = 'SUCCESS' if done else 'FAIL'
        code = colors.ACK if done else colors.ERR
        self.result = f"| {colors.INF}{colors.EMP}{self.TID}{colors.END} | {code}{status.center(7)}{colors.END} | {color}{elapsed:6.2f}{colors.END} |"
        print(self.result)

    def verifyAck(self, seqID, ack, packet):
        md5 = self.compute_checksum(packet)
        correct = f"ACK{seqID}TXN{self.TID}MD5{md5}"
        return ack == correct

    def compute_checksum(self, packet):
        return hashlib.md5(packet.encode('utf-8')).hexdigest()

    def waitEnd(self):
        while True:
            remaining = 130 - (time.time() - self.timer)
            print(
                f"{remaining:.2f}s | [{('█'*int(math.ceil(remaining/120 *10))).ljust(10)}]")
            print("\033[A                             \033[A")
            if remaining <= 0:
                break
        print("Terminated successfully.")
        self.file.close()

    def log(self):
        open('log.txt', 'a').write(f"{self.result}\n")


args = parseArguments()
sender = Sender(args)
for i in range(args.testcases):
    sender.downloadPackage()
    sender.sendIntentMessage()
    if sender.TID != "Existing alive transaction":
        sender.sendPackage()
        sender.waitEnd()
        sender.log()
    else:
        print("Existing alive transaction")
