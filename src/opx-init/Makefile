BIN:=$(DESTDIR)/usr/bin
DROPIN:=$(DESTDIR)/etc/systemd/system

all:

install:
	install -d $(BIN)
	install -m 755 test-opx-hw.sh $(BIN)/test-opx-hw
	install -m 755 opx-init-env.sh $(BIN)/opx-init-env
	install -m 755 opx-snap-init.sh $(BIN)/opx-snap-init
	install -m 755 snap-service-helper.py $(BIN)/snap-service-helper
	install -m 755 start-redis-server.sh $(BIN)/start-redis-server
	install -m 755 stop-redis-server.sh $(BIN)/stop-redis-server
	install -d $(DROPIN)/opx-tmpctl.service.d
	install -m 644 dropins/opx-tmpctl.conf $(DROPIN)/opx-tmpctl.service.d
