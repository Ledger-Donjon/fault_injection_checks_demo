import subprocess as sp

def get_addr2line(addr, no_llvm=True):
	addr2line = sp.run(["addr2line", 
						"-fiC",
						"-e", "./target/thumbv6m-none-eabi/release/examples/fi_test",
						"-a", f"{addr:x}",
				] + ["--llvm"]*(not no_llvm), stdout=sp.PIPE)
	return addr2line.stdout.decode().split()[-2:]

if __name__ == "__main__":
	print(get_addr2line(0x2e2))