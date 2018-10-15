# Debian Packaging for libglvnd

This repository contains debian packaging metadata for the [libglvnd][1]
"GL Vendor-Neutral Dispatch" library by nvidia. The upstream source tarballs
are downloaded directly from [github][2] and debian source packages are
targeted for [launchpad][3] as a PPA.

This repository includes my maintainer script which does the following:

1. Downloads the source tarball
2. Extracts the source tarball into a working area
3. Copies the debian directory into the extracted source
4. Symlinks the distro-specific changelog to `debian/changelog`
5. Creates a signed source package with `debuild`
6. Creates a binary package with `pbuilder`

By default it does this for the last three LTS releases: `trusty`, `xenial`.

The binary packages aren't used anywhere. They are built as a sanity check
prior to uploading to launchpad.

# Notes

The libglvnd that comes with bionic marks itself in conflict with all the
respective mesa packages. I think this is OK for bionic because the packages
it is in conflict with aren't the ones that actually hold the libraries, but
just the ones providing the symlinks. However in older ubuntus there is no
separation of the mesa packages. I work around this by using dpkg-divert to
divert the main opengl shared object files to the ones provided by this package.
This is under the assumption that if any of these files exist they must be
symlinks to somewhere deeper in the tree.

Perform installation test with:

```
buntstrap -c buntstrap-cfg.py ${PWD}/.out/testroot
```

[1]: https://github.com/NVIDIA/libglvnd
[2]: https://github.com/NVIDIA/libglvnd/releases
[3]: https://launchpad.net/~josh-bialkowski/+archive/ubuntu/libglvnd