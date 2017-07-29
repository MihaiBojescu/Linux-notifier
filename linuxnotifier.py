#!/usr/bin/env python3
import gi
import os
import sys
import time
import uuid
import json
import codecs
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

def buildNotification(name, title, data):
    newNotification = Notify.Notification.new(name + ": " + title, data, "dialog-information")
    newNotification.show()

def readValidDevices():
    try:
        deviceFile = open(os.environ["HOME"] + "/.local/share/LinuxNotifier/devices.json", "r")
        jsonObject = json.load(deviceFile)
        deviceFile.close()
        devices = []

        try:
            i = 0
            for deviceName in jsonObject["name"]:
                newDevice = device(jsonObject["name"][i],
                                   jsonObject["address"][i],
                                   jsonObject["pin"][i])
                devices.append(newDevice)
                i += 1
            return devices
        except:
            print("error")
            return
    except FileNotFoundError:
        print("file not found error")
        os.makedirs(os.environ["HOME"] + "/.local/share/LinuxNotifier/")
        deviceFile = open(os.environ["HOME"] + "/.local/share/LinuxNotifier/devices.json", "w+")
        deviceFile.write("{}");
        deviceFile.close()
        return

def writeValidDevices(deviceList):
    jsonObject = {}
    names = []
    addresses = []
    pins = []

    for currentDevice in deviceList:
        names.append(currentDevice.name)
        addresses.append(currentDevice.address)
        pins.append(currentDevice.pin)

    jsonObject["name"] = names
    jsonObject["address"] = addresses
    jsonObject["pin"] = pins

    output = json.dumps(jsonObject)
    outputFile = open(os.environ["HOME"] + "/.local/share/LinuxNotifier/devices.json", "w+")
    outputFile.write(output)
    outputFile.close()


class device():
    def __init__(self, name, address, pin):
        self.name = name
        self.address = address
        self.pin = pin

class authWindow(Gtk.Window):
    def __init__(self, name, address, pin):
        Gtk.Window.__init__(self, title="Linux notifier")

        vBox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hBox = Gtk.Box(spacing=2)

        self.add(vBox)

        label = Gtk.Label()
        label.set_markup("Authentification request from " + name + " (" + address + ").")
        pinLabel = Gtk.Label()
        pinLabel.set_markup("<span size=\"24000\">PIN: " + pin + "</span>")

        vBox.pack_start(label, True, True, 0)
        vBox.pack_start(pinLabel, True, True, 0)
        vBox.pack_start(hBox, True, True, 0)

        acceptButton = Gtk.Button.new_with_label("Accept")
        acceptButton.connect("clicked", self.accepted)
        denyButton = Gtk.Button.new_with_label("Deny")
        denyButton.connect("clicked", self.denied)
        self.connect("delete-event", self.denied)

        hBox.pack_start(denyButton, True, True, 0)
        hBox.pack_start(acceptButton, True, True, 0)

        self.present()
        self.set_keep_above(True)
        self.set_default(denyButton)

    def accepted(self, button):
        self.accepted = True
        self.destroy()
        Gtk.main_quit()

    def denied(self, button):
        self.accepted = False
        self.destroy()
        Gtk.main_quit()

class receiver(threading.Thread):
    def __init__(self, id, mustContinue):
        threading.Thread.__init__(self)
        self.id = id
        self.mustContinue = mustContinue
        self.validDevices = []

    def run(self):
        while self.mustContinue:
            print("Listening...")
            listener.listen()
            connection, address = listener.accept()
            data = connection.recv(1024)

            if data:
                print("Got data, message: " + trimReceivedString(str(data)) + ".")

                receivedData = json.loads(data.decode('utf-8'))
                dataToSend = ""

                if(receivedData["reason"] == "request information"):
                    print("Data is a request for information.")
                    dataToSend = {
                        "name": socket.gethostname(),
                        "mac": getMacAddress()
                    }
                    connection.send(str.encode(str(dataToSend)))

                elif(receivedData["reason"] == "authentificate"):
                    print("auth")
                    newWindow = authWindow(receivedData["name"], receivedData["address"], receivedData["pin"])
                    newWindow.show_all()
                    Gtk.main()

                    if(newWindow.accepted):
                        print("accepted")
                        dataToSend = {
                            "reason": "authresponse",
                            "response": "1"
                        }

                        newDevice = device(receivedData["name"], receivedData["address"], receivedData["pin"])
                        if(newDevice not in self.validDevices):
                            self.validDevices.append(newDevice)
                            writeValidDevices(self.validDevices)

                        connection.send(str.encode(str(dataToSend)))
                    else:
                        print("denied")
                        dataToSend = {
                            "reason": "authresponse",
                            "response": "0"
                        }
                        connection.send(str.encode(str(dataToSend)))

                elif(receivedData["reason"] == "notification"):
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            buildNotification(receivedData["appName"], receivedData["title"], receivedData["data"])
                            break

                connection.close()

    def setMustContinue(self, value):
        self.mustContinue = value

    def addValidDevice(self, newDevice):
        print("New valid device: " + newDevice.name)
        self.validDevices.append(newDevice)


if __name__=="__main__":
    try:
        Notify.init("LinuxNotifier")
        ipAddress = getIPAddress()
        PORT = 5005

        listener = socket.socket(socket.AF_INET,
                             socket.SOCK_STREAM)
        listener.bind((ipAddress, PORT))
        listener.listen(1)
        listener.setblocking(True)
        listenerThread = receiver(1, True)

        validDevices = readValidDevices();
        if(validDevices):
            for validDevice in validDevices:
                listenerThread.addValidDevice(validDevice)

        listenerThread.start()

    except socket.error:
        print("Network error: can't assign IP address.")
    except threading.ThreadError:
        print("Threading error: can't create thread.")
    except KeyboardInterrupt:
        print("Keyboard interrupt detected")
        if(listenerThread):
            listenerThread.setMustContinue(False)
        listener.close()
