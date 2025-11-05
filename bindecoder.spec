%global python3_pkgversion 3
%define pkg bindecoder-colinhogben
%define pypackage bindecoder_colinhogben
%define release 1

Name:		%{pkg}
Version:	%{version}
Release:	1%{?dist}
Summary:    	%{summary}
License:	MIT
Vendor:		%{author} <%{author_email}>
URL:		https://github.com/colinhogben/bindecoder
Source:		%{pkg}-%{version}.tar.gz
#
BuildArch:	noarch
#BuildRequires:	python%{python3_pkgversion}-devel
#BuildRequires:	python%{python3_pkgversion}-setuptools
%description
%{summary}

# Main package
%package -n python%{python3_pkgversion}-%{pkg}
Summary:	%{summary}
%description -n python%{python3_pkgversion}-%{pkg}
%{summary}

%prep
%autosetup -p1 -n %{pkg}-%{version}

%build
%py3_build

%install
%py3_install

%files -n python%{python3_pkgversion}-%{pkg}
%{python3_sitelib}/bindecoder/*.py
%{python3_sitelib}/%{pypackage}-*.egg-info/
%{python3_sitelib}/bindecoder/__pycache__/*
