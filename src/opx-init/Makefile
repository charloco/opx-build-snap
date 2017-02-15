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
	install -m 755 opx-snap-vm-init.sh $(BIN)/opx-snap-vm-init
	install -m 644 80-dn-virt-intf.rules $(BIN)/80-dn-virt-intf.rules
	install -d $(DROPIN)/opx-tmpctl.service.d
	install -m 644 dropins/opx-tmpctl.conf $(DROPIN)/opx-tmpctl.service.d
	install -d $(DROPIN)/redis-server.service.d
	install -m 644 dropins/redis-server.conf $(DROPIN)/redis-server.service.d
	install -d $(DROPIN)/opx-monitor-phy-media.service.d
	install -m 644 dropins/opx-monitor-phy-media.conf $(DROPIN)/opx-monitor-phy-media.service.d
