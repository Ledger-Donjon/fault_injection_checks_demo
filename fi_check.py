from rainbow.generics import rainbow_arm as rbw

def inject_skip(emu, current_pc):
	_, ins_size, ins_mnemonic, ins_str = emu.disassemble_single(current_pc, 4)
	return (current_pc + ins_size) | 1

def inject_stuck_at(emu, current_pc, value):
	ins = emu.disassemble_single_detailed(current_pc, 4)
	_, regs_written = ins.regs_access()
	if len(regs_written) > 0:
		reg_names = list(filter(lambda r:r.lower() not in ['cpsr', 'pc', 'lr'], map(ins.reg_name,regs_written)))

		if len(reg_names) > 0:
			r = reg_names[0]
			# We're stopped before executing the target instruction
			# so we step once, inject the fault, and return
			emu.start(current_pc | 1, 0, count = 1)
			emu[r] = value
			current_pc = emu['pc']
	return current_pc | 1

def test_faults(emulator, target_function, fault_injector, fault_setup, is_faulted, max_ins=45):	
	fault_count = 0 
	crash_count = 0 
	stopgap = 0xddddeeee
	emulator[stopgap] = 0

	for i in range(5, max_ins):
		fault_setup()
		emulator.reset()
		emulator['lr'] = stopgap
		emulator.start(target_function, stopgap, count = i)

		pc_stopped = emulator['pc']
		# print(hex(pc_stopped)[:1], end='\b') # Race condition in unicorn...Without the 'print', pc_stopped is not retrieved
		if pc_stopped != stopgap:
			new_pc = fault_injector(emulator, pc_stopped)
			emulator.start(new_pc, stopgap, count = max_ins) # execute until back to start or looping for too long

		status = is_faulted()
		addr, _, ins_mnemonic, ins_str = emulator.disassemble_single(pc_stopped, 4)
		# emulator.print_asmline(addr, ins_mnemonic, ins_str)
		if status is None:
			# emulator.print_asmline(addr, ins_mnemonic, ins_str)
			# print(' *** crashed ***', end=' ')
			crash_count += 1
		elif status == True:
			emulator.print_asmline(addr, ins_mnemonic, ins_str)
			print(' <= Faulted', end=' ')
			fault_count += 1

	if fault_count > 0:
		clr = "\x1b[1;31m" 
	else:
		clr = "\x1b[1;32m" 

	print(f"\n[x] Found {clr} {fault_count} \x1b[0m fault{'s'*(fault_count>1)} and {crash_count} crashes.")
	return fault_count

if __name__ == "__main__":
	e = rbw()
	e.load('./target/thumbv6m-none-eabi/release/examples/fi_test', typ='.elf')
	e.trace = False 
	# e.function_calls = True
	# e.trace_regs = True

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

	inject_zero = lambda a,p:inject_stuck_at(a,p,0)
	inject_one = lambda a,p:inject_stuck_at(a,p,0xffff_ffff)

	functions_to_test = [e.functions[f] for f in ['fi_test1', 'fi_test2', 'fi_test3', 'fi_test4']]

	for func in functions_to_test:
		print(f'\n* Testing \x1b[1;35m{e.function_names[func]}\x1b[0m') 
		print("[ ] Injecting skips.")
		test_faults(e, func, inject_skip, fi_setup, fi_test)
		print("[ ] Injecting zeroes.")
		test_faults(e, func, inject_zero, fi_setup, fi_test)
		print("[ ] Injecting ones.")
		test_faults(e, func, inject_one, fi_setup, fi_test)