#!/usr/bin/env python3

import threading
import datetime as dt
import json
import shutil
import os
import code
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

class RepoManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.alive = False

        self.scripts = {}

        self.repo_json_lock = threading.Lock()
        self.pause_lock = threading.Lock()

    def run(self):
        self.alive = True
        while self.alive:
            threading.Event().wait(timeout=1)

            self.pause_lock.acquire()

            new_script_files = {Path("scripts", x) for x in os.listdir("scripts") if x.endswith(".py")}
            old_script_files = {Path("scripts", f"{x}.py") for x in self.scripts.keys()}
            for s in old_script_files ^ new_script_files:
                name = s.name[:-3]

                if s in new_script_files:
                    print(f"Adding script: {name}")

                    loc = {}
                    with open(s) as f:
                        exec(f.read(), {}, loc)

                    if name not in loc:
                        raise ValueError("Scripts must have a builder in them with the same name as their filename without the extension")

                    self.scripts[name] = loc[name]()

                    try:
                        if not Path("packages").exists():
                            os.mkdir("packages")

                        icons_path = Path("icons", name).absolute()
                        dst_path = Path("packages", self.scripts[name].name)
                        if icons_path.exists():
                            os.symlink(icons_path, dst_path)
                        else:
                            os.symlink(Path("icons", "default").absolute(), dst_path)
                    except (FileNotFoundError, FileExistsError):
                        pass

                    print("Done.")
                else:
                    try:
                        os.remove(Path("packages", self.scripts[name].name))
                    except FileNotFoundError:
                        pass

                    self.scripts.pop(name)
                    print(f"Removed script: {name}")

            for name in self.scripts:
                script = self.scripts[name]

                if script.should_update():
                    print("Updating package:", script.name)

                    try:
                        script.update()
                    except Exception as e:
                        print(f"Updating {script.name} failed:", e)
                        continue

                    pkg_info = script.info

                    pkg_info["extracted"] = script.prepare_pkg()
                    pkg_info["filesize"], pkg_info["md5"] = script.create_pkg()

                    pkg_info["name"] = script.name
                    pkg_info["updated"] = dt.datetime.now().strftime("%d/%m/%Y")

                    self.repo_json_lock.acquire()
                    try:
                        with open("repo.json") as f:
                            repo_json = json.load(f)
                    except FileNotFoundError:
                        repo_json = {"packages": []}

                    for i in range(len(repo_json["packages"])):
                        if repo_json["packages"][i]["name"] == script.name:
                            repo_json["packages"].pop(i)
                            repo_json["packages"].append(pkg_info)
                            break
                    else:
                        repo_json["packages"].append(pkg_info)

                    with open("repo.json", "w") as f:
                        json.dump(repo_json, f, indent=4, sort_keys=True)

                    self.repo_json_lock.release()
                    print("Done.")

            self.pause_lock.release()

    def kill(self):
        self.alive = False

    def pause(self, paused=True):
        if paused:
            self.pause_lock.acquire()
        else:
            self.pause_lock.release()
    unpause = lambda s:s.pause(False)

    def rm_pkg(self, pkg_name):
        self.pause()

        for name in self.scripts:
            script = self.scripts[name]
            if script.name == pkg_name:
                try:
                    script.lock.acquire()

                    dis_path = Path("scripts.dis", f"{name}.py")
                    if not dis_path.parent.exists():
                        os.makedirs(dis_path.parent)
                    os.rename(Path("scripts", dis_path.name), dis_path)

                    shutil.rmtree(script.cwd)
                    os.remove(Path("zips", f"{script.name}.zip"))

                    script.lock.release()

                    self.repo_json_lock.acquire()
                    with open("repo.json", "r") as f:
                        repo_json = json.load(f)

                    for i in range(len(repo_json["packages"])):
                        if repo_json["packages"][i]["name"] == script.name:
                            repo_json["packages"].pop(i)
                            break

                    with open("repo.json", "w") as f:
                        json.dump(repo_json, f, indent=4, sort_keys=True)
                    self.repo_json_lock.release()
                except FileNotFoundError:
                    pass

                break
        else:
            self.unpause()
            raise ValueError("There is no package by that name")

        self.unpause()

    def reset_scripts(self):
        self.pause()
        self.scripts.clear()
        self.unpause()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clean":
        for d in ("build", "zips", "packages", "repo.json"):
            path = Path(d)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    os.remove(path)
    else:
        from config import *

        server = ThreadingHTTPServer((hostname, port), SimpleHTTPRequestHandler)
        server_thread = threading.Thread(target=server.serve_forever)

        m = RepoManager()

        m.start()
        server_thread.start()

        code.interact("", local=locals())

        server.server_close()
