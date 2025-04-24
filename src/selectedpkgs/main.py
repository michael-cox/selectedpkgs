from pathlib import Path

dpkg_status = Path("/var/lib/dpkg/status")

class Package:
    def __init__(self, name, essential=False):
        self.name = name
        self.essential = essential
    
    def __repr__(self):
        return str(self.__dict__)

    @classmethod
    def from_pkg_buffer(cls, pkg_buffer):
        props = buffer_to_props(pkg_buffer)

        return cls(props.get("Package"), props.get("Essential", False))

def buffer_to_props(buffer):
    props = {}
    for line in buffer:
        split_line = line.split(": ")
        if len(split_line) > 1:
            props[split_line[0]] = split_line[1:]
    return props

def parse_packages(file_path, delimiter='\n'):
    pkg_buffer = []
    with open(file_path, "r") as f:
        for line in f:
            if line == delimiter:
                yield Package.from_pkg_buffer(pkg_buffer)
                pkg_buffer = []
            else:
                pkg_buffer.append(line)

def main():
    if not dpkg_status.exists():
        # error here
        print(f"{dpkg_status} doesn't exist")
        return

    for pkg in parse_packages(dpkg_status): print(pkg)