#!/usr/bin/env python3
import gi
import os
import sys
import uuid
import json
import signal
import socket
import warnings
import threading
from threading import Thread
gi.require_version("Notify", "0.7")
gi.require_version('Gtk', '3.0')
from gi.repository import Notify, GObject


def exit():
    if(listenerThread):
        listenerThread.stop()
    if(discoveryRecv):
        discoveryRecv.stop()
    if(discoverySend):
        discoverySend.stop()
    sys.exit()


def clearValidDevices():
    deviceFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "w+")
    deviceFile.write("{}")
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
            print("Error opening devices file (maybe it doesn't exist?).")
            return

    except FileNotFoundError:
        print("file not found error")
        os.makedirs(os.path.expanduser("~/.local/share/LinuxNotifier"))
        deviceFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/devices.json"), "w+")
        deviceFile.write("{}")
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


class configFile:
    def __init__(self):
        self.modificationDate = self.getModificationDate()
        self.defaultConfig = "[Device]@[App] app: [NewLine][Title][NewLine][Data]"

    def createConfig(self):
        try:
            configFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/config.conf"), "w+")
            configFile.write(self.defaultConfig)
            configFile.close()

        except OSError:
            exit()

    def getConfig(self):
        try:
            configFile = open(os.path.expanduser("~/.local/share/LinuxNotifier/config.conf"), "r")
            returnString = configFile.read()
            configFile.close()
            return returnString

        except OSError:
            self.createConfig()
            return self.defaultConfig

    def getModificationDate(self):
        try:
            return os.path.getmtime(os.path.expanduser("~/.local/share/LinuxNotifier/config.conf"))

        except OSError:
            try:
                self.createConfig()
                return os.path.getmtime(os.path.expanduser("~/.local/share/LinuxNotifier/config.conf"))

            except OSError:
                exit()


class device():
    def __init__(self, name, address, pin):
        self.name = name
        self.address = address
        self.pin = pin


class authThread(threading.Thread):
    def __init__(self, name, address, pin, deviceList, connection):
        Thread.__init__(self)
        self.name = name
        self.address = address
        self.pin = pin
        self.deviceList = deviceList
        self.connection = connection

    def run(self):
        self.loop = GObject.MainLoop()
        self.authNotification = Notify.Notification.new("Auth request",
                                                        ''.join(("From ", self.name, " (", self.address, "), with PIN: ", self.pin, ".")))
        self.authNotification.set_timeout(Notify.EXPIRES_NEVER)
        self.authNotification.add_action("accept", "Accept", self.acceptAuth, None)
        self.authNotification.add_action("deny", "Deny", self.denyAuth, None)
        self.authNotification.connect("closed", self.denyAuthNoClick, self)
        self.authNotification.show()
        GObject.timeout_add(10000, self.denyAuthNoClick)
        self.loop.run()

    def acceptAuth(self, notification, action, data):
        print("accepted")
        newDevice = device(self.name,
                           self.address,
                           self.pin)

        self.shouldAdd = True
        for currentDevice in self.deviceList:
            if(newDevice.address == currentDevice.address):
                self.shouldAdd = False

        if(self.shouldAdd):
            self.deviceList.append(newDevice)
            writeValidDevices(self.deviceList)

        dataToSend = {
            "reason": "authresponse",
            "response": "1"
        }
        self.connection.send(str.encode(str(dataToSend)))
        notification.close()
        self.loop.quit()

    def denyAuth(self, notification):
        dataToSend = {
            "reason": "authresponse",
            "response": "0"
        }
        self.connection.send(str.encode(str(dataToSend)))
        notification.close()
        self.loop.quit()

    def denyAuthNoClick(self):
        dataToSend = {
            "reason": "authresponse",
            "response": "0"
        }
        self.connection.send(str.encode(str(dataToSend)))
        self.authNotification.close()
        self.loop.quit()

    def denyAuthTimeout(self, param):
        self.denyAuthNoClick()


class UDPSender():
    def __init__(self):
        Thread.__init__(self)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    def sendData(self, address):
        dataToSend = {
            "reason": "linux notifier discovery",
            "from": "desktop",
            "name": socket.gethostname(),
            "mac": listenerThread.getMacAddress()
        }
        print(' '.join(("Sending to", address, "message", str(dataToSend))))
        self.socket.sendto(str.encode(str(dataToSend)), (address, 5005))

    def stop(self):
        self.socket.close()


class UDPReceiver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.mustContinue = True

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', 5005))

        except socket.error:
            print("Can't create UDP socket on port 5005.")
            exit()

    def run(self):
        while(self.mustContinue):
            data, address = self.socket.recvfrom(1024)

            if(data):
                message = json.loads(data.decode("utf-8"))
                print(message)

                if(message["reason"] == "linux notifier discovery" and
                   message["from"] == "android"):
                    discoverySend.sendData(str(address[0]))

    def stop(self):
        self.mustContinue = False
        self.socket.close()


class TCPReceiver(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.mustContinue = True
        self.validDevices = []
        self.notificationConfig = configFile()
        self.notificationStringOriginal = self.notificationConfig.getConfig()
        self.notificationConfigModDate = self.notificationConfig.getModificationDate()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind(('', 5005))
            self.socket.listen(1)
            self.socket.setblocking(True)

        except socket.error:
            print("Can't create TCP socket on port 5005.")
            exit()

    def run(self):
        while(self.mustContinue):
            print("Listening...")
            connection, address = self.socket.accept()
            data = connection.recv(1024)

            if(data):
                print("Got data, message: " + data.decode("utf-8") + ".")

                message = json.loads(data.decode("utf-8"))
                if(message["reason"] == "authentificate"):
                    print("auth")
                    newAuthThread = authThread(message["name"], str(address[0]),
                                               message["pin"], self.validDevices,
                                               connection)
                    newAuthThread.start()

                elif(message["reason"] == "notification"):
                    print("Notification from " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            self.buildNotification(currentDevice.name,
                                                   message["app name"],
                                                   message["title"],
                                                   message["data"])
                            break
                    connection.close()

                elif(message["reason"] == "revoke authentification"):
                    print("Revoking auth for " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            validDevices.remove(currentDevice)
                            break
                        connection.close()

                else:
                    connection.close()

    def stop(self):
        self.mustContinue = False
        self.socket.close()

    def addValidDevice(self, newDevice):
        self.shouldAdd = True
        for currentDevice in self.validDevices:
            if(newDevice.address == currentDevice.address):
                self.shouldAdd = False

        if(self.shouldAdd):
            print("New valid device: " + newDevice.name)
            self.validDevices.append(newDevice)

    def getMacAddress(self):
        macNum = hex(uuid.getnode()).replace("0x", "").upper()
        mac = ":".join(macNum[i: i + 2] for i in range(0, 11, 2))
        return mac

    def buildNotification(self, deviceName, appName, title, data):
        if(self.notificationConfigModDate != self.notificationConfig.getModificationDate()):
            self.notificationStringOriginal = self.notificationConfig.getConfig()

        notificationString = self.notificationStringOriginal
        notificationString = notificationString.replace("[NewLine]", os.linesep)
        notificationString = notificationString.replace("[Device]", deviceName)
        notificationString = notificationString.replace("[App]", appName)
        notificationString = notificationString.replace("[Title]", title)
        notificationString = notificationString.replace("[Data]", data)

        newNotification = Notify.Notification.new("LinuxNotifier", notificationString, "dialog-information")
        newNotification.show()


if(__name__ == "__main__"):
    warnings.simplefilter("ignore")
    if(len(sys.argv) > 1 and sys.argv[1] == "clear"):
        clearValidDevices()

    else:
        try:
            Notify.init("LinuxNotifier")
            listenerThread = TCPReceiver()

            discoverySend = UDPSender()
            discoverySend.sendData("224.0.0.1")

            discoveryRecv = UDPReceiver()
            discoveryRecv.start()

            validDevices = readValidDevices()
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
