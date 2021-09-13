## Requirements

Install `addr2line` by cloning [](https://github.com/gimli-rs/addr2line) and `cargo install --example addr2line`

## Usage

First build the example with:

```
cargo build --release --example fi_test
```

### Testing against faults locally

`python fi_check.py --cli fi_test1 ...`

There is also a `replay` functionality available that yields an execution trace, applying the found faults.

```
python fi_check.py --cli fi_test1 -r
```

### VSCode task

Run one of the available tasks:

- `Fault: All tests`
- `Fault: Safe test`