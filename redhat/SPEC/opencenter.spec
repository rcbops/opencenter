%define ver 6

# disable python byte compiling
%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

Name:       opencenter
Version:    0.1.0
Release:    %{ver}%{?dist}
Summary:        Pluggable, modular OpenCenter server
Group:          System
License:        Apache2
URL:            https://github.com/rcbops/opencenter
Source0:        opencenter-%{version}.tgz
Source1:        opencenter.conf
Source2:        opencenter.init
BuildArch: noarch

%description
some description

%package server
Summary:        Some summary
BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python >= 2.6
Requires:       python-requests
Requires:       python-flask
Requires:       python-sqlalchemy0.7
Requires:       python-migrate
Requires:       python-daemon
Requires:       python-chef
# we don't have python-gevent in epel yet
Requires:       python-gevent
Requires:       python-mako
Requires:       python-netifaces
Requires:       opencenter >= %{version}
Requires:       python-opencenter >= %{version}

%description server
The server description

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
Requires: python-gevent
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
mkdir -p $RPM_BUILD_ROOT/var/log/opencenter
install -m 600 $RPM_SOURCE_DIR/opencenter.conf $RPM_BUILD_ROOT/etc/opencenter/opencenter.conf
install -m 755 $RPM_SOURCE_DIR/opencenter.init $RPM_BUILD_ROOT/etc/init.d/opencenter
install -m 755 $RPM_BUILD_DIR/opencenter-%{version}/manage.py $RPM_BUILD_ROOT/usr/share/opencenter/manage.py
%{__python} -B setup.py install --skip-build --root $RPM_BUILD_ROOT

%files 
%config(noreplace) /etc/opencenter

%files server
%defattr(-,root,root)
/usr/bin/opencenter
/etc/init.d/opencenter
/usr/share/opencenter/manage.py

%files -n python-opencenter
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
