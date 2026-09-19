/-! FAILURE-INJECTION fixture: this "proof" uses sorry. FCVE must NOT pass it. -/
theorem bad_sorry : 1 = 2 := by sorry
theorem mini_add : 2 + 2 = 4 := rfl
