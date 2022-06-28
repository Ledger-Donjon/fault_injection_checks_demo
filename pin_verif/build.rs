//! This build script copies the `script.ld` file from the crate root into
//! a directory where the linker can always find it at build time.

use std::env;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

fn main() {
    // Put `script.ld` in our output directory and ensure it's
    // on the linker search path.
    let out = &PathBuf::from(env::var_os("OUT_DIR").unwrap());
    File::create(out.join("script.ld"))
        .unwrap()
        .write_all(include_bytes!("script.ld"))
        .unwrap();
    println!("cargo:rustc-link-search={}", out.display());
}
