import shutil
from collections import Iterable
from os import stat_result
from pathlib import PosixPath


class CachedPath(PosixPath):
    def get_cached(self, prop):
        name = f"__cached__{prop}"
        if hasattr(self, name):
            return getattr(self, name)
        else:
            baseclass_method = getattr(self.__class__.__base__, prop)
            value = baseclass_method(self)
            setattr(self, name, value)
            return value

    def stat(self) -> stat_result:
        return self.get_cached("stat")


class VirtualFileSystem:
    def __init__(self, method="symlink"):
        self.method = method
        self.mappings = {}

    def _add(self, src, dest_parent_dir, visited=None):
        if visited is None:
            visited = set()
        if src.is_symlink():
            src = src.resolve().absolute()
        dest = dest_parent_dir / src.name

        if src.is_file():
            self.mappings[CachedPath(dest)] = CachedPath(src)
        elif src.is_dir() and src not in visited:
            visited.add(src)
            for src_item in src.iterdir():
                self._add(src_item, dest, visited)
        else:
            # Skipping
            pass

    def copy(self, src, dest):
        if isinstance(src, Iterable):
            for x in src:
                self.copy(x, dest)
            return
        if type(src) is str:
            src = CachedPath(src)
        if type(dest) is str:
            dest = CachedPath(dest)
        if src.exists():
            self._add(src.resolve().absolute(), dest.resolve().absolute())

    def remove(self, filter_func):
        new_mappings = {}
        for dest, src in self.mappings.items():
            should_remove = filter_func(src, dest)
            if not should_remove:
                new_mappings[dest] = src

        self.mappings = new_mappings

    def sync(self):
        for dest, src in self.mappings.items():
            if dest.exists():
                if (
                    (dest.is_symlink() and dest.resolve() == src)
                    or (dest.stat().st_ino == src.stat().st_ino)
                    or (dest.stat().st_size == src.stat().st_size)
                ):
                    print("Skipping", str(dest))
                    continue
                # it exists, but isn't the same. Delete first.
                dest.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            if self.method == "symlink":
                dest.symlink_to(src)
            elif self.method == "hardlink":
                dest.link_to(src)
            else:
                shutil.copy2(str(src), str(dest))
