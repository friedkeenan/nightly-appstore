import json
import os
import shutil
import zipfile
import git
import subprocess
import hashlib
import math
import threading
from pathlib import Path

def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except (TypeError, OverflowError):
        return False

def _lock(func):
    """
    This should decorate at least
    should_update, update, prepare_pkg,
    and create_pkg.
    Beware that decorators don't pass on
    when overriding methods.
    """
    def wrapper(self, *args, **kwargs):
        self.lock.acquire()
        r = func(self, *args, **kwargs)
        self.lock.release()
        return r
    return wrapper

class PackageBuilder:
    # Note that all of these can be overriden by property methods
    title = "n/a"
    author = "n/a"
    category = "n/a"
    version = "n/a"
    description = "n/a"
    details = "n/a"
    url = "n/a"
    license = "n/a"

    # Attributes in here won't be returned in the info property
    _blacklisted_attrs = [
        "info",
        "name",
        "cwd",
        "pkg_files"
    ]

    def __init__(self):
        self.lock = threading.Lock()


    @_lock
    def should_update(self):
        raise NotImplementedError

    @_lock
    def update(self):
        """
        Should get the final binaries for the package,
        whether that be building from source
        or downloading precompiled binaries.
        """
        raise NotImplementedError

    @property
    def pkg_files(self):
        """
        Should return a dictionary with the keys being
        paths from self.cwd to the files to be packages,
        and the values being the path where those files
        should be within the package.
        Ex:
        {"application/application.nro": "switch/application/application.nro"}

        If the key is "_touch" then its value should be
        a list of empty files to create.
        """
        raise NotImplementedError

    @_lock
    def prepare_pkg(self):
        files = self.pkg_files

        if len(files) < 1:
            return

        if not Path(self.cwd, "tmp").exists():
            os.mkdir(Path(self.cwd, "tmp"))

        total_size = 0

        manifest_path = Path(self.cwd, "tmp", "manifest.install")
        with manifest_path.open("w") as f:
            for file in files:
                if file == "_touch":
                    for f in files["_touch"]:
                        touch = Path(self.cwd, "tmp", f)
                        if not touch.parent.exists():
                            os.makedirs(touch.parent)
                        touch.open("a").close()
                    continue

                dst = Path(self.cwd, "tmp", files[file])
                if not dst.parent.exists():
                    os.makedirs(dst.parent)

                src = Path(self.cwd, file)

                if not src.exists():
                    raise FileNotFoundError(str(src))

                if src.is_dir():
                    shutil.copytree(src, dst)
                    for root, dirs, files in os.walk(dst):
                        total_size += Path(root, files).stat().st_size
                else:
                    shutil.copy2(src, dst)
                    total_size += dst.stat().st_size

                f.write(f"U: {files[file]}")
        total_size += manifest_path.stat().st_size

        info_path = Path(self.cwd, "tmp", "info.json")
        with info_path.open("w") as f:
            json.dump(self.info, f, indent=4, sort_keys=True)
        total_size += info_path.stat().st_size

        return math.ceil(total_size/1024)

    @_lock
    def create_pkg(self):
        if not os.path.exists("zips"):
            os.mkdir("zips")

        zip_path = Path("zips", f"{self.name}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            folder = Path(self.cwd, "tmp")
            for root, dirs, files in os.walk(folder):
                for file in files:
                    path = Path(root, file)
                    z.write(path, path.relative_to(folder))

        shutil.rmtree(Path(self.cwd, "tmp"))

        with zip_path.open("rb") as f:
            md5sum = hashlib.md5(f.read()).hexdigest()

        return (math.ceil(zip_path.stat().st_size/1024), md5sum)

    @property
    def info(self):
        return {x:getattr(self, x) for x in dir(self) if x not in self._blacklisted_attrs and not x.startswith("_") and is_jsonable(getattr(self, x))}

    @property
    def name(self):
        return type(self).__name__

    @property
    def cwd(self):
        return Path("build", self.name)

class NightlyPackage(PackageBuilder):
    def __init__(self):
        super().__init__()

        repo_dir = Path(self.cwd, self.name)
        try:
            self._repo = git.Repo(repo_dir)
        except git.exc.InvalidGitRepositoryError:
            shutil.rmtree(repo_dir)
            self._repo = git.Repo.clone_from(self.url, repo_dir, recursive=True)
        except git.exc.NoSuchPathError:
            self._repo = git.Repo.clone_from(self.url, repo_dir, recursive=True)

        if not os.path.exists(Path(self._repo.git_dir, "FETCH_HEAD")):
            self._repo.remotes.origin.fetch()

    @_lock
    def should_update(self):
        if not Path(self.cwd, ".first_update").exists():
            return True

        info = self._repo.remotes.origin.fetch(dry_run=True)
        for i in info:
            if not i.flags & i.HEAD_UPTODATE:
                return True
        return False

    @_lock
    def update(self):
        self._repo.remotes.origin.pull()

        try:
            self.build()
        except ValueError as e:
            print(f"Building {self.name} failed:", e)
        
        Path(self.cwd, ".first_update").open("a").close()

    def build(self):
        """
        Should build the binaries from the source code
        """
        raise NotImplementedError

    @property
    def version(self):
        ver = self._repo.head.reference.commit.hexsha
        ver = ver[:7]
        if self._repo.is_dirty():
            ver += "-dirty"
        return ver

    @property
    def name(self):
        return self.url.split("/")[-1]
    

class NightlyHomebrew(NightlyPackage):
    pkg_files = {}

    _makefile = "Makefile"
    _make_args = ""

    def __init__(self):
        super().__init__()

        target = self.get_make_var("TARGET")
        if target == "$(notdir $(CURDIR))":
            target = Path(self._repo.working_tree_dir).name

        for f in os.listdir(self._repo.working_tree_dir):
            if f == f"{target}.json" or f == "config.json":
                self._npdm_json = f
                break
        else: # Didn't break so the final binary is an NRO
            self._npdm_json = None

        if not isinstance(type(self).pkg_files, property):
            if len(self.pkg_files) < 1:
                output = self.get_make_var("OUTPUT")
                output = output.replace("$(CURDIR)", Path(self._repo.working_tree_dir).name)
                output = output.replace("$(TARGET)", target)

                if self._npdm_json is None:
                    self.pkg_files = {f"{output}.nro": f"switch/{self.name}/{self.name}.nro"}
                else:
                    with Path(self._repo.working_tree_dir, self._npdm_json).open() as f:
                        cont = json.load(f)
                        title_id = cont["title_id"][2:]
                        self.pkg_files = {
                            f"{output}.nsp": f"atmosphere/titles/{title_id}/exefs.nsp",
                            "_touch": [f"atmosphere/titles/{title_id}/flags/boot2.flag"]
                        }
            else: # Keys in pkg_files should be relative to the repo directory
                files = self.pkg_files
                self.pkg_files = {Path(Path(self._repo.working_tree_dir).relative_to(self.cwd.absolute()), x):files[x] for x in files}

    def get_make_var(self, var, makefile=None):
        if makefile is None:
            makefile = self._makefile

        with Path(self._repo.working_tree_dir, makefile).open() as f:
            for line in f.readlines():
                if var in line and ":=" in line:
                    return line.split(":=", 1)[1].strip()

    def build(self):
        with subprocess.Popen(["make", "-C", self._repo.working_tree_dir, "-f", self._makefile] + self._make_args.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as p:
            p.wait()
            if p.poll() != 0:
                raise ValueError(f"make returned a non-zero result: {p.poll()}")

    @property
    def author(self):
        auth = self.get_make_var("APP_AUTHOR")
        if auth is None:
            return super().author
        return auth

    @property
    def title(self):
        title = self.get_make_var("APP_TITLE")
        if title is None:
            return super().title
        return title