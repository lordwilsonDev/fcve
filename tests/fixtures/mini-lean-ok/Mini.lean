/-! Tiny Mathlib-free fixture for FCVE's smoke test: two axiom-free theorems. -/
theorem mini_add : 2 + 2 = 4 := rfl
theorem mini_comm (a b : Nat) : a + b = b + a := Nat.add_comm a b
