install:
	cp ./linuxnotifier.py /usr/bin/linuxnotifier
	cp ./linuxnotifier.service /etc/systemd/user/linuxnotifier.service

uninstall:
	rm /usr/bin/linuxnotifier
	rm /etc/systemd/user/linuxnotifier.service

info:
	@echo "Run \"sudo make install\" to install."
	@echo "Run \"sudo make uninstall\" to remove."

.PHONY: install
