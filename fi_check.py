import capstone as cs
from rainbow.generics import rainbow_arm as rbw
from addr2line import get_addr2line

def inject_skip(emu, current_pc):
	thumb_bit = (emu["cpsr"]>>5) & 1
	_, ins_size, ins_mnemonic, ins_str = emu.disassemble_single(current_pc, 4)
	return (current_pc + ins_size) | thumb_bit 

def inject_stuck_at(emu, current_pc, value):
	ins = emu.disassemble_single_detailed(current_pc, 4)
	_, regs_written = ins.regs_access()
	if len(regs_written) > 0:
		reg_names = list(filter(lambda r:r.lower() not in ['cpsr', 'pc', 'lr'], map(ins.reg_name,regs_written)))
		if len(reg_names) > 0:
			r = reg_names[0]
			# We're stopped before executing the target instruction
			# so we step once, inject the fault, and return
			thumb_bit = (emu["cpsr"]>>5) & 1
			emu.start(current_pc | thumb_bit, 0, count = 1)
			emu[r] = value
			current_pc = emu['pc']
	thumb_bit = (emu["cpsr"]>>5) & 1
	return current_pc | thumb_bit 

def test_faults(emulator, target_function, fault_injector, fault_setup, is_faulted, max_ins=200, cli_report=False):	
	fault_count = 0 
	crash_count = 0 
	stopgap = 0xddddeeee
	emulator[stopgap] = 0

	for i in range(1, max_ins):
		fault_setup()
		emulator.reset()
		# Reset disassembler
		emulator.disasm.mode = cs.CS_MODE_THUMB
		emulator['lr'] = stopgap
		emulator.start(target_function, stopgap, count = i)

		pc_stopped = emulator['pc']
		print(hex(pc_stopped)[:1], end='\b') # Race condition in unicorn...Without the 'print', pc_stopped is not retrieved
		if pc_stopped != stopgap:
			new_pc = fault_injector(emulator, pc_stopped)
			emulator.start(new_pc, stopgap, count = max_ins) # execute until back to start or looping for too long
		else:
			continue	

		status = is_faulted()
		try:
			addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(pc_stopped, 4)
		except Exception as e:
			# Invalid instruction encountered, terminate
			crash_count += 1
			continue

		if status is None:
			crash_count += 1
		elif status == True:
			if cli_report:
				emulator.print_asmline(addr, ins_mnemonic, ins_str)
				print(' <= Faulted', end='')
				func, file_ = get_addr2line(addr)
				print( f" in \x1b[1;36m{func}\x1b[0m ({file_}) \x1b[0m", end='')
			else:
				func, file_ = get_addr2line(addr)
				print(f"\nwarning: '[{fault_injector.__name__}] {ins_mnemonic} {ins_str}' {file_} ")
			fault_count += 1

	if cli_report:
		if fault_count > 0:
			clr = "\x1b[1;31m" 
		else:
			clr = "\x1b[1;32m" 

		print(f"\n[x] Found {clr} {fault_count} \x1b[0m fault{'s'*(fault_count>1)} and {crash_count} crashes.")
	return fault_count

if __name__ == "__main__":
	import sys
	from argparse import ArgumentParser
	argp = ArgumentParser()
	argp.add_argument('functions', nargs='+', help="functions to be scanned")
	argp.add_argument('--cli', action='store_const', const=True, default=False, help="Produce report in command line.")
	args = argp.parse_args()

	e = rbw()
	e.load('./target/thumbv6m-none-eabi/release/examples/fi_test', typ='.elf')
	e.trace = False 

	def success(emu):
		global EXIT_STATUS
		EXIT_STATUS = True
		return True

	def fail(emu):
		global EXIT_STATUS
		EXIT_STATUS = False 
		return True

	e.stubbed_functions['fail'] = fail 
	e.stubbed_functions['success'] = success 

	def fi_setup():
		global EXIT_STATUS
		EXIT_STATUS = None

	def fi_test():
		global EXIT_STATUS
		return EXIT_STATUS 

	def inject_zero(a,p):
		inject_stuck_at(a,p,0)

	def inject_ones(a,p):
		inject_stuck_at(a,p,0xffff_ffff)

	functions_to_test = [e.functions[f] for f in args.functions]

	total_faults = 0
	for func in functions_to_test:
		if args.cli:
			print(f'\n* Testing \x1b[1;35m{e.function_names[func]}\x1b[0m') 
		for model in [inject_skip, inject_zero, inject_ones]:
			if args.cli:
				print(f"[ ] {model.__name__}")
			total_faults += test_faults(e, func, model, fi_setup, fi_test, cli_report=args.cli)

	
	if total_faults > 0:
		sys.exit(1)
	sys.exit(0)	