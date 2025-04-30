import re
import logging
from pathlib import Path
from sys import stderr
from argparse import ArgumentParser

dpkg_status = Path("/var/lib/dpkg/status")

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
    parser.add_argument("--disable-dependency-checking", action="store_true", help="disable dependency checking")
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
        self.dependencies = []
        self.recommends = []

    def __repr__(self):
        return str(self.__dict__)

    # parse_dependencies
    # --------
    # parse a dependency line into a list of dependencies (w/o version annotations)
    def parse_dependencies(self, dependencies_line, recommends=False):

        logger.debug(f"got dependency line: {dependencies_line}")

        # treat "|" as "," as we do not care in this case
        dependencies = dependencies_line.replace("|", ",").split(",")

        for dependency in dependencies:

            # remove version annotations from package name as we don't care
            name = pkg_name.search(dependency.strip()).group(0)

            if name:  # split() will return a "" element - make sure these aren't added
                if recommends:
                    # ensure recommend isn't cyclical
                    if name != self.source:
                        self.recommends.append(name)
                else:
                    self.dependencies.append(name)
    
    # is_required
    # --------
    # check if a pkg is required
    def is_required(self):
        if not self.essential and self.priority != "required" and self.source == "":
            return False
        return True
    
    # resolve_dependencies
    # --------
    # resolve each dependency from a string to the package it references
    def resolve_dependencies(self, packages):
        for idx, dependency in self.dependencies:
            self.dependencies[idx] = packages.get(dependency, dependency)
            if self.dependencies[idx] == dependency:
                logger.warning(f"unable to find {self.name}'s dependency {dependency}")
        for idx, recommend in self.recommends:
            self.recommends[idx] = packages.get(recommend, recommend)
            if self.recommends[idx] == recommend:
                logger.warning(f"unable to find {self.name}'s recommend {recommend}")


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

        # add dependencies
        pkg.parse_dependencies(props.get("Depends", ""))
        pkg.parse_dependencies(props.get("Recommends", ""), recommends=True)

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

    pkgs = {}
    dependencies = set()
    pkg_buffer = []

    with open(file_path, "r") as f:
        for line in f:
            if line == delimiter:
                pkg = Package.from_pkg_buffer(pkg_buffer)
                pkgs[pkg.name] = pkg

                # add dependencies and recommends as dependencies - in our case we don't care which
                if len(pkg.dependencies):
                    dependencies |= set(pkg.dependencies)
                if len(pkg.recommends):
                    dependencies |= set(pkg.recommends)

                # reset buffer
                pkg_buffer = []
            else:
                pkg_buffer.append(line)
    
    for pkg in pkgs.values:
        pkg.resolve_dependencies(pkgs)

    return pkgs, dependencies

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

    pkgs, dependencies = parse_packages(dpkg_status)

    # print what should be user-installed packages
    for pkg in pkgs.values:
        if (
            not pkg.essential
            and pkg.priority != "required"
            and pkg.source == ""
        ):
            if args.disable_dependency_checking:
                print(pkg.name)
            else:
                if pkg.name not in dependencies:
                    print(pkg.name)
