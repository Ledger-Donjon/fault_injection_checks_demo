#![cfg_attr(not(test), no_std)]

pub mod bool;

/// The goal of this library would be to provide a comparison function
/// that is tested against faults in a continuous integration manner.
/// The better way to provide it would be as a special type/struct
/// that reimplements its own 'PartialEq' so that it can transparently
/// be used externally, without having to worry about invoking correctly
/// or at the right place.
/// The user would only need to wrap the sensitive contents in this type
/// and it would ideally be sufficient.
pub struct Protected<T: PartialEq>(pub T);

/// We need this auxiliary function to force non-inlining of
/// the actual low-level comparison
#[inline(never)]
fn compare_never_inlined<T: PartialEq>(a: T, b: T) -> bool {
    // For other security reasons, one should hope this comparison
    // is constant time.
    a == b
}

impl<T: PartialEq> PartialEq<&T> for Protected<T> {
    /// The core of the countermeasure:
    /// compare twice, and return true only when both comparison
    /// succeeded
    /// Always inline because otherwise the call to `eq()` could
    /// be skipped.
    #[inline(always)]
    fn eq(&self, rhs: &&T) -> bool {
        if compare_never_inlined(rhs, &&self.0) {
            if compare_never_inlined(&self.0, rhs) {
                true
            } else {
                // Can only reach this branch when faulted
                panic!("fault")
            }
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const CORRECT_PIN: [u8; 4] = [1, 2, 3, 4];

    #[test]
    fn protected_true() {
        let ref_pin = Protected(CORRECT_PIN);
        assert_eq!(ref_pin == &[1, 2, 3, 4], true);
    }

    #[test]
    fn protected_false() {
        let ref_pin = Protected(CORRECT_PIN);
        assert_eq!(ref_pin == &[0; 4], false);
    }
}
