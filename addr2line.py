import subprocess as sp
from typing import Tuple


def get_addr2line(path: str, addr: int, no_llvm=True) -> Tuple[str, str]:
	addr2line = sp.run(["addr2line", 
						"-fiC",
						"-e", path,
						"-a", f"{addr:x}",
				] + ["--llvm"]*(not no_llvm), stdout=sp.PIPE)
	func, file = addr2line.stdout.decode().split()[-2:]
	return func, file

if __name__ == "__main__":
	print(get_addr2line("example.elf", 0x2e2))
