# Python server that runs on Base Station
# Specifications: Runs on Base station computer
# Last Revision: 1 June 2016, 11:23 PM

import socket
import threading
import time
import random

# Constants
FORWARD = 1
BACKWARD = 2
LEFT = 3
RIGHT = 4
SENDING_PORT = 9877
RECEIVING_PORT = 9876

my_host = "192.168.1.6"   # local loopback is 127.0.0.1 or just say 'localhost'
remote_host = "192.168.1.5"

# The variable which is used to halt the code in case of keyboard interrupt
globalKeepAlive = True

# Establishes and manages the connections between the devices, i.e., the on-board server and base station
class CommunicationServer:
    def __init__(self):
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # The variable which is used to halt the code in case of keyboard interrupt
        self.keepAlive = True
        global my_host
        global remote_host
        self.myHost = my_host
        self.remoteHost = remote_host
        self.sendFailCount = 0

    # Handles incoming connection. All received data is processed here
    def handleClient(self, client, address):
        while self.keepAlive:
            try:
                data = client.recv(1024)
                if not data:    # If data is None, connection has ended
                    break   # breaks out of while loop
                message = str(data.decode()).strip()
                # The data should be enclosed within {}
                if message.startswith('{') and message.endswith('}'): # Check integrity of the data received
                    print("Received from client(" + address[0] + "): " + message)
                    if message.find("CONTROL-") > 0: # >0 is Not found
                        self.send(message)
                    elif message.find("SENSOR-") > 0: # Its from the rover itself, don't send back again to rover!
                        pass
                else:
                    print("Invalid data received from client(" + address[0] + "): " + message)
            except Exception as e:
                client.close()
                print("Error while receiving: " + str(e))
                break   # breaks out of while loop. If this is not written, while loop continues even after exception

        print("Disconnected from " + address[0])
    # end of handleClient()

    # Used to accept connections from the base station. Usually started as a thread.
    def startListening(self):
        global RECEIVING_PORT
        print("Started Listening at " + self.myHost)
        self.serverSock.bind((self.myHost, RECEIVING_PORT))
        self.serverSock.listen(5)  # Handles utmost 5 clients simultaneously
        self.serverSock.settimeout(2)
        while self.keepAlive:    # When this flag is false, while breaks. keepAlive is global
            try:
                (client, address) = self.serverSock.accept()
                print("Accepted connection from: " + address[0])
                threading.Thread(target=self.handleClient, args=(client, address)).start()
            except socket.timeout as t: # Ignore timeouts
                pass
        # while ended, time to cleanup and shutdown the listening socket
        self.serverSock.shutdown(socket.SHUT_RDWR)
        self.serverSock.close()

    # Sends the string over the specified socket. Returns 0 if successful, else 1
    # If the send fails more than 3 times, the socket tries to reinitialize itself
    def send(self, string):
        global SENDING_PORT
        try:
            self.clientSock.connect((self.remoteHost, SENDING_PORT))   # Attempt to connect, if its already connected an exception is thrown
            print("Connected to: " + self.remoteHost)
        except Exception as e:      # Ignore the exception thrown if the socket is already connected
            pass
        try:
            self.clientSock.send(str(string).encode())
            self.sendFailCount = 0  # Sent successfully, reset the counter
            return 0
        except Exception as e:  # If send failed
            print("Could not send data: " + str(e))
            self.sendFailCount += 1       # Send failed, increment the counter

            if(self.sendFailCount > 3):  # Enough, sending failed for 3 times, try reinitializing the socket
                self.sendFailCount = 0
                self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # print("Socket reinitialized since it failed too many times")
            return 1
    # end of send()

    # Stops listening to the clients by turning off keepAlive
    def stop(self):
        self.keepAlive = False
        self.clientSock.shutdown(socket.SHUT_RDWR)
        self.clientSock.close()
    # serverSock will be shutdown automatically in startListening()

# end of class CommunicationServer

if __name__ == "__main__":
    comm = CommunicationServer();
    try:
        threading.Thread(target=comm.startListening, args=()).start() # Receiver thread

        # Code to continuously send data
        #while globalKeepAlive:
            # comm.send(random.random())
            # time.sleep(1)
        # while ended, time to cleanup
    except KeyboardInterrupt as e:  # Oh, the user wants to stop the program! Pressed Ctrl+C
        print("Shutting down Rover server....")
        globalKeepAlive = False
        comm.stop()