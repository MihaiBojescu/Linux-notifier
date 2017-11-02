# Linux notifier
A small python script that enables receiving android notifications on your GNU/Linux PC. It must be used in combination with [Linux Notifier Android application](https://github.com/MihaiBojescu/Linux-notifier-Android).<br>
The service will <b>run as an user service</b>.

## Requirements
* Python 3
* Libnotify
* python-gi

## Notification message configuration
The notification message can be edited. The configuration file is located in `~/.local/share/LinuxNotifier/config.conf`. For now, these are the supported labels:
* `[NewLine]` - appends a new line
* `[Device]` - shows the device name
* `[App]` - shows the app name that sent the notification
* `[Title]` - shows the title of the notification
* `[Data]` - shows the notification message

Any other text elements are ignored. Here are some examples of configurations:
* `[Device]@[App] app: [NewLine][Title][NewLine][Data]` - the default configuration. Will print like this:
```
Phone name@LinuxNotifier app:
Notification title
Notification data
```
* `[Device]:[NewLine][App] notified you this: [Data].` - will be like this:
```
Phone name:
LinuxNotifier notified you this: Notification data.
```
* `[Title][NewLine][Data][NewLine]Sent from [Device].` - will be like this:
```
Notification title
Notification data
Sent from Phone name.
```

* `String notification(String [Device])[NewLine]{[NewLine][Title][NewLine][Data][NewLine][NewLine]return [App]}` - will be like this:
```
String notification(String PhoneName)
{
Notification title
Notification data
return LinuxNotifier
}
```

## Installation
Run `sudo make install` or just `sudo make`.

## Uninstallation
Run `sudo make uninstall`
