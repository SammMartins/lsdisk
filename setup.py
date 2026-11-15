from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.sdist import sdist


class CleanSdist(sdist):
    """Keep setuptools' generated egg-info out of the source archive.

    Setuptools generates this directory while preparing an sdist, after the
    manifest has been evaluated.  Removing it here preserves the required
    root PKG-INFO while excluding generated SOURCES.txt and other egg-info
    files from the archive.
    """

    def make_release_tree(self, base_dir, files):
        super().make_release_tree(base_dir, files)
        egg_info = Path(base_dir) / "src" / "lsdisk.egg-info"
        if egg_info.exists():
            shutil.rmtree(egg_info)


setup(cmdclass={"sdist": CleanSdist})
