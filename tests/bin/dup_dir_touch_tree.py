#!/usr/bin/env python3
"""Copy a directory hierarchy by creating directories and touching files. """

from pathlib import Path

fake = Path("fake")
if fake.exists():
    fake.rmdir()
fake.mkdir()

found = [f for f in Path().cwd().rglob("*")]
for ff in found:
    if ff.is_dir():
        print("found dir", ff)
        print(str(fake / ff.relative_to(Path.cwd())))
        Path(fake / ff.relative_to(Path.cwd())).mkdir()
    elif ff.is_file():
        print("found file", ff.relative_to(Path.cwd()))
        Path(fake / ff.relative_to(Path.cwd())).touch()
