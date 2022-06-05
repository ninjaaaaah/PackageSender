# Package Sender

A package sender is a software responsible for transporting a file or data from one peer to anothet.

This implementation uses UDP sockets to send data from the client to the server and it does so by determining the optimal parameter values so that the data is sent at the optimal speed.

## Dependencies

To get the program running, Python 3 of version at least 3.8.10 must be installed in the system. Further, the machine should also be at the same network (AWS Virtual Private Cloud) as the TGRS for the program to work. The following is the command to check which
version of python is running on the system:

```
python3 --version
```

## Running the Program

After verifying that the version of python is at least 3.8.10, the following command can be used to run the program in normal mode.

```
python3 sender.py -f <path/to/file> -a <address> -s <server port> -c
<client port> -i <personal id>
```

## Downloading the Package

The program will not work if the file to be sent does not exist. The user may manually download the file by going to this link:

```
http://3.0.248.41:5000/get_data?student_id=<PID>
```

Replace the `<PID>` with the personal ID provided in the email. Afterwards, a text file will automatically be downloaded when the user visits this link. The text file contains the payload
that the sender should send.

The wget command could also be used to download the file. The following command would download the file from the server:

```
wget http://3.0.248.41:5000/get_data?student_id=<PID> -O <PID>.txt
```

Replace the `<PID>` with the personal ID provided in the email. The text file will be saved in the current directory with the file name `<PID>.txt`.

## Batch Testing

If batch testing would be used, make sure to modify the Sender.downloadPackage function inside the sender.py file to reflect which TGRS is being used. The current version of the program uses the new TGRS accesible [here](http://54.169.121.89:5000) which could be changed to the original
TGRS provided [here](http://3.0.248.41:5000).

The sender code could be executed in debug and batch testing mode by adding the `-d` flag which must be set to `True`. The `-t` flag must be set to the number of tests to be conducted.

```
python3 sender.py -f <path/to/file> -a <address> -s <server port> -c
<client port> -i <personal id> -d True -t <number of tests>
```

## Trace Generation

For trace generation, this is the command to run alongsiide the code. The `-f` flag filters for UDP packets and the `-w` flag writes the packets to a file.

```
sudo tshark -f "udp" -w <path/to/file>
```

## Attributions

This project was made in accomplishment of the requirements of our CS 145 class in the University of the Philippines Diliman.
