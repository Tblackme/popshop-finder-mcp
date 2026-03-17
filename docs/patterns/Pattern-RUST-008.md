# Pattern-RUST-008: Rust 2021 Edition Benchmark Configuration

**CREATED:** 2025-11-02
**CATEGORY:** Uncategorized
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.80
**APPLICABILITY:** All Rust 2021 projects using Criterion benchmarks
**STATUS:** Skeleton created (full implementation pending P1-012)
**RELATED:** PATTERN-RUST-003

---




## PROBLEM

Cargo error when adding Criterion benchmarks to Rust 2021 edition project:

```
error: couldn't find required key `path` in table `bench.pattern_matching`
  --> Cargo.toml:21:1
   |
21 | [[bench]]
   | ^^^^^^^^^
```

**ROOT CAUSE:**
Rust 2021 edition requires explicit `path` field in `[[bench]]` sections. Previous editions (2018, 2015) would infer the path from the benchmark name, but 2021 edition enforces explicitness.

**WHY THIS MATTERS:**
Benchmarks are critical for validating performance targets (e.g., <50ms pattern matching for 10k patterns). Broken benchmark configuration blocks performance validation.

---

## SOLUTION

**Add explicit `path` and `harness = false` to [[bench]] sections:**

```toml
# Cargo.toml

[package]
name = "aetherlight-core"
version = "0.1.0"
edition = "2021"  # ← Rust 2021 edition requires explicit paths

# ... dependencies ...

[dev-dependencies]
criterion = "0.5"

[[bench]]
name = "pattern_matching"           # Benchmark name (used in `cargo bench --bench pattern_matching`)
path = "benches/pattern_matching.rs"  # ← REQUIRED in 2021 edition
harness = false                      # ← REQUIRED for Criterion (disables default harness)
```

**Benchmark file structure:**
```
crates/aetherlight-core/
├── Cargo.toml
├── benches/
│   └── pattern_matching.rs  # ← Path referenced in Cargo.toml
└── src/
    └── lib.rs
```

---

## WHEN TO USE

### Always Use This Pattern When:
- Project uses `edition = "2021"` in Cargo.toml
- Adding Criterion benchmarks (`criterion = "0.5"` in dev-dependencies)
- Benchmark files in `benches/` directory

### Not Needed When:
- Using Rust 2018 or 2015 edition (path inference works)
- Using built-in benchmark harness (`#[bench]` with nightly Rust)
- Not using Criterion framework

---

## IMPLEMENTATION

### Full Benchmark Configuration

```toml
# Cargo.toml

[package]
name = "aetherlight-core"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib", "staticlib", "rlib"]

[dependencies]
serde = { version = "1.0", features = ["derive"] }
uuid = { version = "1.6", features = ["v4", "serde"] }
chrono = { version = "0.4", features = ["serde"] }

[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true

[[bench]]
name = "pattern_matching"
path = "benches/pattern_matching.rs"
harness = false  # Required for Criterion (uses custom main function)
```

### Benchmark File Template

```rust
// benches/pattern_matching.rs

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use aetherlight_core::{Pattern, PatternMatcher};

/**
 * Benchmark: Pattern matching performance
 *
 * DESIGN DECISION: Benchmark with varying pattern counts (100, 1k, 10k)
 * WHY: Validate O(n) scaling and ensure <50ms target for 10k patterns
 *
 * REASONING CHAIN:
 * 1. Create pattern library with N patterns
 * 2. Execute find_matches() with realistic query
 * 3. Measure time (excluding library initialization)
 * 4. Repeat for different N values
 * 5. Validate performance targets met
 *
 * PATTERN: Pattern-RUST-008 (Benchmark configuration)
 * RELATED: SOP-004 (Performance targets)
 */
fn benchmark_pattern_matching(c: &mut Criterion) {
    let mut group = c.benchmark_group("pattern_matching");

    for pattern_count in [100, 1000, 10000] {
        // Setup: Create pattern library
        let mut matcher = PatternMatcher::new();
        for i in 0..pattern_count {
            let pattern = Pattern::new(
                format!("Pattern {}", i),
                format!("Content for pattern {}", i),
                vec![format!("tag-{}", i)],
            );
            matcher.add_pattern(pattern).unwrap();
        }

        // Benchmark: Find matches
        group.bench_with_input(
            BenchmarkId::from_parameter(pattern_count),
            &pattern_count,
            |b, _| {
                b.iter(|| {
                    let results = matcher.find_matches(
                        black_box("How do I handle errors in Rust?"),
                        black_box(5),
                    );
                    black_box(results)
                });
            },
        );
    }

    group.finish();
}

criterion_group!(benches, benchmark_pattern_matching);
criterion_main!(benches);
```

### Running Benchmarks

```bash
# Run all benchmarks
cargo bench

# Run specific benchmark
cargo bench --bench pattern_matching

# Save baseline for comparison
cargo bench -- --save-baseline before

# Compare against baseline
# (make code changes)
cargo bench -- --baseline before

# Generate HTML report
cargo bench
# Open target/criterion/report/index.html
```

---

## ALTERNATIVES CONSIDERED

### Alternative 1: Use Built-In Benchmark Harness
**Description:** Use Rust's built-in `#[bench]` attribute instead of Criterion.

```rust
#![feature(test)]
extern crate test;

#[bench]
fn benchmark_pattern_matching(b: &mut test::Bencher) {
    b.iter(|| {
        // benchmark code
    });
}
```

**Pros:**
- No external dependencies (built-in)
- No Cargo.toml configuration needed

**Cons:**
- **Requires nightly Rust** (unstable feature)
- Less statistical analysis than Criterion
- No HTML reports
- No baseline comparison
- Project targets stable Rust

**Why Rejected:** Criterion is industry standard and works on stable Rust.

### Alternative 2: Inline Benchmarks
**Description:** Put benchmarks in `src/` directory with `#[cfg(test)]` guards.

**Pros:**
- No separate benchmark directory
- Can access private functions

**Cons:**
- Bloats compiled binary (benchmarks included in lib)
- Slower compilation (benchmarks compiled with main crate)
- Criterion requires `harness = false` (cannot be inline)

**Why Rejected:** Separate `benches/` directory is Rust best practice.

### Alternative 3: Custom Benchmark Harness
**Description:** Write custom main function for benchmarks without Criterion.

```rust
fn main() {
    let start = std::time::Instant::now();
    // benchmark code
    let elapsed = start.elapsed();
    println!("Time: {:?}", elapsed);
}
```

**Pros:**
- Full control over benchmark execution
- No dependencies

**Cons:**
- No statistical analysis (mean, median, std dev)
- No warmup iterations
- No outlier detection
- Reinventing the wheel

**Why Rejected:** Criterion provides professional-grade benchmarking infrastructure.

---

## RELATED PATTERNS

- **Pattern-RUST-003:** Test-driven development setup (testing pattern)
- **SOP-004:** Performance targets (benchmark validation)
- **Pattern-001:** Rust Core + Language Bindings (performance critical)

---

## EXAMPLES IN CODEBASE

### Benchmark Configuration
- **File:** `crates/aetherlight-core/Cargo.toml:21-24`
- **Content:**
  ```toml
  [[bench]]
  name = "pattern_matching"
  path = "benches/pattern_matching.rs"
  harness = false
  ```

### Benchmark Implementation
- **File:** `crates/aetherlight-core/benches/pattern_matching.rs`
- **Status:** Skeleton created (full implementation pending P1-012)

---

## DEBUGGING TIPS

### If You See "couldn't find required key `path`":
1. Check `edition = "2021"` in Cargo.toml
2. Add explicit `path = "benches/benchmark_name.rs"` to `[[bench]]` section
3. Verify file exists at specified path

### If You See "unresolved import `criterion`":
1. Add Criterion to dev-dependencies: `criterion = "0.5"`
2. Ensure you're running `cargo bench` (not `cargo test`)
3. Check feature flags: `features = ["html_reports"]` is optional

### If Benchmarks Don't Run:
1. Verify `harness = false` in `[[bench]]` section
2. Check benchmark file has `criterion_main!(benches);` at end
3. Ensure criterion_group! macro includes all benchmark functions

### If Performance Differs Between Runs:
1. Run benchmarks multiple times: `cargo bench --bench pattern_matching -- --sample-size 100`
2. Disable CPU frequency scaling (Linux: `sudo cpupower frequency-set --governor performance`)
3. Close background applications
4. Use baseline comparison to validate changes: `cargo bench -- --baseline before`

---

## PERFORMANCE TARGETS

### ÆtherLight Performance Targets (SOP-004)

| Metric | Target | Validation |
|--------|--------|------------|
| Pattern matching (100 patterns) | <5ms | `cargo bench` |
| Pattern matching (1k patterns) | <25ms | `cargo bench` |
| Pattern matching (10k patterns) | <50ms | `cargo bench` |
| Memory usage (10k patterns) | <100MB | `cargo bench --bench memory` |
| Cold start (first match) | <100ms | Integration test |

### How to Validate Targets Met

```bash
# Run benchmarks
cargo bench --bench pattern_matching

# Check output for:
# pattern_matching/10000  time: [47.2 ms 47.8 ms 48.4 ms]
#                         ↑ Must be <50ms

# If target not met, profile with flamegraph:
cargo install flamegraph
cargo flamegraph --bench pattern_matching
# Opens flamegraph.svg in browser
```

---

## FUTURE IMPROVEMENTS

### Potential Enhancements:
1. **Memory benchmarks:** Add benchmarks for memory usage (via cargo-bench-memory crate)
2. **Parallel benchmarks:** Benchmark thread-safe pattern matcher with rayon
3. **Regression detection:** Add CI job that fails if benchmarks regress >10%
4. **Comparison reports:** Generate comparison report (before/after changes)

### Known Limitations:
1. Criterion adds ~1-2 second warmup overhead per benchmark
2. HTML reports stored in `target/` (can grow large over time, clean with `cargo clean`)
3. Benchmark results vary with CPU frequency, background load, etc.

---

## RELATED DOCUMENTATION

### Criterion Documentation:
- [Criterion.rs User Guide](https://bheisler.github.io/criterion.rs/book/)
- [Benchmark Best Practices](https://bheisler.github.io/criterion.rs/book/user_guide/benchmarking_tips.html)

### Rust Benchmarking:
- [Cargo Benchmarks](https://doc.rust-lang.org/cargo/commands/cargo-bench.html)
- [The Rust Performance Book](https://nnethercote.github.io/perf-book/)

---

**LAST UPDATED:** 2025-10-04
**PATTERN ID:** RUST-008
**STATUS:** Validated (benchmark configuration works)
**RELATED TASKS:** P1-003 (Test harness setup), P1-012 (Documentation + benchmarks)

---

**Chain of Thought:**
This pattern was discovered while setting up Criterion benchmarks (P1-003). Initial Cargo.toml configuration failed with "couldn't find required key `path`" error. Investigation revealed Rust 2021 edition requires explicit paths in [[bench]] sections. Pattern extracted to prevent future confusion about Criterion configuration.

**Impact:** Enables performance validation for Phase 1 targets (<50ms pattern matching). Without this pattern, benchmarks would not compile, blocking performance validation (P1-012).
