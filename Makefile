PYPROJECT = bindecoder_colinhogben
PKG = bindecoder-colinhogben
VERSION := $(shell ./toml2x version)

# Derived
TOPDIR = $(shell pwd)

SOURCES = README.md \
	LICENSE \
	$(wildcard src/bindecoder/*.py) \
	pyproject.toml \
	setup.py \
	Makefile \
	toml2x \

all:	pybuild

#--- Build artifacts for the python ecosystem ---
WHL = $(PYPROJECT)-$(VERSION)-py3-none-any.whl
PYTARBALL = $(PYPROJECT)-$(VERSION).tar.gz

.PHONY:	pybuild
pybuild:	dist/$(WHL) dist/$(PYTARBALL)

dist/$(WHL) dist/$(PYTARBALL):	$(SOURCES)
	python -m build

#--- Build artifacts for the RPM ecosystem
ARCH = noarch
RELEASE = 1
TARBALL = $(PKG)-$(VERSION).tar.gz
SRPM = $(PKG)-$(VERSION)-$(RELEASE).src.rpm
RPM = python3-$(PKG)-$(VERSION)-$(RELEASE).$(ARCH).rpm

.PHONY:	rpms
rpms:	tarball srpm rpm

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

#--- Clean up ---
.PHONY:	clean
clean:
	rm -fr dist/ SPECS/ SOURCES/ SRPMS/ RPMS/ BUILD/ BUILDROOT/
