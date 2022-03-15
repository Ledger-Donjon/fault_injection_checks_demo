#![no_std]
#![cfg_attr(test, no_main)]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]
#![test_runner(test_utils::test_runner)]

pub mod qemu;

#[cfg(test)]
mod test_utils;

use core::panic::PanicInfo;
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
    for (digit_user, digit_ref) in user_pin.iter().zip(ref_pin.iter()) {
        if digit_user != digit_ref {
            return false;
        }
    }
    return true;
}

/// The easy way to fix against single fault injections. Does it work?
pub fn compare_pin_double(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    if compare_pin(&user_pin, &ref_pin) {
        if compare_pin(&ref_pin, &user_pin) {
            return true;
        } else {
            return false;
        }
    } else {
        return false;
    }
}

/// This one is out of curiosity because it is difficult (to me) to anticipate
/// how this will be compiled and how it would naturally resist to attacks.
/// Also contains an otherwise important fix: it does not have an early exit
/// and should be constant time.
pub fn compare_pin_fp(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    user_pin
        .iter()
        .zip(ref_pin.iter())
        .fold(0, |acc, (a, b)| acc | (a ^ b))
        == 0
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
    #[inline(always)]
    fn eq(&self, rhs: &&T) -> bool {
        if compare_never_inlined(rhs, &&self.0) {
            if compare_never_inlined(&self.0, rhs) {
                return true;
            } else {
                // Can only reach this branch when faulted
                // perhaps a `panic!()` is more appropriate
                // or an infinite loop, ...
                return false;
            }
        } else {
            return false;
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
#[no_mangle]
pub fn _start() -> ! {
    #[cfg(test)]
    test_main();

    qemu::exit();
}
