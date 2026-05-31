-- A tiny agda-stdlib-backed development used by agdablueprint's end-to-end
-- test. Unlike tests/fixtures/agda-project (which imports nothing), this module
-- `depend:`s on standard-library, so checking it exercises Agda's library
-- resolution path (under Nix: `agda.withPackages [ standard-library ]`).
module Sum where

open import Data.Nat using (ℕ; zero; suc; _+_)
open import Data.Nat.Properties using (+-comm; +-identityʳ)
open import Relation.Binary.PropositionalEquality using (_≡_; refl; cong)

-- The double of a natural number.
double : ℕ → ℕ
double n = n + n

-- double zero is zero.
double-zero : double zero ≡ zero
double-zero = refl

-- Addition is commutative (re-exported from the standard library for the
-- blueprint to point at via \agda{Sum.+-comm′}).
+-comm′ : ∀ (m n : ℕ) → m + n ≡ n + m
+-comm′ = +-comm
