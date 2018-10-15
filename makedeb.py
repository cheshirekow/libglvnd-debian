# -*- coding: utf-8 -*-
"""
Make debian packages. Constructs source packages with  debbuild and binary
packages with pbuilder.

To prep your system, install the following packages through apt:

* debhelper
* devscripts
* gnupg2
* pbuilder
* rsync

And the following python packages through pip

* requests

"""

from __future__ import print_function
from __future__ import unicode_literals

import argparse
import io
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time

import requests


def parse_changelog(logpath):
  """
  Parse the changelog to get package name and version number
  """
  with io.open(logpath, "r", encoding="utf-8") as infile:
    lineiter = iter(infile)
    firstline = next(lineiter)

  pattern = r"(\S+) \(([\d\.]+)-(\S+)\) (\S+); urgency=\S+"
  match = re.match(pattern, firstline)
  assert match, "Failed to match firstline pattern:\n {}".format(firstline)
  package_name = match.group(1)
  upstream_version = match.group(2)
  local_version = match.group(3)
  distribution = match.group(4)

  return package_name, upstream_version, local_version, distribution


def get_progress_bar(fraction, numchars=30):
  """
  Return a high resolution unicode progress bar
  """
  blocks = ["", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
  length_in_chars = fraction * numchars
  n_full = int(length_in_chars)
  if n_full > numchars:
    n_full = numchars

  i_partial = int(8 * (length_in_chars - n_full))
  partial = blocks[i_partial]
  n_empty = max(numchars - n_full - len(partial), 0)
  return ("█" * n_full) + partial + (" " * n_empty)


def get_human_readable_size(size_in_bytes):
  """
  Convert a number of bytes into a human readable string.
  """
  if size_in_bytes == 0:
    return '{:6.2f}{}'.format(0, " B")

  exponent = int(math.log(size_in_bytes, 1024))
  unit = [' B', 'KB', 'MB', 'GB', 'PB', 'EB'][exponent]
  size_in_units = float(size_in_bytes) / (1024 ** exponent)
  return '{:6.2f}{}'.format(size_in_units, unit)


def get_orig_tarball(version, outpath):
  """
  Download glslang.orig.tar.gz if it doesn't already exist
  """
  srcurl = ("https://github.com/NVIDIA/libglvnd/archive/v{}.tar.gz"
            .format(version))
  tmppath = outpath + ".tmp"
  if os.path.exists(tmppath):
    os.remove(tmppath)

  response = requests.head(srcurl)
  assert response.status_code < 400
  totalsize = int(response.headers.get("content-length", 2320000))
  recvsize = 0

  request = requests.get(srcurl, stream=True)
  assert request.status_code < 400
  last_print = 0

  outname = os.path.basename(outpath)
  with open(tmppath, "wb") as outfile:
    for chunk in request.iter_content(chunk_size=4096):
      outfile.write(chunk)
      recvsize += len(chunk)

      if time.time() - last_print > 0.1:
        last_print = time.time()
        percent = 100.0 * recvsize / totalsize
        message = ("Downloading {}: {}/{} [{}] {:6.2f}%"
                   .format(outname,
                           get_human_readable_size(recvsize),
                           get_human_readable_size(totalsize),
                           get_progress_bar(percent / 100.0), percent))
        sys.stdout.write(message)
        sys.stdout.flush()
        sys.stdout.write("\r")
  message = ("Downloading {}: {}/{} [{}] {:6.2f}%"
             .format(outname,
                     get_human_readable_size(totalsize),
                     get_human_readable_size(totalsize),
                     get_progress_bar(1.0), 100.0))
  sys.stdout.write(message)
  sys.stdout.write("\n")
  sys.stdout.flush()
  os.rename(tmppath, outpath)
  return outpath


def get_base_tgz(distro, arch):
  return "/var/cache/pbuilder/{}-{}-base.tgz".format(distro, arch)


def prep_pbuilder(distro, arch, basetgz):
  """
  Create base rootfs tarfiles for the specified distro/arch.
  """
  subprocess.check_call(
      ["sudo", "pbuilder", "--create", "--distribution", distro,
       "--architecture", arch, "--basetgz", basetgz])


def exec_pbuilder(dscpath, distro, arch, basetgz, outdir):
  """
  Execute pbuilder to get the binary archives
  """
  subprocess.check_call(
      ["sudo", "env", 'DEB_BUILD_OPTIONS="parallel=8"',
       "pbuilder", "--build", "--distribution", distro,
       "--architecture", arch, "--basetgz", basetgz,
       "--buildresult", outdir, dscpath])


def main():
  logging.basicConfig(level=logging.INFO)

  arches = ["i386", "amd64", "armhf", "arm64"]
  distros = ["trusty", "xenial", "bionic"]

  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--distro", choices=distros, nargs="*",
                      help="which distros to build",
                      default=list(distros))
  parser.add_argument("--arch", choices=arches, nargs="*",
                      help="which architectures to build",
                      default=["amd64"])

  srcdir = os.path.dirname(os.path.realpath(__file__))
  parser.add_argument("--src", help="source directory", default=srcdir)
  parser.add_argument("--out", help="output directory",
                      default=os.path.join(srcdir, ".out"))
  parser.add_argument("--skip-build", action="store_true")
  args = parser.parse_args()

  for distro in args.distro:
    logging.info("Building for %s", distro)

    changelog_path = os.path.join(args.src,
                                  "debian/changelog.{}".format(distro))
    (package_name, upstream_version,
     local_version, distribution) = parse_changelog(changelog_path)

    assert distribution == distro, (
        "Bad changelog for {} != {}".format(distro, distribution))

    if not os.path.isdir(args.out):
      os.makedirs(args.out)

    outname = "{}_{}.orig.tar.gz".format(package_name, upstream_version)
    origtarpath = os.path.join(args.out, outname)
    if not os.path.exists(origtarpath):
      get_orig_tarball(upstream_version, origtarpath)

    origdir = "{}-{}".format(package_name, upstream_version)
    workpath = os.path.join(args.out, origdir)

    needs_extract = False
    if os.path.exists(workpath):
      if os.stat(workpath).st_mtime < os.stat(origtarpath).st_mtime:
        logging.info("%s is out of date", origdir)
        needs_extract = True
      else:
        logging.info("%s is up to date", origdir)
    else:
      logging.info("Need to create %s", origdir)
      needs_extract = True

    if needs_extract:
      logging.info("Extracting source tarball")
      subprocess.check_call(['tar', 'xf', origtarpath], cwd=args.out)

    logging.info("Syncing debian directory")
    subprocess.check_call(['rsync', "-a",
                           os.path.join(args.src, "debian"),
                           workpath])

    logging.info("Symlinking changelog")
    changelogout = os.path.join(workpath, "debian/changelog")
    changelogsrc = os.path.join(workpath,
                                "debian/changelog.{}".format(distro))
    if os.path.lexists(changelogout):
      os.remove(changelogout)
    shutil.copyfile(changelogsrc, changelogout)

    outname = ("{}_{}-{}.dsc"
               .format(package_name, upstream_version, local_version))
    dscpath = os.path.join(args.out, outname)
    if os.path.exists(dscpath):
      logging.info("%s already built", outname)
    else:
      logging.info("Creating %s", outname)
      subprocess.check_call(['debuild', "-S", "-sa", "-pgpg2", "-k6A8A4FAF"],
                            cwd=workpath)

    if args.skip_build:
      continue
    for arch in args.arch:
      basetgz = get_base_tgz(distro, arch)
      outname = os.path.basename(basetgz)
      if os.path.exists(basetgz):
        logging.info("%s up to date", outname)
      else:
        logging.info("Making %s", outname)
        prep_pbuilder(distro, arch, basetgz)

      # NOTE(josh): this source package doesn't create just one binary package
      # so the mapping isn't very easy. Would have to parse the control file
      # to get that for real.
      outname = ("{}0_{}-{}_{}.deb"
                 .format(package_name, upstream_version, local_version, arch))

      binout = os.path.join(args.out, 'binary')
      if not os.path.exists(binout):
        os.makedirs(binout)

      outpath = os.path.join(binout, outname)
      needs_build = False
      if os.path.exists(outpath):
        if os.stat(outpath).st_mtime < os.stat(dscpath).st_mtime:
          needs_build = True
          logging.info("%s is out of date", outname)
        else:
          logging.info("%s is up to date", outname)
      else:
        needs_build = True
        logging.info("Need to create %s", outname)

      if needs_build:
        exec_pbuilder(dscpath, distro, arch, basetgz, binout)

    # Create Packages.gz so that the directory can be used as a debian
    # repository for the purposes of testing installation
    outfd = os.open(os.path.join(binout, "Packages.gz"),
                    os.O_WRONLY | os.O_CREAT, 0o655)
    proc1 = subprocess.Popen(["gzip", "-9c"], stdout=outfd,
                             stdin=subprocess.PIPE)
    os.close(outfd)
    proc2 = subprocess.Popen(["dpkg-scanpackages", ".", "/dev/null"],
                             cwd=binout, stdout=proc1.stdin)
    proc1.stdin.close()
    proc2.wait()
    proc1.wait()


if __name__ == "__main__":
  main()
