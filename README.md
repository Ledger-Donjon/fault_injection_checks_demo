# Fault injection simulation demonstrations

This repository contains the source code associated with the
[Integrating fault injection in development workflows](https://blog.ledger.com/fault-injection-simulation/) blog post.
Next to the `fi_check.py` demonstration script, you may find these Rust crates:

  * `rust_fi`: contains the custom `assert_eq!` macro used by `fi_check.py`.
  * `pin_verif`: contains examples of vulnerable functions and mitigation.
  * `fault_hardened`: a set of Rust types hardened against single-fault
    injection attacks.

## Requirements

If you have never used Rust on your machine, you might start by
[installing rustup](https://www.rust-lang.org/tools/install).

  * The Nightly Rust distribution with `thumbv6m-none-eabi` target,
    can be installed using
    `rustup default nightly` and `rustup target add thumbv6m-none-eabi`,
  * Python 3.8 or later,
  * Rainbow module, can be installed using
    `pip install git+https://github.com/Ledger-Donjon/rainbow`.

The evaluation script requires `addr2line` to locate which line of source code
generated an instruction in the assembly. The standard provided in GNU/Linux
distributions might not handle Rust code correctly.
We recommend installing the Rust variant with
`cargo install addr2line --examples`.

## Usage

### Testing against faults locally

To evaluate all function beginning with `test_fi_` in `pin_verif` crate:

```
python fi_check.py --cli --path pin_verif
```

There is also a `replay` functionality available that yields execution traces,
applying the found faults:

```
python fi_check.py --cli test_fi_simple -r
```

### Visual Studio Code integration

The `.vscode` folder includes some tasks that runs evaluation on current crate:

- `Fault: All tests`
- `Fault: Safe test`
