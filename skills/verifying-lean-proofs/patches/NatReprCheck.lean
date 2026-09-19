import Export
def main : IO Unit := do
  let mut bad := 0
  let mut x : Nat := 12345678901234567
  for i in [0:3000] do
    x := (x * 6364136223846793005 + 1442695040888963407) % (2^64)
    let n := (x + 1) ^ (1 + i % 40) * (x % 7 + 1) + i
    if natToDecStr n != toString n then bad := bad + 1
  for n in [0, 1, 999999999999999999, 1000000000000000000, 10^36-1, 10^36, 10^72, 10^72-1, 2^200, 2^5000, 10^100 - 1] do
    if natToDecStr n != toString n then bad := bad + 1
  IO.println s!"mismatches: {bad}"
