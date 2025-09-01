# dissect

Dissect is a digital forensics & incident response framework and toolset that allows you to quickly access and analyse forensic artefacts from various disk and file formats, developed by Fox-IT (part of NCC Group).

This project is a meta package, it will install all other Dissect modules with the right combination of versions. For
more information, please see [the documentation](https://docs.dissect.tools/).

## What is Dissect?

Dissect is an incident response framework build from various parsers and implementations of file formats. Tying this all together, Dissect allows you to work with tools named `target-query` and `target-shell` to quickly gain access to forensic artefacts, such as Runkeys, Prefetch files, and Windows Event Logs, just to name a few!

**Singular approach**

And the best thing: all in a singular way, regardless of underlying container (E01, VMDK, QCoW), filesystem (NTFS, ExtFS, FFS), or Operating System (Windows, Linux, ESXi) structure / combination. You no longer have to bother extracting files from your forensic container, mount them (in case of VMDKs and such), retrieve the MFT, and parse it using a separate tool, to finally create a timeline to analyse. This is all handled under the hood by Dissect in a user-friendly manner.

If we take the example above, you can start analysing parsed MFT entries by just using a command like `target-query -f mft <PATH_TO_YOUR_IMAGE>`!

**Create a lightweight container using Acquire**

Dissect also provides you with a tool called `acquire`. You can deploy this tool on endpoint(s) to create a lightweight container of these machine(s). What is convenient as well, is that you can deploy `acquire` on a hypervisor to quickly create lightweight containers of all the (running) virtual machines on there! All without having to worry about file-locks. These lightweight containers can then be analysed using the tools like `target-query` and `target-shell`, but feel free to use other tools as well.

**A modular setup**

Dissect is made with a modular approach in mind. This means that each individual project can be used on its own (or in combination) to create a completely new tool for your engagement or future use!

**Try it out now!**

Interested in trying it out for yourself? You can simply `pip install dissect` and start using the `target-*` tooling right away. Or you can use the interactive playground at https://try.dissect.tools to try Dissect in your browser.

Don’t know where to start? Check out the [introduction page](https://docs.dissect.tools/en/latest/usage/introduction.html).

Want to get a detailed overview? Check out the [overview page](https://docs.dissect.tools/en/latest/overview/).

Want to read everything? Check out the [documentation](https://docs.dissect.tools).

## Projects

Dissect currently consists of the following projects.

- [dissect.archive](https://github.com/fox-it/dissect.archive)
- [dissect.btrfs](https://github.com/fox-it/dissect.btrfs)
- [dissect.cim](https://github.com/fox-it/dissect.cim)
- [dissect.clfs](https://github.com/fox-it/dissect.clfs)
- [dissect.cramfs](https://github.com/fox-it/dissect.cramfs)
- [dissect.cstruct](https://github.com/fox-it/dissect.cstruct)
- [dissect.esedb](https://github.com/fox-it/dissect.esedb)
- [dissect.etl](https://github.com/fox-it/dissect.etl)
- [dissect.eventlog](https://github.com/fox-it/dissect.eventlog)
- [dissect.evidence](https://github.com/fox-it/dissect.evidence)
- [dissect.executable](https://github.com/fox-it/dissect.executable)
- [dissect.extfs](https://github.com/fox-it/dissect.extfs)
- [dissect.fat](https://github.com/fox-it/dissect.fat)
- [dissect.ffs](https://github.com/fox-it/dissect.ffs)
- [dissect.fve](https://github.com/fox-it/dissect.fve)
- [dissect.hypervisor](https://github.com/fox-it/dissect.hypervisor)
- [dissect.jffs](https://github.com/fox-it/dissect.jffs)
- [dissect.ntfs](https://github.com/fox-it/dissect.ntfs)
- [dissect.ole](https://github.com/fox-it/dissect.ole)
- [dissect.qnxfs](https://github.com/fox-it/dissect.qnxfs)
- [dissect.regf](https://github.com/fox-it/dissect.regf)
- [dissect.shellitem](https://github.com/fox-it/dissect.shellitem)
- [dissect.sql](https://github.com/fox-it/dissect.sql)
- [dissect.squashfs](https://github.com/fox-it/dissect.squashfs)
- [dissect.target](https://github.com/fox-it/dissect.target)
- [dissect.thumbcache](https://github.com/fox-it/dissect.thumbcache)
- [dissect.util](https://github.com/fox-it/dissect.util)
- [dissect.vmfs](https://github.com/fox-it/dissect.vmfs)
- [dissect.volume](https://github.com/fox-it/dissect.volume)
- [dissect.xfs](https://github.com/fox-it/dissect.xfs)

### Related

These projects are closely related to Dissect, but not installed by this meta package.

- [acquire](https://github.com/fox-it/acquire)
- [flow.record](https://github.com/fox-it/flow.record)

## Requirements

This project is part of the Dissect framework and requires Python.

Information on the supported Python versions can be found in the Getting Started section of [the documentation](https://docs.dissect.tools/en/latest/index.html#getting-started).

## Installation

`dissect` is available on [PyPI](https://pypi.org/project/dissect/).

```bash
pip install dissect
```

## Build and test instructions

This project uses `tox` to build source and wheel distributions. Run the following command from the root folder to build
these:

```bash
tox -e build
```

The build artifacts can be found in the `dist/` directory.

`tox` is also used to run linting and unit tests in a self-contained environment. To run both linting and unit tests
using the default installed Python version, run:

```bash
tox
```

For a more elaborate explanation on how to build and test the project, please see [the
documentation](https://docs.dissect.tools/en/latest/contributing/tooling.html).

## Contributing

The Dissect project encourages any contribution to the codebase. To make your contribution fit into the project, please
refer to [the development guide](https://docs.dissect.tools/en/latest/contributing/developing.html).

## Copyright and license

Dissect is released as open source by Fox-IT (<https://www.fox-it.com>) part of NCC Group Plc
(<https://www.nccgroup.com>).

Developed by the Dissect Team (<dissect@fox-it.com>) and made available at <https://github.com/fox-it/dissect>.

License terms: AGPL3 (<https://www.gnu.org/licenses/agpl-3.0.html>). For more information, see the LICENSE file.
