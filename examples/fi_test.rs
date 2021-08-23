#![no_std]
#![no_main]

use pin_verif::{compare_pin, compare_pin_fp, safe_compare_pin};
use pin_verif::println;

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

#[no_mangle]
#[inline(never)]
pub fn fi_test1() {
	if compare_pin(&[0,0,0,0], &[1,2,3,4]) {
		success();
	} else {
		fail();
	}
}

#[no_mangle]
#[inline(never)]
pub fn fi_test2() {
	if compare_pin_fp(&[0,0,0,0], &[1,2,3,4]) {
		success();
	} else {
		fail();
	}
}

#[no_mangle]
#[inline(never)]
pub fn fi_test3() {
	if compare_pin_fp(&[1,0,0,0], &[1,2,3,4]) {
		success();
	} else {
		fail();
	}
}

#[no_mangle]
#[inline(never)]
pub fn fi_test4() {
	if safe_compare_pin(&[0,0,0,0], &[1,2,3,4]) == 0 {
		success();
	} else {
		fail();
	}
}

#[no_mangle]
pub fn _start() {
	fi_test1();
	fi_test2();
	fi_test3();
	fi_test4();
}