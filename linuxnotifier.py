#!/usr/bin/env python3
import gi
import os
import sys
import uuid
import json
import signal
import socket
import threading
gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from threading import Thread
from gi.repository import Gtk
from gi.repository import Notify
from gi.repository import GObject

def exit():
    if(listenerThread):
        listenerThread.stop()
    listener.close()
    sys.exit()

def clearValidDevices():
    deviceFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "w+")
    deviceFile.write("{}");
    deviceFile.close()

def readValidDevices():
    try:
        deviceFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "r")
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
        os.makedirs(os.path.expanduser("~/.local/share/LinuxNotifier"))
        deviceFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "w+")
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
    outputFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "w+")
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
        GObject.timeout_add(10000, self.closeAndDeny)
        self.set_default(denyButton)

    def accepted(self, button):
        self.accepted = True
        self.destroy()
        Gtk.main_quit()

    def denied(self, button):
        self.accepted = False
        self.destroy()
        Gtk.main_quit()

    def closeAndDeny(self):
        self.accepted = False
        self.destroy()
        Gtk.main_quit()

class receiver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.mustContinue = True
        self.validDevices = []

    def run(self):
        while(self.mustContinue):
            print("Listening...")
            connection, address = listener.accept()
            data = connection.recv(1024)

            if(data):
                print("Got data, message: " + data.decode("utf-8") + ".")

                receivedData = json.loads(data.decode("utf-8"))
                dataToSend = ""

                if(receivedData["reason"] == "request information"):
                    print("Data is a request for information.")
                    dataToSend = {
                        "name": socket.gethostname(),
                        "mac": self.getMacAddress()
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

                        self.shouldAdd = True
                        for currentDevice in self.validDevices:
                            if(newDevice.address == currentDevice.address):
                                self.shouldAdd = False

                        if(self.shouldAdd):
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
                    print("Notification from " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            self.buildNotification(receivedData["appName"], receivedData["title"], receivedData["data"])
                            break

                elif(receivedData["reason"] == "deny authentification"):
                    print("Deny auth for " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            validDevices.remove(currentDevice)
                            break

                connection.close()

    def stop(self):
        self.mustContinue = False

    def addValidDevice(self, newDevice):
        print("New valid device: " + newDevice.name)
        self.validDevices.append(newDevice)

    def getIPAddress(self):
        return os.popen("ip route get 1 | head -n 1 | awk '{print $NF}'").read()

    def getMacAddress(self):
        macNum = hex(uuid.getnode()).replace("0x", "").upper()
        mac = ":".join(macNum[i : i + 2] for i in range(0, 11, 2))
        return mac

    def buildNotification(self, name, title, data):
        newNotification = Notify.Notification.new(name + ": " + title, data, "dialog-information")
        newNotification.show()

if __name__== "__main__":
    if(len(sys.argv) > 1 and sys.argv[1] == "clear"):
        clearValidDevices()

    else:
        try:
            Notify.init("LinuxNotifier")
            listenerThread = receiver()

            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind((listenerThread.getIPAddress(), 5005))
            listener.listen(1)
            listener.setblocking(True)

            validDevices = readValidDevices();
            if(validDevices):
                for validDevice in validDevices:
                    listenerThread.addValidDevice(validDevice)

            listenerThread.start()
            signal.pause()

        except socket.error:
            print("Network error: cannot bind port.")
            exit()
        except threading.ThreadError:
            print("Threading error: can't create thread.")
            exit()
        except KeyboardInterrupt:
            print("Keyboard interrupt detected.")
            exit()
