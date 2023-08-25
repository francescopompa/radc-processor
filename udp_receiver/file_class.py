"""
Class class TargetFiles() taking care of file management and overwrite-checks in
assistance for the UDP-Receiver Receiver()-class.
"""

# import os
import copy
import os.path as pa
from pathlib import Path

class TargetFiles():
    """
    Class TargetFiles()

    Returns an object able to proceed most checks needed by the class
    Receiver(). The full path is built as follows:

        /root_path/ dir/ name . ext

    where name is made of

        basename {_readout|_results} .number

    and ext is made of

        {.chunk .number|.wfm .number|.bin|.json}
    """

    ftype_strings = {
        "full": ("readout", "bin"),
        "chunk": ("chunk", "bin"),
        "split": ("wfm", "bin"),
        "results": ("results", "json"),
    }
    numbered_ftypes = ["chunk", "split"]

    _iterations = []
    """
    List of TargetFiles created during this execution.
    For now, this stores a new copy of the class instance each time it
    succesfully adopted a new target path (or it's first).
    This may cause unnecessary memory-usage on the long term or when
    using splitting.
    Over time, it may be judicious to switch to the string-representations
    of the paths, as returned by list_files() instead.
    """

    # @property
    @classmethod
    def list_files(cls):
        """List of file-paths created during this execution."""
        return [i.filepath for i in cls._iterations]


    def __init__(
            self,
            root_path: str,
            basename: str="",
            fdir: str="",
            ftype: str="full",   # full, chunk, split, results
            number: int=1,
            number_padding_length: int=4,
            version: int=1,
            version_padding_length: int=2,
            allow_overwrite: bool=False,
            ) -> None:

        self._number_padding_length = number_padding_length
        self._version_padding_length = version_padding_length
        self.allow_overwrite = allow_overwrite

        filename = self._init_path(Path(root_path), Path(fdir))

        self._init_name(
            basename, ftype,
            number,
            version,
            filename
            )



    def __repr__(self):
        return (
            f"{self.__class__.__name__}(root_path={self.root_path},"
            f"basename=\"{self.basename}\","
            # f"ext={self.ext},"
            f"fdir=\"{self.fdir}\","
            f"ftype=\"{self.ftype}\","
            f"number={self.number},"
            f"number_padding_length={self._number_padding_length},"
            f"version={self.version},"
            f"version_padding_length={self._version_padding_length},"
            f"allow_overwrite={self.allow_overwrite}"
            ")"
            )

    def __str__(self):
        return str(self.filepath)

    def _init_path(self, root_path: Path, fdir: Path):
        filename = None
        root_path.resolve() # make absolute, uses cwd if empty string

        if root_path.suffix != "" or root_path.is_file():
            # root_path includes target file -> split
            filename = root_path.name
            root_path = root_path.parent

        if fdir == fdir.parent:
            # fdir is empty -> get from root_path (never ends with /)
            fdir = root_path.name
            root_path = root_path.parent

        self.root_path = root_path
        self.fdir = fdir
        return filename

    def _init_name(self,
            basename, ftype,
            number,
            version,
            filename=None,
            make_duplicate=True,
            ):

        if filename is not None and basename == "":
            basename = filename
        elif filename is not None:
            raise ValueError(f"Specified both filename {filename} and basename {basename}")
        if basename == "":
            basename = "radc_receiver"

        parts = basename.split('.')
        n_fragments = 4 if ftype in self.numbered_ftypes else 3
        last_n_parts = parts[-n_fragments:] # use last three or four fragments
        remaining_parts = parts[:-n_fragments]
        spec, ext = self.ftype_strings[ftype]

        def set_name(p):
            nonlocal basename#, parts
            words = p.rstrip('_').split('_')
            # if words[-1] in [s[0] for s in ftype_strings.values()]
            if words[-1] == spec:
                words.pop(-1)
            basename = "_".join(words)

        def set_version(p):
            nonlocal version, remaining_parts
            if p.isdecimal():
                version = int(p)
            else:
                remaining_parts.append(p)

        def set_number(p):
            nonlocal number, remaining_parts
            if p.isdecimal():
                number = int(p)
            else:
                remaining_parts.append(p)

        def set_ext(p):
            nonlocal ext, remaining_parts
            if p != ext:
                remaining_parts.append(p)

        if n_fragments == 3:
            gen = iter((set_name, set_version, set_ext))
        elif n_fragments == 4:
            gen = iter((set_name, set_version, set_number, set_ext))

        for p in last_n_parts:
            func = next(gen)
            func(p)

        if ext in remaining_parts:
            remaining_parts.remove(ext) # remove extension in case basename had
                                        # less than n_fragments elements
        self.basename = ".".join(remaining_parts) + basename + "_" + spec
        self.version = version
        self.number = number
        self.ext = ext
        self.ftype = ftype

        self._check_overwrite(make_duplicate)

    def _re_init_name(self,
            basename=None, ftype=None,
            number=None,
            version=None,
            # filename=None,
            make_duplicate=False,
            ):

        self._init_name(basename or self.basename,
                        ftype or self.ftype,
                        number or self.number,
                        version or self.version,
                        # filename or self.filename,
                        make_duplicate=make_duplicate)

    @property
    def filedir(self):
        """Path to the parent folder of the targetted files."""
        return Path(self.root_path, self.fdir)

    @property
    def filepath(self):
        """Full path of the currently targetted file."""
        return Path(self.root_path, self.fdir, self.filename)

    @property
    def filename(self):
        """Full name of the currently targetted file."""
        if self.ftype in self.numbered_ftypes:
            return '.'.join([
                self.basename,
                f"{self.version:0{self._version_padding_length}}",  # 0 pad
                f"{self.number:0{self._number_padding_length}}",    # 0 pad
                self.ext
            ])
        else:
            return '.'.join([
                self.basename,
                f"{self.version:0{self._version_padding_length}}",  # 0 pad
                self.ext
            ])


    def _check_overwrite(self, make_duplicate=True):
        """If needed, increment file version to avoid overwrite."""
        if self.filepath.exists() and not self.allow_overwrite:
            # version += 1
            self.version += 1
            self._check_overwrite(make_duplicate)
        elif make_duplicate is True:
            self._iterations.append(copy.copy(self))
        else:
            self._iterations.append(self)

    def _reset(self, version=1, number=1):
        """
        Reset number and version values.
        """
        self.version = version
        self.number = number
        return version, number

    def lowest_safe(self, start=None):
        """Increment chunk of split number to next lowest safe number"""
        if start is None:
            start = self.number
        else:
            self.number = start

        while self.filepath.exists():
            self.number +=1
        self._check_overwrite()

    def next(self):
        """Increment chunk or split number"""
        if self.ftype not in self.numbered_ftypes:
            return
        self.number += 1
        self._check_overwrite()

    def switch(self,
            filename=None,
            number=None, version=None, reset=False,
            ftype=None
            ):
        """Switch to a new basename inside the same directory."""

        if reset is True:
            self._reset()

        self._init_name(
            filename or self.basename.rstrip("_"+self.ftype_strings[self.ftype][0]),
            ftype or self.ftype,
            number or self.number,
            version or self.version,
            )

    def generate(self, **kwargs):
        """
        Return a new path, but don't use it as current path.
        Example: to dump results.
        """
        new = copy.copy(self)
        for key, val in kwargs.items():
            if hasattr(new, key):
               setattr(new, key, val) #getattr(self, key))
        new._re_init_name(make_duplicate=False)
        # new._check_overwrite(make_duplicate=False)  # Don't append a COPY of new
        # # self._iterations.append(new)              # but append new itself.
        return new




class Test():
    instances = []

    @property
    def numbers(self):
        return [i.number for i in self.instances]

    def __init__(self, name="a", number=0):
        self.name = name
        self.number = number
        self.increase()

    def increase(self):
        if self.number % 3 != 0:
            self.number += 1
            self.increase()
        else:
            self.instances.append(copy.copy(self))
