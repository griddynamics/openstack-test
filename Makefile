all:    help

help:
	@echo "make install [DESTDIR=/path/to/destdir]"

install: clean
	install -m 0755 -d ${DESTDIR}/usr/local/share/openstack-core-test
	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/basic
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/basic smoketests/basic/*

	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/local_volumes
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/local_volumes smoketests/local_volumes/*

#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flat-network
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flat-network smoketests/flat-network/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flip
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flip smoketests/flip/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/keystone
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/keystone smoketests/keystone/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/secgroup
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/secgroup smoketests/secgroup/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/volume
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/volume smoketests/volume/*

	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/_setup
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/_setup smoketests/_setup/*

	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/_remove
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/_remove smoketests/_remove/*

#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flat-network
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flat-network smoketests/flat-network/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flip
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/flip smoketests/flip/*
#
	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/keystone
	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/keystone smoketests/keystone/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/secgroup
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/secgroup smoketests/secgroup/*
#
#	install -m 0755	-d  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/volume
#	install -m 0755 -t  ${DESTDIR}/usr/local/share/openstack-core-test/smoketests/volume smoketests/volume/*

clean:
	 @printf "Cleaning up files that are already in .gitignore... "
	@for pattern in `cat .gitignore | grep -v idea`; do find . -name "$$pattern" -delete; done
	@echo "OK!"
