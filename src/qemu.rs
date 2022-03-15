use core::arch::asm;

#[cfg(test)]
pub fn exit() -> ! {
    unsafe {
        asm!(
            "bkpt #0xab",
            in("r1") 0x20026, // ADP_Stopped_ApplicationExit
            inout("r0") 0x18 => _,
        );
    }

    loop {}
}

// Print using semihosting
// Used to easily display something in QEMU
pub fn debug_print(s: &str) {
    let p = s.as_bytes().as_ptr();
    for i in 0..s.len() {
        let m = unsafe { p.offset(i as isize) };
        unsafe {
            asm!(
                "bkpt #0xab",
                in("r1") m,
                inout("r0") 3 => _,
            );
        }
    }
}

struct DebugStruct {}

impl DebugStruct {
    pub fn new() -> DebugStruct {
        DebugStruct {}
    }
}

use core::fmt;

impl fmt::Write for DebugStruct {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        crate::qemu::debug_print(s);
        Ok(())
    }
}

pub fn _print(args: fmt::Arguments) {
    use core::fmt::Write;
    DebugStruct::new().write_fmt(args).unwrap();
}

#[macro_export]
macro_rules! print {
    ($($arg:tt)*) => {
        ($crate::qemu::_print(format_args!($($arg)*)))
    }
}

#[macro_export]
macro_rules! println {
    () => ($crate::print!("\n"));
    ($($arg:tt)*) => ($crate::print!("{}\n", format_args!($($arg)*)));
}
