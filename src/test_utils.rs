#[macro_export]
macro_rules! assert_eq_err {
    ($left:expr, $right:expr) => {{
        match (&$left, &$right) {
            (left_val, right_val) => {
                if !(*left_val == *right_val) {
                    $crate::println!("assertion failed: left != right");
                    return Err(());
                }
            }
        }
    }};
}

pub struct TestType {
    pub modname: &'static str,
    pub name: &'static str,
    pub f: fn() -> Result<(), ()>,
}

use crate::{print,println};
pub fn test_runner(tests: &[&TestType]) {
    println!("--- {} tests ---", tests.len());
    for t in tests {
        match (t.f)() {
            Ok(()) => print!("\x1b[1;32m   ok   \x1b[0m"),
            Err(()) => print!("\x1b[1;31m  fail  \x1b[0m"),
        }
        println!("{}::{}", t.modname, t.name);
    }
}