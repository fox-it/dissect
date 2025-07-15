from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Iterator

from pip._vendor import tomli

try:
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S UTC", utc=True),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    )
    log = structlog.get_logger()
    HAS_STRUCTLOG = True

except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    log = logging.getLogger(__name__)
    HAS_STRUCTLOG = False


PYPROJECT_FILE_PATHS = [
    # wheels will have a toml file at dissect/update/pyproject.toml
    str(Path(os.path.realpath(__file__)).parent) + "/pyproject.toml",
    # tgz dist files will have a toml file at dissect/pyproject.toml
    str(Path(os.path.realpath(__file__)).parent.parent) + "/pyproject.toml",
    # git source repositories will have a toml file inside the repository root.
    str(Path(os.path.realpath(__file__)).parent.parent.parent) + "/pyproject.toml",
]

PYPROJECT_ONLINE_URL = os.getenv(
    "DISSECT_PYPROJECT_URL", "https://raw.githubusercontent.com/fox-it/dissect/main/pyproject.toml"
)


def _run(cmd: str, verbose: int) -> subprocess.CompletedProcess:
    """Wrapper for subprocess run command."""
    res = subprocess.run(cmd, shell=True, capture_output=True)
    if verbose or res.returncode != 0:
        print(res.stdout.decode())
        if res.stderr != b"":
            log.error("Process returned stderr output:")
            print(res.stderr.decode("utf-8"))
    return res


def main():
    try:
        actual_main()
    except KeyboardInterrupt:
        print()
        return


def actual_main():
    help_formatter = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(
        description="Update your Dissect installation.",
        fromfile_prefix_chars="@",
        formatter_class=help_formatter,
    )
    parser.add_argument("-u", "--do-not-upgrade-pip", action="store_true", help="do not upgrade pip", default=False)
    parser.add_argument("-o", "--online", action="store_true", help="use the latest pyproject.toml from GitHub.com")
    parser.add_argument("-f", "--file", default=False, action="store", help="path to a custom pyproject.toml file")
    parser.add_argument("-v", "--verbose", action="store_true", help="show output of pip", default=False)
    args = parser.parse_args()

    if args.verbose:
        if HAS_STRUCTLOG:
            structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG))
        else:
            logging.getLogger().setLevel(logging.DEBUG)

    # By default we want to ensure we have the latest pip version since outdated pip
    # versions can be troublesome with dependency version resolving and matching.
    if not args.do_not_upgrade_pip:
        log.info("Updating pip..")
        _run(f"{sys.executable} -m pip install --upgrade pip", args.verbose)

    # We collect the current state of the installed modules so we can compare versions later.
    initial_modules = environment_modules(args.verbose)

    # If the user requested an online pyproject.toml update we mis-use the args.file flag
    # and ask the user to confirm the URL for safety since we use dependency module names
    # from that file inside subprocess.run calls.
    if args.online:
        args.file = PYPROJECT_ONLINE_URL
        log.info(f"The following url will be used to determine dependencies: {args.file}")
        try:
            input("Press ENTER to continue..")
        except KeyboardInterrupt:
            print()
            return

    # We attempt to obtain our dependencies from a pyproject.toml file.
    pyproject = load_pyproject_toml(args.file)

    # We check if the current environment has any git editable install locations.
    editable_installs = list(find_editable_installs(args.verbose))

    if not pyproject and not editable_installs:
        log.error("No pyproject.toml or editable installs found, exiting..")
        return

    if pyproject:
        modules = pyproject["project"]["dependencies"]
        log.info(f"Found {str(len(modules))} dependencies")

        for module in modules:
            pretty_module_name = module.split(">")[0].split("=")[0]

            # If this module is also in the editable installs we found we skip them here.
            if pretty_module_name in [m.get("name") for m in editable_installs]:
                log.debug(f"Not updating module {pretty_module_name} as it is installed as editable")
                continue

            log.info(f"Updating dependency using pip: {pretty_module_name}")
            # --pre does not do anything if pyproject.toml defines its dependencies strict like foo==1.0.0,
            # so this only affects loose custom dependency definitions with, e.g. foo>1.0.0,<2.0.0.
            _run(f"{sys.executable} -m pip install '{module.strip(',')}' --upgrade --no-cache-dir --pre", args.verbose)

    if editable_installs:
        log.info(f"Found {str(len(editable_installs))} editable installs in current environment")

        for module in editable_installs:
            module_name = module.get("name")
            module_path = module.get("editable_project_location")
            log.info(f"Updating local dependency: {module_name} @ {module_path}")
            # We assume that this is a git repository and we have git available to us.
            _run(f"cd {module_path} && git pull && {sys.executable} -m pip install -e .", args.verbose)

    log.info("Finished updating dependencies")

    # Display the version differences between the dependencies.
    current_modules = environment_modules(args.verbose)
    if initial_modules and current_modules:
        for module in current_modules:
            previous_module = next(filter(lambda prev_module: prev_module["name"] == module["name"], initial_modules))
            module_name = module.get("name")
            previous_version = previous_module.get("version")
            current_version = module.get("version")

            if previous_version != current_version:
                print(f"{module_name} \x1b[31m{previous_version}\x1b[0m -> \x1b[32m\x1b[1m{current_version}\x1b[0m")

    if args.verbose:
        log.info("Currently installed dependencies listed below:")
        _run(f"{sys.executable} -m pip freeze", args.verbose)


def load_pyproject_toml(custom_path: str | None) -> dict | None:
    """Attempt to load a pyproject.toml file and return the parsed dictionary."""

    if custom_path:
        log.info(f"Using {custom_path} as pyproject.toml source.")
        path = Path(custom_path)

        if path.exists():
            with open(custom_path, mode="rb") as f:
                return tomli.load(f)

        elif custom_path.startswith("https://"):
            try:
                content = urllib.request.urlopen(custom_path).read().decode()
                return tomli.loads(content)
            except Exception as e:
                log.error(f"Unable to fetch {custom_path}: {str(e)}")
                return

    for toml_file in PYPROJECT_FILE_PATHS:
        try:
            with open(toml_file, mode="rb") as f:
                log.info(f"Found file {toml_file} to read dependencies from.")
                return tomli.load(f)
        except FileNotFoundError:
            log.debug(f"File {toml_file} not found!")
            continue

    log.error("No pyproject.toml files found to read dependencies from! Consider using --file or --online")


def environment_modules(verbose: bool) -> list[dict] | None:
    """Wrapper around pip list command."""

    try:
        modules = json.loads(_run(f"{sys.executable} -m pip list --format=json", verbose).stdout.decode())
        return modules

    except Exception as e:
        log.error("Failed to parse current environment using pip!")
        log.debug("", exc_info=e)
        return


def find_editable_installs(verbose: bool) -> Iterator[dict] | None:
    """Attempt to find editable installs in the current environment."""

    modules = environment_modules(verbose)

    if not modules:
        return

    for module in modules:
        if module.get("editable_project_location"):
            yield module
