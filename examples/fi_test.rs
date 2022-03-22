#![no_std]
#![no_main]

use pin_verif::*;

#[no_mangle]
#[inline(never)]
fn success() {
    println!("passed");
}

#[no_mangle]
#[inline(never)]
fn fail() {
    println!("failed");
}

const REF_PIN: [u8; 4] = [1, 2, 3, 4];

#[export_name = "fi_test_simple"]
#[inline(never)]
pub fn simple() {
    if compare_pin(&[0; 4], &REF_PIN) {
        success()
    } else {
        fail()
    }
}

#[export_name = "fi_test_double_call"]
#[inline(never)]
pub fn double_call() {
    let user_pin = [0; 4];
    if compare_pin(&user_pin, &REF_PIN) {
        if compare_pin(&REF_PIN, &user_pin) {
            success()
        } else {
            fail()
        }
    } else {
        fail()
    }
}

#[export_name = "fi_test_simple_fp"]
#[inline(never)]
pub fn simple_fp() {
    if compare_pin_fp(&[0; 4], &REF_PIN) {
        success()
    } else {
        fail()
    }
}

#[export_name = "fi_test_simple_fp2"]
#[inline(never)]
pub fn simple_fp2() {
    if compare_pin_fp(&[1, 0, 0, 0], &REF_PIN) {
        success()
    } else {
        fail()
    }
}

const REFPIN: pin_verif::IntegrityProtected<[u8; 4]> = pin_verif::IntegrityProtected(REF_PIN);

#[export_name = "fi_test_hard"]
#[inline(never)]
pub fn hard() {
    if REFPIN == &[0; 4] {
        success()
    } else {
        fail()
    }
}

#[export_name = "fi_test_hard2"]
#[inline(never)]
pub fn hard2() {
    let ref_pin = pin_verif::IntegrityProtected([
        1, 8, 9, 2, 3, 1, 3, 2, 1, 0, 2, 23, 29381, 281, 283, 172, 381, 280,
    ]);
    if ref_pin == &[1; 18] {
        success()
    } else {
        fail()
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
