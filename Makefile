PKG = bindecoder-colinhogben
RPMNAME = bindecoder-colinhogben
PYPROJECT = bindecoder_colinhogben
ARCH = noarch

-include version.mk

# Derived
TOPDIR = $(shell pwd)
TARBALL = $(PKG)-$(VERSION).tar.gz
SRPM = $(PKG)-$(VERSION)-$(RELEASE).src.rpm
RPM = $(RPMNAME)-$(VERSION)-$(RELEASE).$(ARCH).rpm

SOURCES = README.md \
	Makefile \
	src/bindecoder/*.py \

all:	sdist

release:	tarball rpm srpm

.PHONY:	tarball
tarball:	SOURCES/$(TARBALL)
SOURCES/$(TARBALL):	$(SOURCES)
	@mkdir -p SOURCES
	tar czf $@ \
		--transform "s#^#$(PKG)-$(VERSION)/#" \
		$(SOURCES)

# Copy and customise spec file
SPECS/$(PKG).spec:	bindecoder.spec pyproject.toml
	@mkdir -p SPECS
	( ./toml2x spec; cat $< ) > $@

# Build source RPM
.PHONY:	srpm
srpm:	SRPMS/$(SRPM)
SRPMS/$(SRPM):	SOURCES/$(TARBALL) SPECS/$(PKG).spec
	rpmbuild --define "_topdir $(TOPDIR)" -v -bs SPECS/$(PKG).spec

# Build binary RPM
.PHONY:	rpm
rpm:	RPMS/$(ARCH)/$(RPM)
RPMS/$(ARCH)/$(RPM):	SOURCES/$(TARBALL) SPECS/$(PKG).spec
	rpmbuild --define "_topdir $(TOPDIR)" -v -bb SPECS/$(PKG).spec

version.mk:	pyproject.toml
	./toml2x make > $@
