#
# spec file for package openstack-core-test
#
# Copyright 2011 Grid Dynamics Consulting Services, Inc. All rights reserved.
#

Name:		openstack-core-test		
Version:	0.0.1
Release:	1%{?dist}
Summary:	BDD test suite for OpenStack

Group:		Development/Languages/Python
License:	GNU GPL v3+
URL:		https://github.com/griddynamics/openstack-core-test
Source0:	%{name}-%{version}.tar.gz
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix:		%{_prefix}
BuildArch:      noarch

BuildRequires:	python-setuptools coreutils
Requires:	python-bunch

%description
Test harness for OpenStack written for Bunch tool


%prep
%setup -q -n %{name}-%{version}

%build

%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT


%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
/usr/local/share/%{name}


%changelog
* Thu Feb 2 2012 Sergey Kosyrev  <skosyrev@griddynamics.com>
- initial packaging

