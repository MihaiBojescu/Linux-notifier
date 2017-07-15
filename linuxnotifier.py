#!/usr/bin/env python3
import gi
import time
import uuid
import json
import socket
import threading
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from threading import Thread
from gi.repository import Gtk
from gi.repository import Notify

def trimReceivedString(string):
    return string[2:-1]

def getMacAddress():
  macNum = hex(uuid.getnode()).replace('0x', '').upper()
  mac = ':'.join(macNum[i : i + 2] for i in range(0, 11, 2))
  return mac

def getIPAddress():
    ipAddressSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ipAddressSocket.connect(("8.8.8.8", 80))
    ipAddress = ipAddressSocket.getsockname()[0]
    print("IP address: " + ipAddress)
    ipAddressSocket.close()
    return ipAddress

def buildNotification(name, data):
    Notify.init(name)
    newNotification = Notify.Notification.new(name, data, "dialog-information")
    newNotification.show()

class receiver(threading.Thread):
    def __init__(self, id, mustContinue):
        threading.Thread.__init__(self)
        self.id = id
        self.mustContinue = mustContinue

    def run(self):
        while self.mustContinue:
            print("Listening...")
            listener.listen()
            connection, address = listener.accept()
            data = connection.recv(1024)

            if data:
                print("Got data, message: " + trimReceivedString(str(data)) + ".")

                receivedData = json.loads(trimReceivedString(str(data)))
                dataToSend = ""

                if(receivedData["reason"] == "request info"):
                    print("Data is a request for information.")
                    dataToSend = {
                        "name": socket.gethostname(),
                        "mac": getMacAddress()
                    }
                    connection.send(str.encode(str(dataToSend)))

                connection.close()

        def setMustContinue(value):
            self.mustContinue = value

try:
    ipAddress = getIPAddress()
    PORT = 5005

    listener = socket.socket(socket.AF_INET,
                         socket.SOCK_STREAM)
    listener.bind((ipAddress, PORT))
    listener.listen(1)
    listener.setblocking(True)

    listenerThread = receiver(1, True)
    listenerThread.start()

except socket.error as e:
    print("Network error: can't assign IP address.")
except threading.ThreadError as e:
    print("Threading error: can't create thread.")
except KeyboardInterrupt as e:
    if(listenerThread):
        listenerThread.setMustContinue(False)
    listener.close()
