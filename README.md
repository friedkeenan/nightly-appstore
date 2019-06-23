# nightly-appstore
Manages a libget repo that automatically updates and builds packages.

### Usage
`repo_manager.py [clean]`

Giving `clean` as an argument will delete the `build`, `zips`, and `packages` directories, and the `repo.json` file.

Giving no arguments will start up the server and RepoManager (stored in the `m` variable) and then open up a console. To exit, press Ctrl+D and then Ctrl+C.

The server will be hosted with the hostname and port defined in `config.py` (see `config.py.template`).

### Scripts
Scripts should go in the `scripts` directory and have the `.py` extension (because they're python code, silly). They should have a class in them with the same name as the file (without the extension) that inherits from `PackageBuilder` or one of its subclasses (like `NightlyHomebrew`). They will be run as if they're in the same directory as `repo_manager.py`.

Check `builder.py` for more details and the `scripts` directory for some examples.

### Icons
Icons should go in `icons/<script name>/`. hb-appstore will look for an `icon.png`, which shows when browsing apps, and a `screen.png` file, which shows when an app is selected.

### RepoManger
`manager.kill()` will stop the manager once its finished its current loop.

`manager.pause()` will pause the manager.  
`manager.unpause()` will unpause the manager.

`manager.rm_pkg(pkg_name)` will remove the package and move its script to `scripts.dis`.

`manager.reset_scripts()` will clear `manager.scripts`, causing the scripts to be reloaded.