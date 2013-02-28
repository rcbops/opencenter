%define ver 6

# disable python byte compiling
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

Name:       opencenter-server
Version:    0.1.0
Release:    %{ver}%{?dist}
Summary:        Pluggable, modular OpenCenter server

Group:          System
License:        Apache2
URL:            https://github.com/rcbops/opencenter
Source0:        opencenter.conf

BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python >= 2.6
Requires:       python-requests
Requires:       python-flask
Requires:       python-sqlalchemy
Requires:       python-migrate
Requires:       python-daemon
Requires:       python-chef
# we don't have python-gevent in epel yet
#Requires:       python-gevent
Requires:       python-mako
Requires:       python-netifaces

%description -n python-opencenter

BuildArch: noarch

%description
Pluggable, modular host-based agent.  See the output and input
managers for docs on how to write plugins.

%package -n python-opencenter
Summary: The Python bindings for OpenCenter
Requires: python >= 2.6
Requires: python-requests
Requires: python-requests
Requires: python-flask
Requires: python-sqlalchemy
Requires: python-migrate
Requires: python-daemon
Requires: python-chef
# we don't have python-gevent in epel yet
#Requires: python-gevent
Requires: python-mako
Requires: python-netifaces
Group: System

%description -n python-opencenter
The Python bindings for OpenCenter

%prep
%setup -q -n %{name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} -B setup.py build

%install
mkdir -p $RPM_BUILD_ROOT/usr/bin
mkdir -p $RPM_BUILD_ROOT/etc/init.d
mkdir -p $RPM_BUILD_ROOT/etc/opencenter
mkdir -p $RPM_BUILD_ROOT/usr/share/opencenter
install -m 600 $RPM_SOURCE_DIR/opencenter.conf $RPM_BUILD_ROOT/etc/opencenter/opencenter.conf
install -m 755 $RPM_BUILD_DIR/manage.py $RPM_BUILD_ROOT/usr/share/opencenter/manage.py
%{__python} -B setup.py install --skip-build --root $RPM_BUILD_ROOT

%files
%config(noreplace) /etc/opencenter
%defattr(-,root,root)
/usr/bin/opencenter
/usr/share/opencenter/manage.py

%files - n python-opencenter
%defattr(-,root,root)
%{python_sitelib}/*opencenter*

%clean
rm -rf $RPM_BUILD_ROOT

%post
chkconfig --add opencenter
chkconfig opencenter on

%changelog
* Mon Sep 10 2012 Joseph W. Breu (joseph.breu@rackspace.com) - 0.1.0
- Initial build
