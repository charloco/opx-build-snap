src = $(wildcard *.c)
obj = $(src:.c=.o)

CFLAGS=-Wall -Werror -g -O0
LDFLAGS= -lsystemd -lbsd -lpthread

service-helper: $(obj)
	$(CC) -o $@ $^ $(LDFLAGS)

.PHONY: clean install

clean:
	rm -f $(obj) service-helper

install: service-helper
	mkdir -p $(DESTDIR)$(PREFIX)/usr/bin
	cp $< $(DESTDIR)$(PREFIX)/usr/bin/$<
