use core::cmp::PartialEq;
use core::default::Default;
use core::fmt::{Debug, Display};
use core::ops::{BitAnd, BitAndAssign, BitOr, BitOrAssign, BitXor, BitXorAssign, Not};

// BoolProtected is a fault-resistent boolean type.
// False is represented by 0b01100110 and true by 0b00101010.
// If during an operation an unexpected value is found, panic will be raised.
#[derive(Clone, Copy, Eq)]
pub struct BoolProtected(u32);

// TRUE is not the opposite of FALSE to force the compiler to no use NEG
// First and last bit is 0, in case of boolean casting
// One is not the shift of the other one, in case of shifting
const TRUE: u32 = 0b0010_1010_1010_1010_1010_1110_1010_1010;
const FALSE: u32 = 0b0110_0101_0101_0110_1100_0011_0101_1100;

impl From<BoolProtected> for bool {
    #[inline(always)]
    fn from(source: BoolProtected) -> bool {
        if (source.0 != TRUE) & (source.0 != FALSE) {
            panic!() // Unexpected state
        }
        source.0 == TRUE
    }
}

impl From<bool> for BoolProtected {
    #[inline(always)]
    fn from(source: bool) -> BoolProtected {
        match source {
            true => Self(TRUE),
            false => Self(FALSE),
        }
    }
}

impl Default for BoolProtected {
    fn default() -> Self {
        Self(FALSE)
    }
}

impl Debug for BoolProtected {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "BoolProtected<{:?}>", bool::from(*self))
    }
}

impl Display for BoolProtected {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "{}", bool::from(*self))
    }
}

impl BitAnd for BoolProtected {
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

impl BitAndAssign for BoolProtected {
    #[inline(always)]
    fn bitand_assign(&mut self, rhs: Self) {
        *self = *self & rhs
    }
}

impl BitOr for BoolProtected {
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

impl BitOrAssign for BoolProtected {
    #[inline(always)]
    fn bitor_assign(&mut self, rhs: Self) {
        *self = *self | rhs;
    }
}

impl BitXor for BoolProtected {
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

impl BitXorAssign for BoolProtected {
    #[inline(always)]
    fn bitxor_assign(&mut self, rhs: Self) {
        *self = *self ^ rhs;
    }
}

impl Not for BoolProtected {
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

impl PartialEq for BoolProtected {
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
    use crate::assert_eq_err as assert_eq;
    use crate::test_utils::TestType;
    use testmacro::test_item as test;

    #[test]
    fn test_and_false_false() {
        assert_eq!(
            BoolProtected::from(false) & BoolProtected::from(false),
            BoolProtected::from(false)
        );
    }

    #[test]
    fn test_and_false_true() {
        assert_eq!(
            BoolProtected::from(false) & BoolProtected::from(true),
            BoolProtected::from(false)
        );
    }

    #[test]
    fn test_and_true_true() {
        assert_eq!(
            BoolProtected::from(true) & BoolProtected::from(true),
            BoolProtected::from(true)
        );
    }

    #[test]
    fn test_or_false_false() {
        assert_eq!(
            BoolProtected::from(false) | BoolProtected::from(false),
            BoolProtected::from(false)
        );
    }

    #[test]
    fn test_or_false_true() {
        assert_eq!(
            BoolProtected::from(false) | BoolProtected::from(true),
            BoolProtected::from(true)
        );
    }

    #[test]
    fn test_or_true_true() {
        assert_eq!(
            BoolProtected::from(true) | BoolProtected::from(true),
            BoolProtected::from(true)
        );
    }

    #[test]
    fn test_xor_false_false() {
        assert_eq!(
            BoolProtected::from(false) ^ BoolProtected::from(false),
            BoolProtected::from(false)
        );
    }

    #[test]
    fn test_xor_false_true() {
        assert_eq!(
            BoolProtected::from(false) ^ BoolProtected::from(true),
            BoolProtected::from(true)
        );
    }

    #[test]
    fn test_xor_true_true() {
        assert_eq!(
            BoolProtected::from(true) ^ BoolProtected::from(true),
            BoolProtected::from(false)
        );
    }

    #[test]
    fn test_not_false() {
        assert_eq!(!BoolProtected::from(false), BoolProtected::from(true));
    }

    #[test]
    fn test_not_true() {
        assert_eq!(!BoolProtected::from(true), BoolProtected::from(false));
    }
}
