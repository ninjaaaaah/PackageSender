import requests
import socket

PID = "95b59f86"

# Downloading the payload

URL = f"http://3.0.248.41:5000/get_data?student_id={PID}"
response = requests.get(URL)
open("payload.txt", "wb").write(response.content)

# Establishing a UDP connection with the server
UDP_SENDER_PORT_NO = 6716
UDP_RECEIVER_PORT_NO = 9000
UDP_IP_ADDRESS = "54.169.205.232"

# Sending an intent message

imessage = f"ID{PID}".encode()

clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
clientSock.sendto(imessage, (UDP_IP_ADDRESS, UDP_SENDER_PORT_NO))

serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serverSock.bind(('', UDP_RECEIVER_PORT_NO))

TID = serverSock.recvfrom(UDP_RECEIVER_PORT_NO)
