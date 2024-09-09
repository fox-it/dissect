from __future__ import annotations

import argparse
import logging
import os
import subprocess
import urllib.request
from pathlib import Path

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

except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    log = logging.getLogger(__name__)


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
        print(res.stdout.decode("utf-8"))
        if res.stderr != b"":
            print(res.stderr.decode("utf-8"))
    return res


def main():
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

    if not args.do_not_upgrade_pip:
        log.info("Updating pip..")
        _run("pip install --upgrade pip", args.verbose)

    if args.online:
        args.file = PYPROJECT_ONLINE_URL
        log.info(f"The following url will be used to determine dependencies: {args.file}")
        try:
            input("Press ENTER to continue..")
        except KeyboardInterrupt:
            print()
            return

    pyproject = load_pyproject_toml(args.file)

    if not pyproject:
        log.error("No pyproject.toml found, exiting..")
        return

    modules = pyproject["project"]["dependencies"]
    log.info(f"Found {str(len(modules))} dependencies")

    for module in modules:
        pretty_module_name = module.split(">")[0].split("=")[0]
        log.info(f"Updating dependency {pretty_module_name}")
        # --pre does not do anything if pyproject.toml defines its dependencies strict like foo==1.0.0,
        # so this only affects loose custom dependency definitions with, e.g. foo>1.0.0,<2.0.0.
        # TODO: figure out if this is a git repository, then just git pull!
        _run(f"pip install '{module.strip(',')}' --upgrade --no-cache-dir --pre", args.verbose)

    log.info("Finished updating all dependencies!")

    if args.verbose:
        log.info("Currently installed dependencies listed below:")
        _run("pip freeze", args.verbose)


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

    log.error("No pyproject.toml files found to read dependencies from!")
