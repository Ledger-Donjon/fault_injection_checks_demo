#![no_main]
#![no_std]

// TODO: this macro should be moved to another crate
#[macro_export]
macro_rules! tvla_target {
    (|$fixed_random:ident: u32| $body:block) => {
        use unroll::unroll_for_loops;

        /// Auto-generated function
        #[no_mangle]
        #[inline(never)]
        #[unroll_for_loops]
        pub extern "C" fn rust_tvla_test_trace_begin() {
            use cortex_m::asm;
            for _ in 0..100 {
                asm::nop();
            }
        }

        /// Auto-generated function
        #[no_mangle]
        #[inline(never)]
        #[unroll_for_loops]
        pub extern "C" fn rust_tvla_test_trace_end() {
            use cortex_m::asm;
            // 101!=100 instructions to make _begin and _end distinct
            for _ in 0..101 {
                asm::nop();
            }
        }

        /// Auto-generated function
        #[no_mangle]
        #[inline(never)]
        pub extern "C" fn rust_tvla_test_trace($fixed_random: u32) {
            $body
        }
    };
}

use aes::cipher::{BlockEncrypt, KeyInit};
use aes::Aes128;
use panic_halt as _;

tvla_target!(|fixed_random: u32| {
    // Convert fixed_random in 128-bit block
    let mut block = [0u8; 16];
    block[0..4].copy_from_slice(&fixed_random.to_be_bytes());
    block[4..8].copy_from_slice(&fixed_random.to_be_bytes());
    block[8..12].copy_from_slice(&fixed_random.to_be_bytes());
    block[12..16].copy_from_slice(&fixed_random.to_be_bytes());

    let key = [
        0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF, 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE,
        0xF0,
    ];
    let cipher = Aes128::new(&key.into());

    rust_tvla_test_trace_begin(); // trace from this point
    cipher.encrypt_block(&mut block.into());
    rust_tvla_test_trace_end();
});

#[no_mangle]
pub fn _start() -> ! {
    rust_tvla_test_trace(0x12345678);
    rust_tvla_test_trace(0xDA39A3EE);
    loop {}
}
