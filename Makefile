all:    help

help:
	@echo "make install [DESTDIR=/path/to/destdir]"

install:
	install -m 0755 -d ${DESTDIR}/usr/local/share/openstack-core-test
	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/basic
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/basic smoketests/basic/*
	


