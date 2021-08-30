#![no_std]
#![cfg_attr(test, no_main)]
#![feature(custom_test_frameworks)]
#![reexport_test_harness_main = "test_main"]
#![test_runner(test_utils::test_runner)]
#![feature(asm)]

pub mod qemu;

#[cfg(test)]
mod test_utils;

use core::panic::PanicInfo;
#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    crate::println!("{}", info);
    loop {}
}

pub fn compare_pin(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    for (digit_user, digit_ref) in user_pin.iter().zip(ref_pin.iter()) {
        if digit_user != digit_ref {
            return false
        }
    } 
    return true 
}

pub fn compare_pin_fp(user_pin: &[u8], ref_pin: &[u8]) -> bool {
    user_pin
        .iter()
        .zip(ref_pin.iter())
        .fold(0, |acc, (a, b)| acc | (a ^ b))
        == 0
}

pub fn safe_compare_pin(user_pin: &[u8], ref_pin: &[u8]) -> u8 {
    let mut res0 = 0;
    let mut res1 = 0;
    let len = ref_pin.len();
    for i in 0..len {
        res0 |= user_pin[i] ^ ref_pin[i];
        res1 |= user_pin[i] ^ ref_pin[i];
    }
    res0 | res1 
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_utils::TestType;
    use crate::assert_eq_err as assert_eq;
    use testmacro::test_item as test;

    const CORRECT_PIN: [u8; 4] = [1,2,3,4];

    #[test]
    fn valid_pin() {
        assert_eq!(compare_pin(&[1,2,3,4], &CORRECT_PIN), true);
    }

    #[test]
    fn invalid_pin() {
        assert_eq!(compare_pin(&[0,0,0,0], &CORRECT_PIN), false);
    }

    #[test]
    fn valid_pin_fp() {
        assert_eq!(compare_pin_fp(&[1,2,3,4], &CORRECT_PIN), true);
    }

    #[test]
    fn invalid_pin_fp() {
        assert_eq!(compare_pin_fp(&[0,0,0,0], &CORRECT_PIN), false);
    }

    #[test]
    fn valid_pin_safe() {
        assert_eq!(safe_compare_pin(&[1,2,3,4], &CORRECT_PIN) == 0, true);
    }

    #[test]
    fn invalid_pin_safe() {
        assert_eq!(safe_compare_pin(&[0,0,0,0], &CORRECT_PIN) == 0, false);
    }
}


#[cfg(test)]
#[no_mangle]
pub fn _start() -> ! {

    #[cfg(test)]
    test_main();

    qemu::exit();
}
