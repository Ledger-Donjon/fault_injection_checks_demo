import json
import random
import subprocess
from typing import Iterator, Optional

import numpy as np
from lascar import TraceBatchContainer, compute_ttest
from rainbow.devices import rainbow_stm32 as rainbow
from tqdm import tqdm


def cargo_build_tvla_targets() -> Iterator[str]:
    """Call Cargo to build TVLA targets and yield their path

    :yield Iterator[str]: paths of compiled ELF
    """
    proc = subprocess.run(
        "cargo build --release --message-format=json",
        shell=True,
        cwd="tvla",
        stdout=subprocess.PIPE,
    )
    proc.check_returncode()
    for json_out in proc.stdout.split(b"\n"):
        if not json_out:
            continue  # ignore empty lines
        data = json.loads(json_out)
        if data.get("executable"):
            yield data.get("executable")


def setup_emulator(path: str) -> rainbow:
    """Setup emulation for side-channel traces acquisition.

    :param str path: Path of the ELF file to audit
    :return rainbow: Rainbow instance
    """
    emu = rainbow(sca_mode=True)
    emu.load(path, typ=".elf")

    def trace_begin(emu: rainbow) -> bool:
        emu.trace_reset()
        return True  # replace instruction

    def trace_end(emu: rainbow) -> bool:
        emu.emu.emu_stop()
        return False  # add before instruction

    # Enable user to delimit the side-channel trace
    emu.stubbed_functions["rust_tvla_test_trace_begin"] = trace_begin
    emu.stubbed_functions["rust_tvla_test_trace_end"] = trace_end

    # Measure Hamming weight of written registers
    # emu.mem_trace = True
    emu.trace_regs = True

    return emu


def acquire_trace(emu: rainbow, fixed_random: int, length: int) -> np.ndarray:
    """Acquire one trace from emulation

    :param rainbow emu: Rainbow instance with firmware loaded
    :param int fixed_random: This input is random in only one TVLA set
    :param int length: Expected length of acquired trace, 0 to disable the check
    :raises RuntimeError: Raised if traced function does not have constant
        number of instructions
    :return np.ndarray: Side-channel trace
    """
    emu.reset()
    emu.trace_reset()

    # Collect one trace
    emu["r0"] = fixed_random
    if emu.start(emu.functions["rust_tvla_test_trace"] | 1, 0):
        raise RuntimeError(f"emulator crashed")
    trace = np.array(emu.sca_values_trace)

    if length and length != len(trace):
        raise RuntimeError(
            "traced function does not have constant number of instructions"
        )

    np.nan_to_num(trace, copy=False)
    return trace


def tvla(emu: rainbow, n_tr: int, seed: Optional[int] = None) -> np.ndarray:
    """Test Vector Leakage Assessment emulation

    :param rainbow emu: Rainbow instance with firmware loaded
    :param int n_tr: Number of traces to collect for each set
    :param Optional[int] seed: Random generator seed, defaults to None
    :return np.ndarray: T-test result
    """
    # Initial emulation to get trace length
    # The traced function must have a constant number of instructions
    trace = acquire_trace(emu, 0xDA39A3EE, 0)
    trace_length = len(trace)

    # Allocate memory for traces
    traces1 = np.zeros((n_tr, trace_length), dtype=type(trace[0]))
    traces2 = np.zeros((n_tr, trace_length), dtype=type(trace[0]))
    seeds = np.zeros((n_tr, 1), dtype=int)

    if seed is not None:
        random.seed(seed)

    # Acquire
    fixed_random_2 = random.randint(0, 2**32 - 1)
    for i in tqdm(range(n_tr)):
        fixed_random_1 = random.randint(0, 2**32 - 1)
        seeds[i, :] = [fixed_random_1]
        traces1[i, :] = acquire_trace(emu, fixed_random_1, trace_length)
        traces2[i, :] = acquire_trace(emu, fixed_random_2, trace_length)

    # Compute TVLA
    traces1 = TraceBatchContainer(traces1, seeds)
    traces2 = TraceBatchContainer(traces2, np.array([fixed_random_2]*n_tr))
    ttest = compute_ttest(traces1, traces2)

    return ttest


if __name__ == "__main__":
    import pathlib

    # TVLA for each target in tvla crate
    for path in cargo_build_tvla_targets():
        print(f"Testing Vector Leakage Assessment on {path}")
        target_name = pathlib.PurePath(path).name
        emu = setup_emulator(path)

        n = 100
        ttest = tvla(emu, n, 42)
        np.savetxt(f"tvla/ttests/{target_name}_{n}.csv", ttest)
        np.nan_to_num(ttest, copy=False)
