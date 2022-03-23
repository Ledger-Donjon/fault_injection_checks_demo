#![no_std]
#![no_main]

use pin_verif::*;
use test_fi_macro::test_fi;

#[no_mangle]
#[inline(never)]
fn nominal_behavior() {
    println!("nominal behavior")
}

const REF_PIN: [u8; 4] = [1, 2, 3, 4];

#[test_fi]
pub fn simple() {
    assert_eq!(compare_pin(&[0; 4], &REF_PIN), false);
    nominal_behavior()
}

#[test_fi]
pub fn double() {
    let user_pin = [0; 4];
    assert_eq!(compare_pin_double(&user_pin, &REF_PIN), false);
    nominal_behavior()
}

#[test_fi]
pub fn simple_fp() {
    assert_eq!(compare_pin_fp(&[0; 4], &REF_PIN), false);
    nominal_behavior()
}

#[test_fi]
pub fn simple_fp2() {
    assert_eq!(compare_pin_fp(&[1, 0, 0, 0], &REF_PIN), false);
    nominal_behavior()
}

const REFPIN: pin_verif::IntegrityProtected<[u8; 4]> = pin_verif::IntegrityProtected(REF_PIN);

#[test_fi]
pub fn hard() {
    assert_eq!((REFPIN == &[0; 4]), false);
    nominal_behavior()
}

#[test_fi]
pub fn hard2() {
    let ref_pin = pin_verif::IntegrityProtected([
        1, 8, 9, 2, 3, 1, 3, 2, 1, 0, 2, 23, 29381, 281, 283, 172, 381, 280,
    ]);
    assert_eq!((ref_pin == &[1; 18]), false);
    nominal_behavior()
}

#[no_mangle]
pub fn _start() {
    simple();
    double();
    simple_fp();
    simple_fp2();
    hard();
    hard2();

    use cortex_m_semihosting::debug::{self, EXIT_SUCCESS};
    debug::exit(EXIT_SUCCESS);
}
