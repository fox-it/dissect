# dissect

This project is a meta package, it will install all other Dissect modules with the right combination of versions. For
more information, please see [the documentation](https://dissect.readthedocs.io/en/latest/projects).

## Projects

- [dissect.cim](https://github.com/fox-it/dissect.cim)
- [dissect.clfs](https://github.com/fox-it/dissect.clfs)
- [dissect.cstruct](https://github.com/fox-it/dissect.cstruct)
- [dissect.esedb](https://github.com/fox-it/dissect.esedb)
- [dissect.etl](https://github.com/fox-it/dissect.etl)
- [dissect.eventlog](https://github.com/fox-it/dissect.eventlog)
- [dissect.evidence](https://github.com/fox-it/dissect.evidence)
- [dissect.extfs](https://github.com/fox-it/dissect.extfs)
- [dissect.fat](https://github.com/fox-it/dissect.fat)
- [dissect.ffs](https://github.com/fox-it/dissect.ffs)
- [dissect.hypervisor](https://github.com/fox-it/dissect.hypervisor)
- [dissect.ntfs](https://github.com/fox-it/dissect.ntfs)
- [dissect.ole](https://github.com/fox-it/dissect.ole)
- [dissect.regf](https://github.com/fox-it/dissect.regf)
- [dissect.sql](https://github.com/fox-it/dissect.sql)
- [dissect.target](https://github.com/fox-it/dissect.target)
- [dissect.util](https://github.com/fox-it/dissect.util)
- [dissect.vmfs](https://github.com/fox-it/dissect.vmfs)
- [dissect.volume](https://github.com/fox-it/dissect.volume)
- [dissect.xfs](https://github.com/fox-it/dissect.xfs)

### Related

These projects are closely related to Dissect, but not installed by this meta package.

- [acquire](https://github.com/fox-it/acquire)
- [flow.record](https://github.com/fox-it/flow.record)

## Installation

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
documentation](https://dissect.readthedocs.io/en/latest/contributing/developing.html#building-testing).

## Contributing

The Dissect project encourages any contribution to the codebase. To make your contribution fit into the project, please
refer to [the style guide](https://dissect.readthedocs.io/en/latest/contributing/style-guide.html).

## Copyright and license

Dissect is released as open source by Fox-IT (<https://www.fox-it.com>) part of NCC Group Plc
(<https://www.nccgroup.com>).

Developed by the Dissect Team (<dissect@fox-it.com>) and made available at <https://github.com/fox-it/dissect>.

License terms: AGPL3 (<https://www.gnu.org/licenses/agpl-3.0.html>). For more information, see the LICENSE file.
