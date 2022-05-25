import requests
import socket
import argparse

PID = "95b59f86"
SENDER_PORT = 6716

# Parse command line arguments
parser = argparse.ArgumentParser()

parser.add_argument("-f", "--file", help="File to send", default="payload.txt")
parser.add_argument("-a", "--address",
                    help="Server IP address", default="10.0.7.141")
parser.add_argument("-s", "--receiver_port", type=int,
                    help="Port number used by the receiver", default=9000)
parser.add_argument("-c", "--sender_port", type=int,
                    help="Port number used by the sender", default=SENDER_PORT)
parser.add_argument("-i", "--id", type=str,
                    help="Unique Identifier", default=PID)

args = parser.parse_args()

print(args)

# Downloading the payload

URL = f"http://3.0.248.41:5000/get_data?student_id={PID}"
response = requests.get(URL)
open(args.file, "wb").write(response.content)

# Establishing a UDP connection with the server
UDP_SENDER_PORT_NO = args.sender_port
UDP_RECEIVER_PORT_NO = args.receiver_port
UDP_IP_ADDRESS = args.address

clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock.bind(('', UDP_RECEIVER_PORT_NO))

# Sending an intent message

imessage = f"ID{PID}".encode()
clientSock.sendto(imessage, (UDP_IP_ADDRESS, UDP_SENDER_PORT_NO))

TID = serverSock.recvfrom(UDP_RECEIVER_PORT_NO)
print(TID)
