#!/usr/bin/env python3

import json
import subprocess

import capstone as cs
from rainbow.generics import rainbow_arm
from rainbow.fault_models import fault_skip, fault_stuck_at
from addr2line import get_addr2line


def setup_emulator(path: str) -> rainbow_arm:
    """Setup emulation and hooks around targeted fault injection test in
    executable.

    :param str path: Path of the ELF file to audit
    :return rainbow_arm: Rainbow instance
    """
    emu = rainbow_arm()
    emu.load(path, typ=".elf")
    emu.trace = False

    def faulted_behavior(emu: rainbow_arm):
        # ignore faults that are happening after normal behavior
        if emu.meta.get("exit_status") is None:
            emu.meta["exit_status"] = True
        emu.emu.emu_stop()

    def nominal_behavior(emu: rainbow_arm):
        if emu.meta.get("exit_status") is None:
            emu.meta["exit_status"] = False
        emu.emu.emu_stop()

    # Hook to normal and faulted behavior
    emu.hook_prolog("rust_fi_faulted_behavior", faulted_behavior)
    emu.hook_prolog("rust_fi_nominal_behavior", nominal_behavior)

    # Place an invalid instruction at 0 to detect corrupted stacks
    emu[0] = 0xFFFFFFFF

    return emu


def replay_fault(fault_index: int, emu, begin: int, fault_model, max_ins=200) -> None:
    """Execute function and display instruction trace, while applying fault at 'fault_index'"""
    emu.trace = True
    emu.function_calls = True
    emu.mem_trace = True
    emu.trace_regs = True

    # Init metadata and reset
    emu.meta = {}
    emu.reset()

    # Reset disassembler
    emu.disasm.mode = cs.CS_MODE_THUMB

    end = emu.functions["rust_fi_nominal_behavior"]
    emu.start_and_fault(fault_model, fault_index, begin, end, count=max_ins)


def test_faults(path, begin: int, fault_model, max_ins=1000, cli_report=False):
    faults = []
    crash_count = 0
    emu = setup_emulator(path)

    for i in range(1, max_ins):
        # Init metadata and reset
        emu.meta = {}
        emu.reset()

        # Also reset disassembler to thumb mode
        emu.disasm.mode = cs.CS_MODE_THUMB

        end = emu.functions["rust_fi_nominal_behavior"]
        try:
            pc_stopped = emu.start_and_fault(fault_model, i, begin, end, count=max_ins)
        except IndexError:
            break  # Faulting after the end of the function
        except RuntimeError:
            # Fault introduced crash
            # This includes cases were 'faulted_return' was executed but
            # lead to an incorrect state.
            # However if 'faulted_return' represents a permanent decision like
            # updating a flag in non-volatile memory then it is incorrect
            # to consider this a crash, and this part of the script should
            # be adapted accordingly (i.e. complete the loop iteration).
            crash_count += 1

            # Fully reset emulator
            emu = setup_emulator(path)
            continue

        if emu.meta.get("exit_status") is None:
            # Execution went astray and never reached either 'faulted_return' nor 'nominal_behavior'
            crash_count += 1
        elif emu.meta.get("exit_status") == True:
            # Successful fault: execution reached 'faulted_return' (and did not crash afterwards)
            addr, _, ins_mnemonic, ins_str = emu.disassemble_single(pc_stopped, 4)
            func, file_ = get_addr2line(path, addr, no_llvm=cli_report)
            if cli_report:
                emu.print_asmline(addr, ins_mnemonic, ins_str)
                print(
                    f" <= Faulted with \x1b[1;36m{fault_model.__name__}"
                    f"\x1b[0m in \x1b[1;36m{func}\x1b[0m ({file_}) \x1b[0m",
                    end="",
                )
            else:
                print(
                    f"\nwarning: '[{fault_model.__name__}] {ins_mnemonic} {ins_str}' {file_} "
                )
            faults += [(i, addr)]

    if cli_report:
        fault_count = len(faults)
        clr = "\x1b[1;31m" if fault_count > 0 else "\x1b[1;32m"
        print(
            f"\n[x] Found {clr} {fault_count} \x1b[0m fault{'s'*(fault_count>1)} and {crash_count} crashes."
        )
    return faults


def cargo_build_test(path="pin_verif") -> str:
    """Call Cargo to build test and return path"""
    proc = subprocess.run(
        "cargo test --features test_fi --no-run --release --message-format=json",
        shell=True,
        cwd=path,
        stdout=subprocess.PIPE,
    )
    proc.check_returncode()
    for json_out in proc.stdout.split(b"\n"):
        data = json.loads(json_out)
        if data.get("executable") and data.get("target", {}).get("test"):
            return data.get("executable")
    raise RuntimeError("Cargo did not return a test executable.")


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser

    argp = ArgumentParser()
    argp.add_argument("functions", nargs="*", help="functions to scan, default to all")
    argp.add_argument(
        "--cli",
        action="store_const",
        const=True,
        default=False,
        help="produce report in command line",
    )
    argp.add_argument(
        "-r",
        "--replay",
        action="store_const",
        const=True,
        default=False,
        help="replay found faults with instruction trace",
    )
    args = argp.parse_args()

    # Build emulator
    path = cargo_build_test()
    e = setup_emulator(path)

    # If no functions name were provided, default to all functions beginning
    # with `test_fi_`
    if not args.functions:
        args.functions = [f for f in e.functions.keys() if f.startswith("test_fi_")]

    functions_to_test = [e.functions[f] for f in args.functions]

    exit_code = 0
    for func in functions_to_test:
        if args.cli:
            name = e.function_names[func]
            print(f"\n* Testing \x1b[1;35m{name}\x1b[0m")

        total_faults = []
        for model in [fault_skip, fault_stuck_at(0), fault_stuck_at(0xFFFF_FFFF)]:
            if args.cli:
                print(f"[ ] {model.__name__}")
            res = test_faults(path, func, model, cli_report=args.cli)
            if len(res) > 0:
                exit_code = 1
                total_faults += [[model, res]]

        if args.replay:
            for flts in total_faults:
                model = flts[0]
                print("*" * 10, model.__name__, "*" * 10)
                for flt in flts[1]:
                    print(f"\n{'-'*10} replaying {model.__name__} at {flt[1]:x}:")
                    replay_fault(flt[0], e, func, model)

    sys.exit(exit_code)
