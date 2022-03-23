#![no_std]
#![no_main]

use pin_verif::*;
use test_fi_macro::test_fi;

#[no_mangle]
#[inline(never)]
fn faulted_return() {
    println!("successfully faulted");
}

#[no_mangle]
#[inline(never)]
fn nominal_behavior() {
    println!("nominal behavior");
}

const REF_PIN: [u8; 4] = [1, 2, 3, 4];

#[test_fi]
pub fn simple() {
    if compare_pin(&[0; 4], &REF_PIN) == false {
        nominal_behavior()
    } else {
        faulted_return()
    }
}

#[test_fi]
pub fn double_call() {
    let user_pin = [0; 4];
    if compare_pin(&user_pin, &REF_PIN) == false {
        nominal_behavior()
    } else {
        if compare_pin(&REF_PIN, &user_pin) == false {
            nominal_behavior()
        } else {
            faulted_return()
        }
    }
}

#[test_fi]
pub fn simple_fp() {
    if compare_pin_fp(&[0; 4], &REF_PIN) == false {
        nominal_behavior()
    } else {
        faulted_return()
    }
}

#[test_fi]
pub fn simple_fp2() {
    if compare_pin_fp(&[1, 0, 0, 0], &REF_PIN) == false {
        nominal_behavior()
    } else {
        faulted_return()
    }
}

const REFPIN: pin_verif::IntegrityProtected<[u8; 4]> = pin_verif::IntegrityProtected(REF_PIN);

#[test_fi]
pub fn hard() {
    if (REFPIN == &[0; 4]) == false {
        nominal_behavior()
    } else {
        faulted_return()
    }
}

#[test_fi]
pub fn hard2() {
    let ref_pin = pin_verif::IntegrityProtected([
        1, 8, 9, 2, 3, 1, 3, 2, 1, 0, 2, 23, 29381, 281, 283, 172, 381, 280,
    ]);
    if (ref_pin == &[1; 18]) == false {
        nominal_behavior()
    } else {
        faulted_return()
    }
}

#[no_mangle]
pub fn _start() {
    simple();
    double_call();
    simple_fp();
    simple_fp2();
    hard();
    hard2();
}
