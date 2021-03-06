from __future__ import unicode_literals

import os
from buntstrap import chroot
from buntstrap import config

# dpkg architecture of the rootfs to build. If you'd like to know what
# architecture you're currently on, try running `dpkg --print-architecture`.
architecture = "amd64"

# this is only used to select reasonable defaults if you leave out some
# configuration parameters, but specify the ubuntu target suite here.
suite = "xenial"

# Which chroot application to use. There are three builtin options:
# 1. PosixApp : uses posix ``chroot`` and must be run as root
# 2. ProotApp : uses ``proot``
# 3. UchrootApp : uses ``uchroot`` which creats a user namespace. All files
#    in the target rootfs will have uid/gid ownership with mapped values
chroot_app = chroot.UchrootApp

# This is the directory of the rootfs to bootstrap.
rootfs = "/tmp/rootfs"

# If not none, then we'll set the http proxy environment variables for APT
# using this. If apt-cacher-ng is installed an active it is usually at
# http://localhost:3142. This function will check for apt-cacher-ng and
# return it if found, otherwise None.
apt_http_proxy = config.get_apt_cache_url()

# List of packages to install with apt
apt_packages = [
    # Default mesa installations
    "libegl1-mesa:amd64",
    "libegl1-mesa-dev:amd64",
    "libgl1-mesa-dev:amd64",
    "libgl1-mesa-dri:amd64",
    "libgl1-mesa-glx:amd64",
    "libglapi-mesa:amd64",
    "libgles2-mesa:amd64",
    "libglu1-mesa:amd64",
    "libglu1-mesa-dev:amd64",
    "libwayland-egl1-mesa:amd64",
    "mesa-common-dev:amd64",
    "mesa-utils",
    "mesa-va-drivers:amd64",
    "mesa-vdpau-drivers:amd64",
    # Install my new packages
    "libglvnd-dev"
]

# If true, then we will request a list of all "essential" packages from apt
# and include them in the installation.
apt_include_essential = True

# Specify the set of priority package lists to include.
apt_include_priorities = [
    "required",  # dpkg wont function without these
    # "important",  # standard set of minimal unix programs
    # "standard",  # reasonably small but not too limited character-mode system
]

# Don't forget to dpkg-scanpackages from within the binary directory
this_dir = os.path.dirname(os.path.realpath(__file__))
localbins = os.path.join(this_dir, ".out/binary")

# This is the string contents of the apt sources list used to bootstrap the
# system. The file will be written into the target rootfs before executing
# apt but will be removed afterward.
#
# deb [arch={arch}] http://ppa.launchpad.net/lttng/stable-2.9/ubuntu {suite} main
# deb [arch={arch}] http://ppa.launchpad.net/nginx/stable/ubuntu {suite} main
# deb [arch={arch}] http://ppa.launchpad.net/josh-bialkowski/libglvnd/ubuntu {suite} main
apt_sources = """
# NOTE(josh): these sources are used to bootstrap the rootfs and should be
# omitted from after initial package installation. You should not see this
# file on a live system.

deb [arch={arch}] {ubuntu_url} {suite} main universe multiverse
deb [arch={arch}] {ubuntu_url} {suite}-updates main universe multiverse
deb [arch={arch}] copy://{local} ./
""".format(arch=architecture,
           ubuntu_url=config.get_ubuntu_url(architecture),
           suite=suite, local=localbins)


# If you already have a rootfs that has been bootstrapped and you wish to
# (re)-install packages you can set this true to skip the `apt-get` update
# step. This is mostly useful during debugging/testing iteration.
apt_skip_update = False

# If you would like buntstrap to write out a package size report then specify
# here the output path where you would like that report to go.
apt_size_report = None

# If true, the apt archive cache and other state files are cleaned up. Use this
# if you want to reduce the size of your rootfs.
apt_clean = True

# If you have any plain .deb packages to install inside the rootfs list them
# here. They will be extracted along with those downloaded by apt and configured
# with the rest.
external_debs = []

# If there are any patches that you need to apply or mucking around that you
# need to do before executing dpkg --configure, then create this hook here.
# It will be executed inside the chroot so feel free to mess with any
# files you need.


def user_quirks(_chroot_app):
  pass


# Sometimes a package will fail to configure correctly only because it hasn"t
# correctly declared it"s dependencies and it gets configured out of order.
# An easy work around is to just retry dpkg --configure again. Set here the
# number of times to try execugind `dpkg --configure`.
dpkg_configure_retry_count = 1

# If installing any packages through pip, you can re-use an existing wheelhouse
# to cache binary wheels and speed up repeated bootstrapping. Specify the
# wheelhouse directory here
pip_wheelhouse = os.path.expanduser("~/wheelhouse")

# List of python package to install using pip. Note that if this list is not
# empty then `python-pip` will be included in apt_packages (if it is not
# already) and pip will be installed itself with `pip install --upgrade pip`.
# If you want to pin a specific version of pip then make sure you list it here.
pip_packages = [
    "autopep8",
    'cpplint',
    'file-magic',
    'flask',
    'oauth2client',
    'pygerrit2',
    'pylint',
    'recommonmark',
    'sphinx',
    'sqlalchemy',
]

# If you are cross-arch bootstrapping from amd64 to arm then specify here the
# path to the qemu-static binary that should be copied into the target rootfs
# during chroot execution. `get_qemu_binary(arch)` is a convenience function
# which returns the default path for the qemu-static binary for arm64 or amd64
qemu_binary = config.default_qemu_binary(architecture)
