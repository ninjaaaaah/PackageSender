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
Download Package Function
---
This method downloads the package from the server.
? This method would only be used in debug mode for automating the testing process.
'''


def downloadPackage(file):
    URL = f"http://54.169.121.89:5000/get_data?student_id={PID}"
    response = requests.get(URL)
    open(file, "wb").write(response.content)


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
        self.debug = args.debug
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.RECEIVER_PORT_NO))

    '''
    Send Intent Message Method
    ---
    This method sends the intent message to the server and receives a transaction ID as a response.
    The transaction ID will be saved to the class variables.
    '''

    def sendIntentMessage(self):
        intent = f"ID{self.PID}".encode()
        self.sock.sendto(intent, (self.IP_ADDRESS, self.SENDER_PORT_NO))
        data, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
        self.timer = time.time()
        self.TID = data.decode()

    '''
    Send Package Method
    ---
    This method sends the package to the server.

    VARIABLES:
    ? self.file - the file to be sent
    ? self.data - the data to be sent
    ? self.length - the length of the data
    ? self.size - the size parameter of the sender
    ? self.seq - the sequence number of the package
    ? self.last - the last successful size parameter
    ? self.limit - the maximum size parameter
    ? self.elapsed - the time elapsed from establishing an intent message
    ? self.success - determines if the package was successfully sent
    ? self.target - the time limit for the sender
    ? self.status - used for printing to console, only used on debug mode
    ? self.output - used for printing to console, only used on debug mode
    ? self.eta - the expected time of arrival of the package to the receiver
    ? self.estimatedRTT - the estimated round trip time
    ? self.devRTT - the deviation of the estimated round trip time
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
        self.estimatedRTT = 0
        self.devRTT = 0

        '''
        This line prints the TID and the length of the data to be sent in the terminal if in debug mode.
        '''
        if self.debug:
            print(
                f"TID: {colors.INF}{colors.EMP}{self.TID}{colors.END} | LENGTH: {self.length}")

        while True:
            if self.checkGuard():
                break

            '''
            seqID   - the sequence number of the packet
            isLast  - determines if this is the last packet of the file to be sent
            packet  - the string of the message to be sent to the server
            '''
            seqID = f"{self.seq}".zfill(7)
            isLast = 1 if self.sent + self.size >= self.length else 0
            packet = f"ID{self.PID}SN{seqID}TXN{self.TID}LAST{isLast}{self.data[self.sent:self.sent+self.size]}"

            '''
            Sender will send the packet to the server.
            Then, if in debug mode, this will be logged to the terminal.
            '''
            self.sock.sendto(
                packet.encode(), (self.IP_ADDRESS, self.SENDER_PORT_NO))
            # if self.debug:
            #     print(f"[ {colors.TOP}{seqID}{colors.END} ] ")

            '''
            Starts the timer for the sender to calculate the RTT of the packet.
            '''
            self.initial = time.time()

            '''
            Using try catch to catch the timeout exception.
            '''
            try:
                '''
                Get a reply from the server. if reply doesn't come within the set timeout, the timeout exception will be raised.
                Otherwise, the decoded reply will be saved to the variable ack.
                '''
                reply, _ = self.sock.recvfrom(self.RECEIVER_PORT_NO)
                ack = reply.decode()

                '''
                Updates the parameters of the sender.
                '''
                self.updateParameters()

                '''
                Verify the ack received from the server and reflect the status of the packet to the output variable.
                '''
                if self.verifyAck(seqID, ack, packet):
                    self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ACK}ACK | ETA: {self.eta:6.2f}s | LEN: {self.last:2} | LIM: {self.limit:4} | RTT: {time.time() - self.initial:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"
                else:
                    self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.ERR}ERR | ETA: {self.eta:6.2f}s | LEN: {self.last:2} | LIM: {self.limit:4} | RTT: {time.time() - self.initial:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"

            # Raise an exception if the timeout is reached.
            except socket.timeout:
                # Compute for the remaining packets to recalibrate the eta.
                rem_packets = math.ceil((self.length - self.sent) / self.size)
                self.eta = self.elapsed + self.rate + rem_packets * self.rate

                # Set the limit to the current size if size is not the last successful attempt.
                self.limit = self.size if self.size != self.last else self.length

                # Set the output variable to reflect the timeout.
                self.output = f"[ {colors.TOP}{seqID}{colors.END} ] : {colors.NON}NON | ETA: {self.eta:6.2f}s | LEN: {self.size:2} | LIM: {self.limit:4} | RTT: {time.time() - self.initial:5.2f} | RAT: {self.rate:5.2f} | COM: {self.sent}/{self.length}{colors.END}"

                # Update the size parameter to whichever is less, 90% of the current size or 1 packet less than the current packet size.
                self.size = min(int(self.size * 0.9), self.size-1)
                # Finalyl, sets the size to whichever is greater, the last ack'ed size or the size obtained from the previous line.
                self.size = max(self.size, self.last)

            # Print the output variable to the terminal.
            finally:
                if self.debug:
                    # print("\033[A                             \033[A")
                    print(self.output)

        self.log()

    '''
    Check Guard Method
    ---
    This method checks if the sender has reached the end of the file or has used up the allocated transaction time.
    Returns true if either is satisfied. 
    '''

    def checkGuard(self):
        self.elapsed = time.time() - self.timer
        if self.elapsed > 120:
            return True

        if self.sent >= self.length:
            self.success = True
            return True

    '''
    Update Parameters Method
    ---
    This method updates the parameters of the sender.
    '''

    def updateParameters(self):
        self.updateRate()
        self.updateSent()
        self.updateETA()
        self.updateSize()

    '''
    Update Sent Method
    ---
    This method updates the sent parameter of the sender.

    Changes:
    ---
    ? self.sent - added with the current size since packet was ACKed.
    ? self.last - set to the current size since packet was ACKed.
    ? self.seq  - incremented by 1 since packet was ACKed.
    '''

    def updateSent(self):
        self.sent += self.size
        self.last = self.size
        self.seq += 1

    '''
    Update ETA Method
    ---
    This method updates the eta parameter of the sender.

    Computation:
    ---
    ? 1. Get the elapsed time from the initial time of initiating the transaction.
    ? 2. Check if elapsed time is greater than the target time (90s). If so, set the elapsed time to the allocated time(120s).
    ? 3. Get the remaining data left by subtracting the initial data length with the sent data length.
    ? 4. Get the remaining packets left by dividing the remaining data by the size of the packet.
    ? 5. Get the ETA by adding the elapsed time with the remaining packets multiplied by the rate of the packet.
    '''

    def updateETA(self):
        self.elapsed = time.time() - self.timer
        self.target = self.target if self.elapsed < self.target else 120
        rem_data = self.length - self.sent
        rem_packets = math.ceil(rem_data / self.size)
        self.eta = self.elapsed + (rem_packets * self.rate)

    '''
    Update Rate Method
    ---
    This method updates the rate of the sender.

    Computation:
    ---
    This is an implementation of the Exponential Weighted Moving Average at Lec 11.

    ? 1. Get the sample RTT by subtracting the initial time from the current time.
    ? 2. Get the estimated RTT by using the formula at Lec 11 slide #18.
    ? 3. Get the deviation of the estimated RTT by using the formula at Lec 11 slide #19.
    ? 4. Update the rate by using the formula at Lec 11 slide #20.
    '''

    def updateRate(self):
        alpha = 0.125
        beta = 0.25
        sampleRTT = time.time() - self.initial

        if self.estimatedRTT == 0:
            self.estimatedRTT = sampleRTT
        else:
            self.estimatedRTT = (1 - alpha)*self.estimatedRTT + alpha*sampleRTT

        self.devRTT = (1 - beta)*self.devRTT + beta * \
            abs(sampleRTT - self.estimatedRTT)

        self.rate = self.estimatedRTT + 4*self.devRTT
        if self.rate != 0:
            self.sock.settimeout(math.ceil(self.rate))

    '''
    Update Size Method
    ---
    This method updates the size of the packet to be sent.

    Computation:
    ---
    ? 1. Get the remaining time left to achieve the target time. Do this by subtracting the target time to the time elapsed.
    ? 2. Get the remaining data left to send. Do this by subtracting the initial data length with the sent data length.
    ? 3. Get the remaining packets to be sent. Do this by dividing the remaining time by the rate.
    ? 4. Check if the eta is greater than the target time.
    ?    - If it is, set size to whichever is greater, the remaining packets times the rate or, the last successful ack incremented by one.
    ?    - Then, check if the size is greater than the limit.
    ?    - If it is, set the size to the limit-1.
    '''

    def updateSize(self):
        rem_time = self.target - self.elapsed
        rem_data = self.length - self.sent
        rem_packets = math.floor(rem_time/self.rate)
        if self.eta > self.target:
            self.size = max(math.ceil(rem_data / rem_packets), self.last + 1)
            self.size = self.size if self.size < self.limit else self.limit - 1

    '''
    Verify ACK Method
    ---
    This method will verify the ack received from the server.

    Computation:
    ---
    ? 1. Compute the expected Checksum by using the function provided in the project specs.
    ? 2. Determine the right ACK to be received from the server by using the formatting provided in the project specs.
    ? 3. Check if the received checksum is equal to the expected checksum.
    '''

    def verifyAck(self, seqID, ack, packet):
        md5 = self.computeChecksum(packet)
        correct = f"ACK{seqID}TXN{self.TID}MD5{md5}"
        return ack == correct

    '''
    Compute Checksum Method
    ---
    This method will compute the checksum of the packet and is provided in the project specs.
    '''

    def computeChecksum(self, packet):
        return hashlib.md5(packet.encode('utf-8')).hexdigest()

    '''
    Wait End Method
    ---
    This method will wait for the end of the allocated time for the transaction to end.
    '''

    def waitEnd(self):
        while True:
            remaining = 130 - (time.time() - self.timer)
            if self.debug:
                print(
                    f"{remaining:.2f}s | [{('█'*int(math.ceil(remaining/120 *10))).ljust(10)}]")
                print("\033[A                             \033[A")
            if remaining <= 0:
                break
        print("Transaction closed.")
        self.file.close()

    '''
    Log Method
    ---
    This method will log the transaction results to the log file.
    
    LOGGING VARIABLES:
    ? Color variable - is used for coloring the outputs whether it passes the 95s mark or 120s mark.
    ? Code variable  - is used for coloring the outputs for whether the packet was successfully sent or not.
    ? self.status    - SUCCESS or FAIL. Used for printing to console, only used on debug mode
    ? self.result    - Transaction result is used for printing to console, only used on debug mode
    '''

    def log(self):
        self.elapsed = time.time() - self.timer
        color = colors.ACK if self.elapsed < 95 else colors.NON if self.elapsed < 120 else colors.ERR
        code = colors.ACK if self.success else colors.ERR
        status = 'SUCCESS' if self.success else 'FAIL'
        result = f"| {colors.INF}{colors.EMP}{self.TID}{colors.END} | {code}{status.center(7)}{colors.END} | {color}{self.elapsed:6.2f}{colors.END} |"
        if self.debug:
            print(result)


args = parseArguments()
sender = Sender(args)
for i in range(args.tests):
    # downloadPackage(args.file)
    sender.sendIntentMessage()
    if sender.TID != "Existing alive transaction":
        sender.sendPackage()
        sender.waitEnd()
        sender.log()
    else:
        print("Existing alive transaction")
