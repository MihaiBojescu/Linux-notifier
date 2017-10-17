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
from gi.repository import Notify
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import QTimer, Qt


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
            print("error")
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


class device():
    def __init__(self, name, address, pin):
        self.name = name
        self.address = address
        self.pin = pin


class authWindow(QWidget):
    def __init__(self, name, address, pin):
        super().__init__()
        self.setWindowTitle("Authentification window")
        self.icon = QIcon()
        self.icon.addFile("icon.png")
        self.setWindowIcon(self.icon)

        self.acceptButton = QPushButton("Accept", self)
        self.acceptButton.clicked.connect(self.accepted)
        self.denyButton = QPushButton("Deny", self)
        self.denyButton.clicked.connect(self.denied)

        self.label = QLabel()
        self.label.setText(''.join(("Authentification request from:\nName: ",
                                    name, ",\nAddress: ",
                                    address, ".")))
        self.pinLabel = QLabel()
        self.pinLabel.setText(''.join(("PIN: ", pin)))
        self.pinLabel.setFont(QFont("Noto Sans", 24, QFont.Normal))

        self.hBox = QHBoxLayout()
        self.hBox.addStretch(1)
        self.hBox.addWidget(self.acceptButton)
        self.hBox.addWidget(self.denyButton)

        self.vBox = QVBoxLayout()
        self.vBox.addStretch(1)
        self.vBox.addWidget(self.label)
        self.vBox.addWidget(self.pinLabel)
        self.vBox.addLayout(self.hBox)

        self.setLayout(self.vBox)

        self.timer = QTimer()
        self.timer.timeout.connect(self.closeAndDeny)
        self.timer.start(10000)

        self.show()

    def keyPressEvent(self, e):
        if(e.key() == Qt.Key_Escape):
            self.closeAndDeny()

    def accepted(self):
        self.accepted = True
        self.close()

    def denied(self):
        self.accepted = False
        self.close()

    def closeAndDeny(self):
        self.accepted = False
        self.close()


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
                dataToSend = ""

                if(message["reason"] == "authentificate"):
                    print("auth")
                    app = QApplication(sys.argv)
                    newWindow = authWindow(message["name"],
                                           str(address[0]),
                                           message["pin"])
                    app.exec_()
                    app.quit()

                    if(newWindow.accepted):
                        print("accepted")
                        dataToSend = {
                            "reason": "authresponse",
                            "response": "1"
                        }

                        newDevice = device(message["name"],
                                           str(address[0]),
                                           message["pin"])

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

                elif(message["reason"] == "notification"):
                    print("Notification from " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            self.buildNotification(currentDevice.name,
                                                   message["app name"],
                                                   message["title"],
                                                   message["data"])
                            break

                elif(message["reason"] == "revoke authentification"):
                    print("Revoking auth for " + str(address[0]))
                    for currentDevice in self.validDevices:
                        if(currentDevice.address == str(address[0])):
                            validDevices.remove(currentDevice)
                            break

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

    def buildNotification(self, deviceName, name, title, data):
        newNotification = Notify.Notification.new(''.join((deviceName,
                                                           "@", name, " app: ",
                                                           title,
                                                           data,
                                                           "dialog-information")))
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
