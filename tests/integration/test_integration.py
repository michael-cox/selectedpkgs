import subprocess
import pytest
from pathlib import Path
from selectedpkgs.main import main

dpkg_status = Path("/var/lib/dpkg/status")
packages = ['vim', 'curl', 'cowsay', 'tmux', 'unzip']

@pytest.fixture(scope="module")
def install_packages():
    subprocess.run(['apt', 'update'], check=True)
    subprocess.run(['apt', 'install', '-y'] + packages, capture_output=True, text=True, check=True)

@pytest.mark.skipif(not dpkg_status.is_file, reason="Requires Debian")
def test_selectedpkgs(install_packages, capsys):
    main(args=[])
    captured = capsys.readouterr()
    for pkg in packages:
        assert pkg in captured.out