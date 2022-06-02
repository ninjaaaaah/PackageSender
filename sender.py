import math
import time
import requests
import socket
import argparse
import hashlib

PID = "95b59f86"
SENDER_PORT = 6716

''' 
Parse Arguments Function
---
This function parses the arguments passed to the program and returns them as a dictionary. 

FLAGS:
? -f, --file, the path directory of the file to send
? -a, --address, the address of the server
? -s, --receiver_port, the port number used by the receiver
? -c, --sender_port, the port number used by the sender
? -i, --id, the unique identifier
? -t, --tests, the number of tests to be used
? -d, --debug, the debug flag

'''


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
    parser.add_argument("-t", "--tests", type=int,
                        help="Number of tests", default=1)
    parser.add_argument("-d", "--debug", type=bool,
                        help="Toggle debug mode", default=False)
    args = parser.parse_args()
    return args


''' 
Colors Class
---
This a helper class used to print colored text for debugging.
? Class will only be used if the debug flag is active 
'''


class colors:
    TOP = '\033[95m'
    ACK = '\033[92m'
    NON = '\033[93m'
    ERR = '\033[91m'
    END = '\033[0m'
    INF = '\033[94m'
    EMP = '\033[1m'


'''
Sender Class
---
This class contains all the methods used in the UDP connection with the server.
'''


class Sender:
    ''' 
    Initialize Method
    ---
    This method initializes the UDP connection with the server with the command liine arguments provided.
    '''

    def __init__(self, args) -> None:
        self.PID = PID
        self.SENDER_PORT = SENDER_PORT
        self.FILE_NAME = args.file
        self.SENDER_PORT_NO = args.sender_port
        self.RECEIVER_PORT_NO = args.receiver_port
        self.IP_ADDRESS = args.address
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.RECEIVER_PORT_NO))

    ''' 
    Download Package Method
    ---
    This method downloads the package from the server.
    ? This method would only be used in debug mode for automating the testing process.
    '''

    def downloadPackage(self):
        URL = f"http://3.0.248.41:5000/get_data?student_id={self.PID}"
        response = requests.get(URL)
        open(self.FILE_NAME, "wb").write(response.content)

    '''
    Send Intent Message Method
    ---
    This method sends the intent message to the server and receives a transaction ID as a response.
    The transaction ID will be saved to the class variables.
    '''

    def sendIntentMessage(self):
        self.timer = time.time()
        intent = f"ID{self.PID}".encode()
        self.sock.sendto(intent, (self.IP_ADDRESS, self.SENDER_PORT_NO))
        data, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
        self.TID = data.decode()

    '''
    Send Package Method
    ---
    This method sends the package to the server.
    '''

    def sendPackage(self):
        self.file = open(f"{self.PID}.txt", "r")
        self.data = self.file.read()
        self.length = len(self.data)
        self.sent = 0
        self.size = 1
        self.rate = 0
        self.seq = 0
        self.last = 0
        self.limit = self.length
        self.elapsed = 0
        self.success = False
        self.target = 95
        self.status = None
        self.output = ""
        self.eta = 0

        print(
            f"TID: {colors.INF}{colors.EMP}{self.TID}{colors.END} | DATA: {self.length}")

        self.sock.settimeout(15)
        while True:
            if self.elapsed > 120:
                break

            if self.sent >= self.length:
                self.success = True
                break

            seqID = f"{self.seq}".zfill(7)
            isLast = 1 if self.sent + self.size >= self.length else 0

            packet = f"ID{self.PID}SN{seqID}TXN{self.TID}LAST{isLast}{self.data[self.sent:self.sent+self.size]}"

            self.sock.sendto(
                packet.encode(), (self.IP_ADDRESS, self.SENDER_PORT_NO))

            print(f"[ {colors.TOP}{seqID}{colors.END} ] ")

            t0 = time.time()
            try:
                reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
                ack = reply.decode()

                if self.rate != 0:
                    self.sock.settimeout(math.ceil(self.rate))

                self.sent += self.size
                self.last = self.size
                self.elapsed = time.time() - self.timer
                self.eta = self.elapsed + \
                    ((self.length - self.sent) / self.size) * self.rate
                self.target = self.target if self.elapsed < self.target else 120
                self.updateSize()
                self.seq += 1
                self.rate = (self.seq*self.rate + time.time() - t0) / \
                    (self.seq + 1) if self.rate != 0 else time.time() - t0

                if self.verifyAck(seqID, ack, packet):
                    self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ACK}ACK | ETA: {self.eta:6.2f}s | LEN: {self.last:2} | LIM: {self.limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"
                else:
                    self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ERR}ERR | ETA: {self.eta:6.2f}s | LEN: {self.last:2} | LIM: {self.limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"

            except socket.timeout:
                self.eta = self.elapsed + self.rate + \
                    ((self.length - self.sent) / self.size) * self.rate
                self.limit = self.size if self.size != self.last else len(
                    self.data)

                self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.NON}NON | ETA: {self.eta:6.2f}s | LEN: {self.size:2} | LIM: {self.limit:4} | RTT: {time.time() - t0:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"

                self.size = max(
                    min(int(self.size * 0.9), self.size-1), self.last)

            finally:
                self.elapsed = time.time() - self.timer
                print("\033[A                             \033[A")
                print(self.output)

        self.elapsed = time.time() - self.timer
        color = colors.ACK if self.elapsed < 95 else colors.NON if self.elapsed < 100 else colors.ERR
        self.status = 'SUCCESS' if self.success else 'FAIL'
        code = colors.ACK if self.success else colors.ERR
        self.result = f"| {colors.INF}{colors.EMP}{self.TID}{colors.END} | {code}{self.status.center(7)}{colors.END} | {color}{self.elapsed:6.2f}{colors.END} |"
        print(self.result)

    def updateSize(self):
        rem_time = self.target - self.elapsed
        rem_data = self.length-self.sent
        if self.eta > self.target:
            self.size = max(math.ceil(
                (rem_data / rem_time) * self.rate), self.last+1)
            self.size = self.size if self.size < self.limit else min(math.floor(
                (self.seq*self.last+self.limit) / (self.seq+1)), self.limit-1)

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
        print("Transaction closed.")
        self.file.close()

    def log(self):
        open('log.txt', 'a').write(f"{self.result}\n")


args = parseArguments()
sender = Sender(args)
for i in range(args.tests):
    sender.downloadPackage()
    sender.sendIntentMessage()
    if sender.TID != "Existing alive transaction":
        sender.sendPackage()
        sender.waitEnd()
        sender.log()
    else:
        print("Existing alive transaction")
