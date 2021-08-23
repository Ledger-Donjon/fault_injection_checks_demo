from rainbow.generics import rainbow_arm as rbw
from fi_check import *

if __name__ == "__main__":
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

	inject_zero = lambda a,p:inject_stuck_at(a,p,0)
	inject_ones = lambda a,p:inject_stuck_at(a,p,0xffff_ffff)

	# Only interested in verifying the safe comparison function
	# which is fi_test4
	func = e.functions['fi_test4']

	print("[ ] Injecting skips.")
	total_faults = test_faults(e, func, inject_skip, fi_setup, fi_test)
	print("[ ] Injecting zeroes.")
	total_faults += test_faults(e, func, inject_zero, fi_setup, fi_test)
	print("[ ] Injecting ones.")
	total_faults += test_faults(e, func, inject_ones, fi_setup, fi_test)

	import sys

	if total_faults > 0:
		sys.exit(-1)
	sys.exit(0)