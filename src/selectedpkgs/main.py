import re
import logging
from pathlib import Path
from sys import stderr
from argparse import ArgumentParser

dpkg_status = Path("/var/lib/dpkg/status")
auto_installed_priorities = ["required", "important"]

# setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# regex to match package names without version annotations
pkg_name = re.compile(r"[a-zA-Z0-9-.]*")


# get_args
# --------
# parses arguments for debugging
def get_args(args=None):
    parser = ArgumentParser(
        prog="selectedpkgs",
        description="gets user-installed packages in Debian 12 by parsing /var/lib/dpkg/status",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="enable debug logging"
    )
    parser.add_argument("-l", "--debug-logfile", help="set debug logfile")
    return parser.parse_args(args)


# Package
# --------
# abstraction of a package containing data relevant to us
class Package:
    def __init__(self, name, essential=False, priority="", source=""):
        self.name = name
        self.essential = essential
        self.priority = priority
        self.source = source

    def __repr__(self):
        return str(self.__dict__)

    # is_required
    # --------
    # check if a package is required by source, priority, essential
    def is_required(self):
        if (
            not self.essential
            and self.priority not in auto_installed_priorities
            and self.source == ""
        ):
            return False
        return True

    # from_pkg_buffer
    # --------
    # factory method to instantiate packages from list of lines
    @classmethod
    def from_pkg_buffer(cls, pkg_buffer):
        props = buffer_to_props(pkg_buffer)

        essential = True if props.get("Essential", "") == "yes" else False

        # instantiate pkg
        pkg = cls(
            props.get("Package"),
            essential,
            props.get("Priority", ""),
            props.get("Source", ""),
        )

        logger.debug(f"initialized pkg: {pkg}")

        return pkg


# buffer_to_props
# --------
# converts lines in a buffer from "Key: Value" to a dict.
# - ignores lines with no ":"
def buffer_to_props(buffer):
    props = {}
    for line in buffer:
        split_line = line.split(": ")
        if len(split_line) > 1:
            props[split_line[0]] = "".join(split_line[1:]).strip()
    return props


# parse_packages
# --------
# parses file_path to a list of packages and a list of all dependencies
def parse_packages(file_path, delimiter="\n"):

    pkgs = []
    pkg_buffer = []

    with open(file_path, "r") as f:
        for line in f:
            if line == delimiter:
                pkg = Package.from_pkg_buffer(pkg_buffer)
                pkgs.append(pkg)

                # reset buffer
                pkg_buffer = []
            else:
                pkg_buffer.append(line)
    return pkgs


def main(args=None):

    args = get_args(args)

    # init logging
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(levelname)s: %(message)s")

    # setup debug logfile
    if args.debug_logfile:
        file_ch = logging.FileHandler(args.debug_logfile)
        file_ch.setLevel(logging.DEBUG)
        file_ch.setFormatter(formatter)
        logger.addHandler(file_ch)

    # setup debug logging
    if args.debug:
        ch.setLevel(logging.DEBUG)

    # finish logging init
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.debug("logging initialized")

    # verify dpkg_status is a file
    if not dpkg_status.is_file():
        logger.error(f"{dpkg_status} is not a file")
        return 1

    pkgs = parse_packages(dpkg_status)

    # print what should be user-installed packages
    for pkg in pkgs:
        if not pkg.is_required():
            print(pkg.name)