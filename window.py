#!/usr/bin/env python3
import gi
import time
import socket
import threading
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from threading import Thread
from gi.repository import Gtk
from gi.repository import Notify

def trimReceivedString(string):
    return string[2:-1]

class MyWindow(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title="Hello World")

        self.box = Gtk.Box(spacing=1, orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)
        self.label = Gtk.Label("Devices that attempted a connection:")
        self.box.pack_start(self.label, True, True, 0)

        self.receiveThread = Thread(target=self.receiver, args=(self.label,))
        self.receiveThread.setDaemon(True)
        self.receiveThread.start()

    def receiver(self, label):
        while True:
            print("listening...")
            sock.listen();
            conn, addr = sock.accept()
            data = conn.recv(1024)
            label.set_text(label.get_text() + "\n" + str(addr))

            if data:
                print("Got data, message: " + trimReceivedString(str(data)))
                Notify.init("Notification from Android")
                Hello=Notify.Notification.new("Notification from Android", trimReceivedString(str(data)), "dialog-information")
                Hello.show()
                conn.send(socket.gethostname().encode("UTF-8"))
            conn.close()

    def keyPress(self, widget, event):
        if(event.keyval == 65307):
            Gtk.main_quit()

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    IP = s.getsockname()[0]
    print("IP address: " + IP)
    s.close()
    PORT = 5005
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_STREAM) # TCP
    sock.bind((IP, PORT))
    sock.listen(1);
    sock.setblocking(True)

    win = MyWindow()
    win.connect("delete-event", Gtk.main_quit)
    win.connect("key-press-event", win.keyPress)
    win.show_all()
    Gtk.main()
except Exception as e:
    print("Network error: can't assign IP address")
