#!/bin/env python3

from pathlib import Path
import sys

basedir = Path(sys.argv[1])
mintime = int(sys.argv[2])

results=[]
def add(p):
    if not p.exists():
        return
    stats = p.stat()
    if mintime > stats.st_mtime:
        return
    p = p.relative_to(basedir)
    if p.is_symlink():
        results.append((p, p.absolute(), "", ""))
    else:
        results.append((p, "", stats.st_dev, stats.st_ino))


def rec(p):
    if p.is_dir() and not p.is_symlink():
        for item in sorted(p.iterdir()):
            rec(item)
    else:
        add(p)

rec(basedir)

for p, ref, dev, ino in results:
    print(f"{p}\t{ref}\t{dev}\t{ino}")
