"""Unified ``dissect`` command line entry point.

This module provides a single ``dissect`` command that dispatches to the various command line tools that ship with the
dissect suite of packages. For example::

    dissect shell <target>          ->  target-shell <target>
    dissect dd <target>             ->  target-dd <target>
    dissect dump-nskeyedarchiver …  ->  dump-nskeyedarchiver …

Subcommands are discovered dynamically from the installed ``console_scripts`` entry points that live in the ``dissect``
namespace, and are grouped in the help output by the package that provides them (e.g. ``target``, ``util``). Tools from
``dissect.target`` have their ``target-`` prefix stripped so they read as ``dissect <name>``.

The common case, ``dissect <command> [<args>...]``, is kept as lean as possible: it resolves and dispatches the single
requested tool without importing ``argparse``/``ast`` or building the (comparatively expensive) grouped help listing.
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    import argparse
    from collections.abc import Iterator
    from importlib.metadata import EntryPoint

# Namespace that identifies the dissect suite of packages.
NAMESPACE = "dissect"

# The flagship section whose tools get their ``<section>-`` prefix stripped for a shorter invocation.
FLAGSHIP = "target"


class Command(NamedTuple):
    section: str
    entry_point: EntryPoint


def _iter_commands() -> Iterator[tuple[str, str, EntryPoint]]:
    """Yield ``(name, section, entry_point)`` for every dissect suite console script.

    Only ``console_scripts`` that live in the ``dissect`` namespace are considered. The section is derived from the
    providing subpackage (e.g. ``dissect.target.tools.shell`` -> ``target``). For the flagship section the
    ``<section>-`` prefix is stripped from the script name so that, for example, ``target-shell`` becomes ``shell``.
    """
    # Imported lazily: this (relatively expensive) module is only needed for the metadata-based fallback and the help
    # listing, not for the common fast path.
    from importlib.metadata import entry_points

    for ep in entry_points(group="console_scripts"):
        parts = ep.value.partition(":")[0].split(".")

        # Skip anything outside the dissect namespace and our own entry point.
        if parts[0] != NAMESPACE or ep.name == NAMESPACE:
            continue

        section = parts[1] if len(parts) > 1 else "misc"

        name = ep.name
        if section == FLAGSHIP and name.startswith(f"{FLAGSHIP}-"):
            name = name[len(FLAGSHIP) + 1 :]

        yield name, section, ep


def _find_command(target: str) -> EntryPoint | None:
    """Return the entry point for a single subcommand, or ``None`` if it does not exist.

    This intentionally stops at the first match and avoids building the full command table so the common
    ``dissect <command>`` path stays fast.
    """
    for name, _, ep in _iter_commands():
        if name == target:
            return ep
    return None


def _resolve_sibling(command: str) -> tuple[str, str, str] | None:
    """Resolve a subcommand to ``(script, module, function)`` by reading its sibling console script.

    ``dissect`` is installed alongside the other console scripts (in the same directory as the interpreter), each of
    which is a tiny wrapper containing a ``from <module> import <function>`` line. Reading that directly lets the fast
    path dispatch without importing ``importlib.metadata`` (which is comparatively expensive). Returns ``None`` when
    the sibling can't be found or understood, so the caller can fall back to the metadata-based lookup.
    """
    # Reject anything that could escape the scripts directory; such a name is never a valid command anyway.
    if os.sep in command or (os.altsep and os.altsep in command):
        return None

    # Use os.path (already imported at interpreter start) rather than pathlib, whose import would add startup cost and
    # defeat the purpose of this fast path.
    bindir = os.path.dirname(sys.executable)  # noqa: PTH120

    # The flagship candidate (target-<command>) takes precedence over a literal match, mirroring the naming rules.
    for script in (f"{FLAGSHIP}-{command}", command):
        resolved = _read_console_script(os.path.join(bindir, script))  # noqa: PTH118
        if resolved is not None:
            return (script, *resolved)

    return None


def _read_console_script(path: str) -> tuple[str, str] | None:
    """Extract ``(module, function)`` from a generated console script's ``from <module> import <function>`` line."""
    try:
        with open(path, encoding="utf-8") as fh:  # noqa: PTH123
            head = fh.read(4096)
    except OSError:
        return None

    for line in head.splitlines():
        if line.startswith("from ") and " import " in line:
            module, _, function = line[len("from ") :].partition(" import ")
            module, function = module.strip(), function.strip()
            if module.startswith(f"{NAMESPACE}.") and function.isidentifier():
                return module, function

    return None


def _dispatch_module(script: str, module: str, function: str, args: list[str]) -> int:
    """Import ``module``, call its ``function``, forwarding ``args`` to it verbatim."""
    # Rewrite argv so the dispatched tool sees itself as if invoked directly, e.g. `dissect shell foo` becomes
    # `target-shell foo`. The tool's own ArgumentParser then handles the remaining arguments (including -h/--help).
    sys.argv = [script, *args]

    func = getattr(__import__(module, fromlist=[function]), function)
    result = func()
    return result if isinstance(result, int) else 0


def _dispatch(ep: EntryPoint, args: list[str]) -> int:
    """Load and run the tool behind ``ep`` (metadata fallback), forwarding ``args`` to it verbatim."""
    module, _, function = ep.value.partition(":")
    return _dispatch_module(ep.name, module, function, args)


def _error(message: str) -> int:
    # The error path is rare, so we can afford argparse here to render a usage line consistent with (and colored like)
    # the rest of the help output, without building the full command listing.
    _build_parser(with_commands=False).error(message)
    return 2  # unreachable: parser.error() exits, but keeps the type checker and callers happy


def main() -> int:
    argv = sys.argv[1:]

    # Fast path: a subcommand was given directly. Resolve and dispatch it without importing importlib.metadata,
    # argparse or ast, or building the grouped help listing.
    if argv and not argv[0].startswith("-"):
        command, args = argv[0], argv[1:]

        resolved = _resolve_sibling(command)
        if resolved is not None:
            return _dispatch_module(*resolved, args)

        # Fall back to the metadata-based lookup when the sibling script can't be read (e.g. Windows .exe wrappers,
        # or scripts installed outside the interpreter's directory such as with `pip install --user`).
        ep = _find_command(command)
        if ep is not None:
            return _dispatch(ep, args)

        return _error(f"invalid command: {command!r} (see '{NAMESPACE} --help')")

    if not argv:
        return _error(f"a command is required (see '{NAMESPACE} --help')")

    # Slow path: an option such as -h/--help was given. Only now do we pull in argparse and build the full,
    # descriptive help output.
    _build_parser(with_commands=True).parse_args(argv)
    return 0


def _build_parser(*, with_commands: bool) -> argparse.ArgumentParser:
    """Build the top-level argument parser.

    ``<command>`` and ``<args>`` are declared as real arguments (rather than a hardcoded ``usage=`` string) so that
    argparse generates and colorizes the usage line itself. The (comparatively expensive) grouped command listing is
    only attached as the epilog when ``with_commands`` is set, i.e. for ``--help`` rather than error messages.
    """
    # argparse is imported here (not at module level) so the fast dispatch path stays lean.
    import argparse
    from importlib.metadata import PackageNotFoundError, version

    # On Python 3.14+ argparse colorizes usage/options by default (respecting can_colorize(): tty, NO_COLOR, ...); on
    # older versions there is no color support to enable.
    parser = argparse.ArgumentParser(
        prog=NAMESPACE,
        description="Unified entry point for the `dissect` suite of tools.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    try:
        dist_version = version(NAMESPACE)
    except PackageNotFoundError:
        # Running from a source checkout that isn't installed as a distribution.
        dist_version = "0+unknown"
    parser.add_argument("--version", action="version", version=f"%(prog)s {dist_version}")
    # nargs="*" (rather than REMAINDER) so the usage line renders as `<command> [<args> ...]`, consistent with the
    # `<args>` metavar shown in the positional listing. These arguments are only ever used to render usage/help; the
    # fast path resolves and dispatches the real command itself.
    parser.add_argument("command", metavar="<command>", help="the dissect command to run")
    parser.add_argument("args", metavar="<args>", nargs="*", help="arguments for the command")

    if with_commands:
        # `--help` lists only the flagship commands to keep it short; `--help-all` expands to every section.
        class HelpAllAction(argparse.Action):
            def __init__(self, option_strings: list[str], dest: str, **kwargs) -> None:
                super().__init__(option_strings, dest, nargs=0, default=argparse.SUPPRESS, **kwargs)

            def __call__(self, parser, namespace, values, option_string=None) -> None:  # noqa: ANN001
                parser.epilog = _format_commands(_commands())
                parser.print_help()
                parser.exit()

        parser.add_argument(
            "--help-all", action=HelpAllAction, help="show all commands, including non-target tools, and exit"
        )
        parser.epilog = _format_commands(_commands(), only={FLAGSHIP})

    return parser


def _commands() -> dict[str, Command]:
    """Return the full mapping of subcommand name to the command that implements it, sorted by name."""
    return dict(sorted((name, Command(section, ep)) for name, section, ep in _iter_commands()))


class _Theme(NamedTuple):
    heading: str = ""
    action: str = ""
    prog: str = ""
    long_option: str = ""
    reset: str = ""


def _theme() -> _Theme:
    """Return the ANSI codes argparse itself uses for help, or empty strings when color is unavailable/disabled.

    This mirrors argparse's own decision (Python 3.14+ ``_colorize``), so our hand-rendered epilog is colorized
    consistently with the rest of the help output. On older Pythons, or when color is disabled, it degrades to no-op
    strings.
    """
    try:
        from _colorize import can_colorize, get_theme
    except ImportError:
        return _Theme()

    if not can_colorize():
        return _Theme()

    t = get_theme(force_color=True).argparse
    return _Theme(
        heading=t.heading,
        action=t.action,
        prog=t.prog,
        long_option=t.long_option,
        reset=t.reset,
    )


def _format_commands(commands: dict[str, Command], *, only: set[str] | None = None) -> str:
    """Render the available commands grouped per section for the ``--help`` epilog.

    When ``only`` is given, just those sections are listed and a hint about ``--help-all`` is appended.
    """
    sections: dict[str, list[tuple[str, EntryPoint]]] = {}
    for name, command in commands.items():
        if only is not None and command.section not in only:
            continue
        sections.setdefault(command.section, []).append((name, command.entry_point))

    # Show the flagship section first, then the rest alphabetically.
    order = sorted(sections, key=lambda section: (section != FLAGSHIP, section))
    # Align the help column against only the names that are actually shown.
    width = max((len(name) for names in sections.values() for name, _ in names), default=0)

    theme = _theme()

    def item(name: str, ep: EntryPoint, indent: int) -> str:
        # Pad with plain spaces (ANSI codes have no display width) to keep the help column aligned.
        padding = " " * (width - len(name))
        return f"{' ' * indent}{theme.action}{name}{theme.reset}{padding}  {_describe(ep)}"

    lines = []
    for section in order:
        if lines:
            lines.append("")
        lines.append(f"{theme.heading}{section} commands:{theme.reset}")
        lines.extend(item(name, ep, 2) for name, ep in sorted(sections[section]))

    if only is not None:
        hint = f"{theme.prog}{NAMESPACE}{theme.reset} {theme.long_option}--help-all{theme.reset}"
        lines.append(f"\nrun '{hint}' to list all available commands")

    return "\n".join(lines)


def _describe(ep: EntryPoint) -> str:
    """Return a help string for a tool, using its module docstring's summary line.

    The docstring is extracted statically (without importing the tool, so there are no side effects and no dependency
    on the tool's runtime imports), and falls back to ``run <script>`` when no docstring is available.
    """
    # These are only needed for the help listing, so keep them out of the fast path.
    import ast
    import importlib.util

    fallback = f"run {ep.name}"

    module, _, _ = ep.value.partition(":")
    try:
        spec = importlib.util.find_spec(module)
        if not spec:
            return fallback
        source = open(spec.origin, encoding="utf-8").read()  # noqa: PTH123, SIM115
        tree = ast.parse(source)
    except (ImportError, OSError, SyntaxError, ValueError, AttributeError):
        return fallback

    docstring = ast.get_docstring(tree)
    if docstring and (summary := docstring.strip().splitlines()[0].strip()):
        return summary

    return fallback


if __name__ == "__main__":
    sys.exit(main())
