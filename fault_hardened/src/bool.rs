use core::cmp::PartialEq;
use core::default::Default;
use core::fmt::{Debug, Display};
use core::ops::{BitAnd, BitAndAssign, BitOr, BitOrAssign, BitXor, BitXorAssign, Not};

// Bool is a fault-resistent boolean type.
// If during an operation an unexpected value is found, panic will be raised.
#[derive(Clone, Copy, Eq)]
pub struct Bool(u32);

// TRUE is not the opposite of FALSE to force the compiler to no use NEG
// First and last bit is 0, in case of boolean casting
// One is not the shift of the other one, in case of shifting
const TRUE: u32 = 0b0010_1010_1010_1010_1010_1110_1010_1010;
const FALSE: u32 = 0b0110_0101_0101_0110_1100_0011_0101_1100;

impl From<Bool> for bool {
    #[inline(always)]
    fn from(source: Bool) -> bool {
        if (source.0 != TRUE) & (source.0 != FALSE) {
            panic!() // Unexpected state
        }
        source.0 == TRUE
    }
}

impl From<bool> for Bool {
    #[inline(always)]
    fn from(source: bool) -> Bool {
        match source {
            true => Self(TRUE),
            false => Self(FALSE),
        }
    }
}

impl Default for Bool {
    fn default() -> Self {
        Self(FALSE)
    }
}

impl Debug for Bool {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "Bool<{:?}>", bool::from(*self))
    }
}

impl Display for Bool {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "{}", bool::from(*self))
    }
}

impl BitAnd for Bool {
    type Output = Self;

    #[inline(always)]
    fn bitand(self, rhs: Self) -> Self::Output {
        match (self.0, rhs.0) {
            (TRUE, TRUE) => Self(TRUE),
            (FALSE, FALSE) | (FALSE, TRUE) | (TRUE, FALSE) => Self(FALSE),
            _ => panic!(),
        }
    }
}

impl BitAndAssign for Bool {
    #[inline(always)]
    fn bitand_assign(&mut self, rhs: Self) {
        *self = *self & rhs
    }
}

impl BitOr for Bool {
    type Output = Self;

    #[inline(always)]
    fn bitor(self, rhs: Self) -> Self::Output {
        match (self.0, rhs.0) {
            (TRUE, TRUE) | (FALSE, TRUE) | (TRUE, FALSE) => Self(TRUE),
            (FALSE, FALSE) => Self(FALSE),
            _ => panic!(),
        }
    }
}

impl BitOrAssign for Bool {
    #[inline(always)]
    fn bitor_assign(&mut self, rhs: Self) {
        *self = *self | rhs;
    }
}

impl BitXor for Bool {
    type Output = Self;

    #[inline(always)]
    fn bitxor(self, rhs: Self) -> Self::Output {
        match (self.0, rhs.0) {
            (TRUE, TRUE) | (FALSE, FALSE) => Self(FALSE),
            (TRUE, FALSE) | (FALSE, TRUE) => Self(TRUE),
            _ => panic!(),
        }
    }
}

impl BitXorAssign for Bool {
    #[inline(always)]
    fn bitxor_assign(&mut self, rhs: Self) {
        *self = *self ^ rhs;
    }
}

impl Not for Bool {
    type Output = Self;

    #[inline(always)]
    fn not(self) -> Self::Output {
        match self.0 {
            TRUE => Self(FALSE),
            FALSE => Self(TRUE),
            _ => panic!(),
        }
    }
}

impl PartialEq for Bool {
    #[inline(always)]
    fn eq(&self, other: &Self) -> bool {
        match (self.0, other.0) {
            (TRUE, TRUE) | (FALSE, FALSE) => true,
            (TRUE, FALSE) | (FALSE, TRUE) => false,
            _ => panic!(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn and_false_false() {
        assert_eq!(Bool::from(false) & Bool::from(false), Bool::from(false));
    }

    #[test]
    fn and_false_true() {
        assert_eq!(Bool::from(false) & Bool::from(true), Bool::from(false));
    }

    #[test]
    fn and_true_true() {
        assert_eq!(Bool::from(true) & Bool::from(true), Bool::from(true));
    }

    #[test]
    fn or_false_false() {
        assert_eq!(Bool::from(false) | Bool::from(false), Bool::from(false));
    }

    #[test]
    fn or_false_true() {
        assert_eq!(Bool::from(false) | Bool::from(true), Bool::from(true));
    }

    #[test]
    fn or_true_true() {
        assert_eq!(Bool::from(true) | Bool::from(true), Bool::from(true));
    }

    #[test]
    fn xor_false_false() {
        assert_eq!(Bool::from(false) ^ Bool::from(false), Bool::from(false));
    }

    #[test]
    fn xor_false_true() {
        assert_eq!(Bool::from(false) ^ Bool::from(true), Bool::from(true));
    }

    #[test]
    fn xor_true_true() {
        assert_eq!(Bool::from(true) ^ Bool::from(true), Bool::from(false));
    }

    #[test]
    fn not_false() {
        assert_eq!(!Bool::from(false), Bool::from(true));
    }

    #[test]
    fn not_true() {
        assert_eq!(!Bool::from(true), Bool::from(false));
    }
}
