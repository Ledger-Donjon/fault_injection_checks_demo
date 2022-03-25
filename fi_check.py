import capstone as cs
import unicorn as uc 
from rainbow.generics import rainbow_arm as rbw
from addr2line import get_addr2line

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
			try:
				emu.start(current_pc | thumb_bit, 0, count = 1)
			except uc.unicorn.UcError:
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

	emulator[0] = 0xffffffff

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

def test_faults(emulator, target_function, fault_injector, fault_setup, is_faulted, max_ins=1000, cli_report=False):	
	faults = [] 
	crash_count = 0 
	stopgap = 0xddddeeee
	emulator[stopgap:stopgap+max_ins] = 0

	# Place an invalid instruction at 0
	# so that we also detect corrupted stacks
	emulator[0] = 0xffffffff

	for i in range(1, max_ins):
		fault_setup()
		emulator.reset()

		# Also reset disassembler to thumb mode
		emulator.disasm.mode = cs.CS_MODE_THUMB

		# Setup fake caller so we know when the function returned
		emulator['lr'] = stopgap

		try:
			emulator.start(target_function, stopgap, count = i)
		except uc.unicorn.UcError as uc_error:
			crash_count += 1
			continue	

		pc_stopped = emulator['pc']

		# Only if we haven't already reached
		# the end of the execution
		if pc_stopped == stopgap:
			# current 'i' hits after the function has ended
			# No more tests to do
			break
		else:
			new_pc = fault_injector(emulator, pc_stopped)
			if new_pc is None:
				# Trying to fault an invalid instruction, pass
				crash_count += 1
				continue
			try:
				# execute until back to start or looping for too long
				emulator.start(new_pc, stopgap, count = max_ins) 
			except uc.unicorn.UcError as uc_error:
				# Crashed after the fault.
				# This includes cases were 'faulted_return' was executed but
				# lead to an incorrect state 
				# However if 'faulted_return' represents a permanent decision like
				# updating a flag in non-volatile memory then it is incorrect
				# to consider this a crash, and this part of the script should
				# be adapted accordingly (i.e. complete the loop iteration)
				crash_count += 1
				continue	

		status = is_faulted()
		if status is None:
			# Execution went astray and never reached either 'faulted_return' nor 'nominal_behavior'
			crash_count += 1
		elif status == True:
			# Successful fault: execution reached 'faulted_return' (and did not crash afterwards)
			addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(pc_stopped, 4)
			func, file_ = get_addr2line(addr, no_llvm=cli_report)
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

if __name__ == "__main__":
	import sys
	from argparse import ArgumentParser
	argp = ArgumentParser()
	argp.add_argument('functions', nargs='*', help="functions to scan, default to all")
	argp.add_argument('--cli', action='store_const', const=True, default=False, help="produce report in command line")
	argp.add_argument('-r', '--replay', action='store_const', const=True, default=False, help="replay found faults with instruction trace")
	args = argp.parse_args()

	e = rbw()
	e.load('./target/thumbv6m-none-eabi/release/examples/fi_test', typ='.elf')
	e.trace = False 

	def faulted_return(emu):
		global EXIT_STATUS
		EXIT_STATUS = True
		return False  # do not skip instruction

	def nominal_behavior(emu):
		global EXIT_STATUS
		EXIT_STATUS = False 
		return False  # do not skip instruction

	# Hook to panic, mostly caused by fault injection
	# rust_begin_unwind is called when panic! happens
	e.stubbed_functions['rust_begin_unwind'] = faulted_return

	def fi_setup():
		global EXIT_STATUS
		EXIT_STATUS = None

	def fi_test():
		global EXIT_STATUS
		return EXIT_STATUS 

	def inject_zero(a,p):
		return inject_stuck_at(a,p,0)

	def inject_ones(a,p):
		return inject_stuck_at(a,p,0xffff_ffff)

	# If no functions name were provided, default to all functions beginning
	# with `fi_test_`
	if not args.functions:
		args.functions = [f for f in e.functions.keys() if f.startswith("fi_test_")]

	functions_to_test = [e.functions[f] for f in args.functions]

	total_faults = [] 
	for func in functions_to_test:
		# Hook to a function appended to the end of the test
		# This is used to check if the fault makes the function return
		name = e.function_names[func]
		e.stubbed_functions[f'nominal_behavior_{name}'] = nominal_behavior

		if args.cli:
			print(f'\n* Testing \x1b[1;35m{name}\x1b[0m')
		for model in [inject_skip, inject_zero, inject_ones]:
			if args.cli:
				print(f"[ ] {model.__name__}")
			res = test_faults(e, func, model, fi_setup, fi_test, cli_report=args.cli)
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