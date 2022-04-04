import json
import subprocess
from typing import Optional

import capstone as cs
from rainbow.generics import rainbow_arm
from addr2line import get_addr2line


def setup_emulator(path: str, target_function: Optional[int]) -> rainbow_arm:
	"""Setup emulation and hooks around targeted fault injection test in
	executable.

	:param str path: Path of the ELF file to audit
	:param Optional[int] target_function: Address of the fault injection test,
		can be None to skip hook setup.
	:return rainbow_arm: Rainbow instance
	"""
	emu = rainbow_arm()
	emu.load(path, typ=".elf")
	emu.trace = False

	def faulted_return(emu: rainbow_arm) -> bool:
		# ignore faults that are happening after normal behavior
		if emu.meta["exit_status"] is None:
			emu.meta["exit_status"] = True
		return False  # do not skip instruction

	def nominal_behavior(emu: rainbow_arm) -> bool:
		emu.meta["exit_status"] = False
		emu.emu.emu_stop()
		return False  # do not skip instruction

	# Hook to panic, mostly caused by fault injection
	# rust_begin_unwind is called when panic happens
	emu.stubbed_functions["rust_begin_unwind"] = faulted_return

	# Hook to a function appended to the end of the test
	# This is used to check if the fault makes the function return
	if target_function is not None:
		name = emu.function_names[target_function]
		emu.stubbed_functions[f"nominal_behavior_{name}"] = nominal_behavior

	# Place an invalid instruction at 0 to detect corrupted stacks
	emu[0] = 0xffffffff

	return emu


def inject_skip(emu, current_pc):
	""" Skip current instruction at 'current_pc' with emulator state 'emu' """
	ins = emu.disassemble_single(current_pc, 4)
	if ins is None:
		return None
	_, ins_size, _, _ = ins
	thumb_bit = (emu["cpsr"]>>5) & 1
	return (current_pc + ins_size) | thumb_bit 


def inject_stuck_at(emu, current_pc, value):
	""" Injects a value in the destination register updated by the current instruction """
	ins = emu.disassemble_single_detailed(current_pc, 4)
	if ins is None:
		return None
	_, regs_written = ins.regs_access()
	if len(regs_written) > 0:
		reg_names = list(filter(lambda r:r.lower() not in ['cpsr', 'pc', 'lr'], map(ins.reg_name,regs_written)))
		if len(reg_names) > 0:
			r = reg_names[0]
			# We're stopped before executing the target instruction
			# so we step once, inject the fault, and return
			thumb_bit = (emu["cpsr"]>>5) & 1
			if emu.start(current_pc | thumb_bit, 0, count = 1):
				return None 
			emu[r] = value
			current_pc = emu['pc']
	thumb_bit = (emu["cpsr"]>>5) & 1
	ret = current_pc | thumb_bit
	return ret 


def replay_fault(instruction_index, emulator, target_function, fault_injector, max_ins=200):
	""" Execute function and display instruction trace, while applying fault at 'instruction_index'"""
	emulator.trace = True
	emulator.function_calls = True
	emulator.mem_trace = True
	emulator.trace_regs = True

	stopgap = 0xddddeeee
	emulator[stopgap:stopgap+max_ins] = 0

	emulator.reset()
	# Reset disassembler
	emulator.disasm.mode = cs.CS_MODE_THUMB

	emulator['lr'] = stopgap
	emulator.start(target_function, stopgap, count = instruction_index)

	pc_stopped = emulator['pc']
	new_pc = fault_injector(emulator, pc_stopped)
	addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(pc_stopped, 4)
	emulator.print_asmline(addr, ins_mnemonic, ins_str)
	print('<--!', end='\n\n')
	ret = emulator.start(new_pc, stopgap, count = max_ins)


def test_faults(path, target_function, fault_injector, max_ins=1000, cli_report=False):
	faults = [] 
	crash_count = 0 
	stopgap = 0xddddeeee

	# Setup emulator
	emulator = setup_emulator(path, target_function)
	emulator[stopgap:stopgap+max_ins] = 0

	for i in range(1, max_ins):
		# Init exit_status state
		emulator.meta = {}
		emulator.meta["exit_status"] = None

		emulator.reset()

		# Also reset disassembler to thumb mode
		emulator.disasm.mode = cs.CS_MODE_THUMB

		# Setup fake caller so we know when the function returned
		emulator['lr'] = stopgap

		if emulator.start(target_function, stopgap, count=i):
			raise RuntimeError(f"Emulator crashed before faulting")

		pc_stopped = emulator['pc']

		# Only if we haven't already reached
		# the end of the execution
		if pc_stopped == stopgap or emulator.meta["exit_status"] is not None:
			# current 'i' hits after the function has ended
			# No more tests to do
			break
		else:
			new_pc = fault_injector(emulator, pc_stopped)
			if new_pc is None:
				# Trying to fault an invalid instruction, pass
				crash_count += 1
				continue

			# execute until back to start or looping for too long
			if emulator.start(new_pc, stopgap, count=max_ins):
				# Crashed after the fault.
				# This includes cases were 'faulted_return' was executed but
				# lead to an incorrect state 
				# However if 'faulted_return' represents a permanent decision like
				# updating a flag in non-volatile memory then it is incorrect
				# to consider this a crash, and this part of the script should
				# be adapted accordingly (i.e. complete the loop iteration)
				crash_count += 1

				# Fully reset emulator
				emulator = setup_emulator(path, target_function)
				emulator[stopgap:stopgap+max_ins] = 0
				continue

		if emulator.meta["exit_status"] is None:
			# Execution went astray and never reached either 'faulted_return' nor 'nominal_behavior'
			crash_count += 1
		elif emulator.meta["exit_status"] == True:
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


def cargo_build_test() -> str:
	"""Call Cargo to build test and return path"""
	proc = subprocess.run(
		"cargo test --features test_fi --no-run --release --message-format=json",
		shell=True,
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

	def inject_zero(a,p):
		return inject_stuck_at(a,p,0)

	def inject_ones(a,p):
		return inject_stuck_at(a,p,0xffff_ffff)

	# Build emulator
	path = cargo_build_test()
	e = setup_emulator(path, None)

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
		for model in [inject_skip, inject_zero, inject_ones]:
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

	if len(total_faults) > 0:
		sys.exit(1)
	sys.exit(0)	