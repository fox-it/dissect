"""Unified ``dissect`` command line entry point.

This module provides a single ``dissect`` command that dispatches to the various ``target-*`` tools that ship with
``dissect.target`` (and any other installed dissect distribution). For example::

    dissect shell <target>      ->  target-shell <target>
    dissect dd <target>         ->  target-dd <target>

Subcommands are discovered dynamically from the installed ``console_scripts`` entry points, so any tool named
``target-<name>`` automatically becomes available as ``dissect <name>``.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint

PREFIX = "target-"


def _discover_commands() -> dict[str, EntryPoint]:
    """Return a mapping of subcommand name to its console_script entry point."""
    commands = {}
    for ep in entry_points(group="console_scripts"):
        if ep.name.startswith(PREFIX):
            name = ep.name[len(PREFIX) :]
            commands[name] = ep
    return dict(sorted(commands.items()))


def _describe(ep: EntryPoint) -> str:
    """Return a help string for a tool, using its module docstring's summary line.

    The docstring is extracted statically (without importing the tool, so there are no side effects and no dependency
    on the tool's runtime imports), and falls back to ``run <script>`` when no docstring is available.
    """
    fallback = f"run {ep.name}"

    module = ep.value.partition(":")[0]
    try:
        spec = importlib.util.find_spec(module)
        source = open(spec.origin, encoding="utf-8").read()  # noqa: PTH123, SIM115
        tree = ast.parse(source)
    except (ImportError, OSError, SyntaxError, ValueError, AttributeError):
        return fallback

    docstring = ast.get_docstring(tree)
    if docstring and (summary := docstring.strip().splitlines()[0].strip()):
        return summary

    return fallback


def build_parser(commands: dict[str, EntryPoint]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dissect",
        description="Unified entry point for the dissect target-* tools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>", required=True)

    for name, ep in commands.items():
        subparser = subparsers.add_parser(
            name,
            help=_describe(ep),
            add_help=False,
            prog=f"dissect {name}",
        )
        # Forward everything after the subcommand to the underlying tool, including its own -h/--help.
        subparser.add_argument("args", nargs=argparse.REMAINDER, metavar="...")
        subparser.set_defaults(entry_point=ep)

    return parser


def main() -> int:
    commands = _discover_commands()
    parser = build_parser(commands)

    argv = sys.argv[1:]

    # Locate the command: the first argument that names a known subcommand. Everything after it is forwarded to the
    # underlying tool verbatim, so that the tool's own ArgumentParser handles its options (including -h/--help). This
    # also sidesteps the argparse.REMAINDER bug that drops a leading option.
    split = next((i for i, tok in enumerate(argv) if tok in commands), None)

    if split is None:
        # No command given: let argparse render help or the appropriate error.
        parser.parse_args(argv)
        return 2

    head, command, tool_args = argv[:split], argv[split], argv[split + 1 :]

    # Validate anything before the command (only -h/--help is defined here).
    parser.parse_args([*head, command])

    ep = commands[command]
    func = ep.load()

    # Rewrite argv so the dispatched tool sees itself as if invoked directly, e.g. `dissect shell foo` becomes
    # `target-shell foo`.
    sys.argv = [ep.name, *tool_args]

    result = func()
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
