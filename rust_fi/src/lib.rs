#![no_std]

#[no_mangle]
#[inline(never)]
pub fn rust_fi_nominal_behavior() {
    panic!("nominal behavior")
}

#[no_mangle]
#[inline(never)]
pub fn rust_fi_faulted_behavior() {
    panic!("faulted behavior")
}

/// Custom assert_eq macro to differentiate between a panic inside the
/// called function and a faulted behavior
#[macro_export]
macro_rules! assert_eq {
    ($left:expr, $right:expr $(,)?) => {{
        // Deref coercion
        match (&$left, &$right) {
            (left_val, right_val) => {
                if *left_val == *right_val {
                    rust_fi_nominal_behavior();
                } else {
                    rust_fi_faulted_behavior();
                }
            }
        }
    }};
}
