use core::fmt;

pub fn _print(args: fmt::Arguments) {
    use core::fmt::Write;
    use cortex_m_semihosting::hio;

    if let Ok(mut hstdout) = hio::hstdout() {
        write!(hstdout, "{}", args).ok();
    }
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
