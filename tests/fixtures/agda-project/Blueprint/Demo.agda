-- Self-contained fixture module for agdablueprint's checkdecls tests.
-- Deliberately depends on no library so the test suite needs only `agda`.
module Blueprint.Demo where

data ℕ : Set where
  zero : ℕ
  suc  : ℕ → ℕ

data Even : ℕ → Set where
  even-zero : Even zero
  even-suc  : ∀ {n} → Even n → Even (suc (suc n))

-- A fully formalized statement: zero is even.
zero-even : Even zero
zero-even = even-zero
