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
	emu[0] = 0xffffffff

	return emu


def replay_fault(instruction_index, emulator, target_function, fault_injector, max_ins=200):
	""" Execute function and display instruction trace, while applying fault at 'instruction_index'"""
	emulator.trace = True
	emulator.function_calls = True
	emulator.mem_trace = True
	emulator.trace_regs = True

	stopgap = 0xddddeeee
	emulator[stopgap:stopgap+max_ins] = 0

	emulator.meta = {}
	emulator.reset()
	# Reset disassembler
	emulator.disasm.mode = cs.CS_MODE_THUMB

	emulator['lr'] = stopgap
	emulator.start(target_function, stopgap, count=instruction_index)

	addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(emulator['pc'], 4)
	emulator.print_asmline(addr, ins_mnemonic, ins_str)
	print('<--!', end='\n\n')
	thumb_bit = (emulator["cpsr"] >> 5) & 1
	fault_injector(emulator)
	emulator.start(emulator["pc"] | thumb_bit, stopgap, count=max_ins)


def test_faults(path, target_function, fault_injector, max_ins=1000, cli_report=False):
	faults = []
	crash_count = 0
	stopgap = 0xddddeeee

	# Setup emulator
	emulator = setup_emulator(path)
	emulator[stopgap:stopgap+max_ins] = 0

	for i in range(1, max_ins):
		# Init metadata and reset
		emulator.meta = {}
		emulator.reset()

		# Also reset disassembler to thumb mode
		emulator.disasm.mode = cs.CS_MODE_THUMB

		# Setup fake caller so we know when the function returned
		emulator['lr'] = stopgap

		end = emulator.functions["rust_fi_nominal_behavior"]
		try:
			pc_stopped = emulator.start_and_fault(fault_injector, i, target_function, end, count=max_ins)
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
			emulator = setup_emulator(path)
			emulator[stopgap:stopgap+max_ins] = 0
			continue

		if emulator.meta.get("exit_status") is None:
			# Execution went astray and never reached either 'faulted_return' nor 'nominal_behavior'
			crash_count += 1
		elif emulator.meta.get("exit_status") == True:
			# Successful fault: execution reached 'faulted_return' (and did not crash afterwards)
			addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(pc_stopped, 4)
			func, file_ = get_addr2line(path, addr, no_llvm=cli_report)
			if cli_report:
				emulator.print_asmline(addr, ins_mnemonic, ins_str)
				print(' <= Faulted', end='')
				print( f" with \x1b[1;36m{fault_injector.__name__}\x1b[0m in \x1b[1;36m{func}\x1b[0m ({file_}) \x1b[0m", end='')
			else:
				print(f"\nwarning: '[{fault_injector.__name__}] {ins_mnemonic} {ins_str}' {file_} ")
			faults += [(i, addr)]

	if cli_report:
		fault_count = len(faults)
		if fault_count > 0:
			clr = "\x1b[1;31m"
		else:
			clr = "\x1b[1;32m"

		print(f"\n[x] Found {clr} {fault_count} \x1b[0m fault{'s'*(fault_count>1)} and {crash_count} crashes.")
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
	argp.add_argument('functions', nargs='*', help="functions to scan, default to all")
	argp.add_argument('--cli', action='store_const', const=True, default=False, help="produce report in command line")
	argp.add_argument('-r', '--replay', action='store_const', const=True, default=False, help="replay found faults with instruction trace")
	args = argp.parse_args()

	# Build emulator
	path = cargo_build_test()
	e = setup_emulator(path)

	# If no functions name were provided, default to all functions beginning
	# with `test_fi_`
	if not args.functions:
		args.functions = [f for f in e.functions.keys() if f.startswith("test_fi_")]

	functions_to_test = [e.functions[f] for f in args.functions]

	total_faults = []
	for func in functions_to_test:
		if args.cli:
			name = e.function_names[func]
			print(f'\n* Testing \x1b[1;35m{name}\x1b[0m')
		for model in [fault_skip, fault_stuck_at(0), fault_stuck_at(0xffff_ffff)]:
			if args.cli:
				print(f"[ ] {model.__name__}")
			res = test_faults(path, func, model, cli_report=args.cli)
			if len(res) > 0:
				total_faults += [[model, res]]

	if args.replay:
		for flts in total_faults:
			model = flts[0]
			print('*'*10, model.__name__, '*'*10)
			for flt in flts[1]:
				print(f"\n{'-'*10} replaying {model.__name__} at {flt[1]:x}:")
				replay_fault(flt[0], e, func, model)

	sys.exit(len(total_faults) > 0)
