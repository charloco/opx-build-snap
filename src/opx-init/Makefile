BIN:=$(DESTDIR)/usr/bin
DROPIN:=$(DESTDIR)/etc/systemd/system

all:

install:
	install -d $(BIN)
	install -m 755 test-opx-hw.sh $(BIN)/test-opx-hw
	install -m 755 opx-init-env.sh $(BIN)/opx-init-env
	install -m 755 opx-snap-init.sh $(BIN)/opx-snap-init
	install -m 755 snap-service-helper.py $(BIN)/snap-service-helper
	install -m 755 snapify-redis-config.sh $(BIN)/snapify-redis-config
	install -d $(DROPIN)/opx-tmpctl.service.d
	install -m 644 dropins/opx-tmpctl.conf $(DROPIN)/opx-tmpctl.service.d
	install -d $(DROPIN)/redis-server.service.d
	install -m 644 dropins/redis-server.conf $(DROPIN)/redis-server.service.d
