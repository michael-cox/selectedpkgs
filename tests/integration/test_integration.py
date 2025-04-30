import subprocess
import pytest
from pathlib import Path
from selectedpkgs.main import main

dpkg_status = Path("/var/lib/dpkg/status")
packages = ["vim", "curl", "cowsay", "tmux", "unzip"]
dependent_pkgs = ["lm-sensors", "htop"]


# install packages
@pytest.fixture(scope="module")
def install_packages():
    subprocess.run(["apt", "update"], check=True)
    subprocess.run(
        ["apt", "install", "-y"] + packages + dependent_pkgs, capture_output=True, text=True, check=True
    )


# test that selectedpkgs finds installed packages
@pytest.mark.skipif(not dpkg_status.is_file, reason="Requires Debian")
def test_regular_pkgs(install_packages, capsys):
    main(args=[])
    captured = capsys.readouterr()
    for pkg in packages:
        assert pkg in captured.out

@pytest.mark.skipif(not dpkg_status.is_file, reason="Requires Debian")
def test_deep_dependencies(install_packages, capsys):
    main(args=[])
    captured = capsys.readouterr()
    for pkg in dependent_pkgs:
        assert pkg in captured.out