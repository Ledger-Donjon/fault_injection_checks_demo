#![no_std]
#![cfg_attr(test, no_main)]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]
#![test_runner(test_utils::test_runner)]

pub mod bool_protected;
pub mod qemu;

#[cfg(test)]
mod test_utils;

use core::panic::PanicInfo;

/// With the panic handler being `#[inline(never)]` the symbol
/// `rust_begin_unwind` will be available to place a breakpoint on to halt
/// when a panic is happening. This idea was taken from panic_halt crate.
#[inline(never)]
#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    crate::println!("{}", info);
    loop {}
}

/// First candidate: a basic `memcmp` with early exits that will act
/// as a reference for fault testing.
/// It is never inlined to prevent some optimisations in ['compare_pin_double']
/// where it is explicitly called twice to avoid single faults.
#[inline(never)]
pub fn compare_pin(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    let mut good = true;
    for i in 0..ref_pin.len() {
        if user_pin[i] != ref_pin[i] {
            good = false;
        }
    }
    good
}

/// The easy way to fix against single fault injections. Does it work?
#[inline(never)]
pub fn compare_pin_double(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    if compare_pin(user_pin, ref_pin) {
        compare_pin(ref_pin, user_pin)
    } else {
        false
    }
}

/// The easy way to fix against single fault injections. Does it work?
#[inline(always)]
pub fn compare_pin_double_inline(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    if compare_pin(user_pin, ref_pin) {
        compare_pin(ref_pin, user_pin)
    } else {
        false
    }
}

/// This one is out of curiosity because it is difficult (to me) to anticipate
/// how this will be compiled and how it would naturally resist to attacks.
/// Also contains an otherwise important fix: it does not have an early exit
/// and should be constant time.
#[inline(never)]
pub fn compare_pin_fp(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    user_pin
        .iter()
        .zip(ref_pin.iter())
        .fold(0, |acc, (a, b)| acc | (a ^ b))
        == 0
}

/// Variant which is a bit more robust
#[inline(never)]
pub fn compare_pin_fp_variant(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    user_pin
        .iter()
        .zip(ref_pin.iter())
        .fold(true, |acc, (a, b)| acc & (a == b))
        == true
}

/// The goal of this library would be to provide a comparison function
/// that is tested against faults in a continuous integration manner.
/// The better way to provide it would be as a special type/struct
/// that reimplements its own 'PartialEq' so that it can transparently
/// be used externally, without having to worry about invoking correctly
/// or at the right place.
/// The user would only need to wrap the sensitive contents in this type
/// and it would ideally be sufficient.
pub struct IntegrityProtected<T: PartialEq>(pub T);

/// We need this auxiliary function to force non-inlining of
/// the actual low-level comparison
#[inline(never)]
pub fn compare_never_inlined<T: PartialEq>(a: T, b: T) -> bool {
    // For other security reasons, one should hope this comparison
    // is constant time.
    a == b
}

impl<T: PartialEq> PartialEq<&T> for IntegrityProtected<T> {
    /// The core of the countermeasure:
    /// compare twice, and return true only when both comparison
    /// succeeded
    /// Always inline because otherwise the call to `eq()` could
    /// be skipped.
    fn eq(&self, rhs: &&T) -> bool {
        if compare_never_inlined(rhs, &&self.0) {
            if compare_never_inlined(&self.0, rhs) {
                true
            } else {
                // Can only reach this branch when faulted
                // perhaps a `panic!()` is more appropriate
                // or an infinite loop, ...
                false
            }
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::assert_eq_err as assert_eq;
    use crate::test_utils::TestType;
    use testmacro::test_item as test;

    const CORRECT_PIN: [u8; 4] = [1, 2, 3, 4];

    #[test]
    fn valid_pin() {
        assert_eq!(compare_pin(&[1, 2, 3, 4], &CORRECT_PIN), true);
    }

    #[test]
    fn invalid_pin() {
        assert_eq!(compare_pin(&[0, 0, 0, 0], &CORRECT_PIN), false);
    }

    #[test]
    fn valid_pin_fp() {
        assert_eq!(compare_pin_fp(&[1, 2, 3, 4], &CORRECT_PIN), true);
    }

    #[test]
    fn invalid_pin_fp() {
        assert_eq!(compare_pin_fp(&[0, 0, 0, 0], &CORRECT_PIN), false);
    }

    #[test]
    fn valid_pin_double() {
        assert_eq!(compare_pin_double(&[1, 2, 3, 4], &CORRECT_PIN), true);
    }

    #[test]
    fn invalid_pin_double() {
        assert_eq!(compare_pin_double(&[0, 0, 0, 0], &CORRECT_PIN), false);
    }

    #[test]
    fn valid_safe_trait() {
        let ref_pin = IntegrityProtected(CORRECT_PIN);
        assert_eq!(ref_pin == &[1, 2, 3, 4], true);
    }

    #[test]
    fn invalid_safe_trait() {
        let ref_pin = IntegrityProtected(CORRECT_PIN);
        assert_eq!(ref_pin == &[0; 4], false);
    }
}

#[cfg(test)]
mod tests_fi {
    use super::*;
    use rust_fi::{assert_eq, rust_fi_nominal_behavior, rust_fi_faulted_behavior};

    const CORRECT_PIN: [u8; 4] = [1, 2, 3, 4];
    const CORRECT_PIN_PROTECTED: crate::IntegrityProtected<[u8; 4]> =
        crate::IntegrityProtected([1, 2, 3, 4]);

    #[no_mangle]
    #[inline(never)]
    fn test_fi_simple() {
        assert_eq!(compare_pin(&[0; 4], &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_double() {
        let user_pin = [0; 4];
        assert_eq!(compare_pin_double(&user_pin, &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_double_inline() {
        let user_pin = [0; 4];
        assert_eq!(compare_pin_double_inline(&user_pin, &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_simple_fp() {
        assert_eq!(compare_pin_fp(&[0; 4], &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_simple_fp2() {
        assert_eq!(compare_pin_fp(&[1, 0, 0, 0], &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_simple_fp_variant() {
        assert_eq!(compare_pin_fp_variant(&[0; 4], &CORRECT_PIN), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_hard() {
        assert_eq!((CORRECT_PIN_PROTECTED == &[0; 4]), false);
    }

    #[no_mangle]
    #[inline(never)]
    fn test_fi_hard2() {
        let ref_pin = crate::IntegrityProtected([
            1, 8, 9, 2, 3, 1, 3, 2, 1, 0, 2, 23, 29381, 281, 283, 172, 381, 280,
        ]);
        assert_eq!((ref_pin == &[1; 18]), false);
    }

    #[cfg(feature = "test_fi")]
    pub fn run_all() {
        use cortex_m_semihosting::debug::{self, EXIT_SUCCESS};
        test_fi_simple();
        test_fi_double();
        test_fi_double_inline();
        test_fi_simple_fp();
        test_fi_simple_fp2();
        test_fi_simple_fp_variant();
        test_fi_hard();
        test_fi_hard2();
        debug::exit(EXIT_SUCCESS);
    }
}

#[cfg(test)]
#[no_mangle]
pub fn _start() -> ! {
    #[cfg(not(feature = "test_fi"))]
    test_main();

    #[cfg(feature = "test_fi")]
    tests_fi::run_all();

    loop {}
}
