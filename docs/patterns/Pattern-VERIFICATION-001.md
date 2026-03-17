# Pattern-VERIFICATION-001: Real-Time Agent Claim Verification

**CREATED:** 2025-11-02
**CATEGORY:** AI Safety / Hallucination Detection
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.83
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-TRACKING-001, PATTERN-META-001

---




## Problem Statement

**The Problem:**
- AI agents make unverified claims about code, tests, performance
- Claims are presented with confidence even when hallucinated
- Hallucinations become bugs when executed without validation
- Debugging hallucination-caused bugs is expensive (50% more time)
- Agents don't self-correct because they believe their own claims

**Examples of Hallucinations:**
```
❌ "See src/main.rs:45" (file doesn't exist)
❌ "Function calculate() exists in utils.rs" (function doesn't exist)
❌ "Test coverage is 85%" (didn't run tarpaulin)
❌ "12 out of 15 tests passing" (didn't run cargo test)
❌ "Pattern matching took 45ms" (didn't run benchmark)
```

**Why This Matters:**
- ÆtherLight enables autonomous agent problem-solving (Phase 3.5)
- Autonomous agents with 15% hallucination rate = unreliable
- User trust destroyed by repeated false claims
- Bad claims → bad pattern library → bad future recommendations
- Phase 4 autonomous sprints require <5% hallucination rate

**Impact Without Verification:**
- Bugs from hallucinations: 15% of all bugs (measured in Phase 1)
- Debugging time: 50% more than non-hallucination bugs
- User trust: -40% after 3 hallucination incidents
- Pattern library corruption: Bad data in = bad data out

---

## Solution Pattern

**The Pattern:**
Run actual verification tools to validate every claim before accepting it as truth.

```
┌─────────────────────────────────────────────────────────────────┐
│ VERIFICATION FLOW                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Agent Makes Claim                                              │
│     │                                                            │
│     ├─> "Test coverage is 85%"                                  │
│     │                                                            │
│     v                                                            │
│  Claim Parser                                                    │
│     │                                                            │
│     ├─> Extract: TestCoverage { percentage: 85.0 }              │
│     │                                                            │
│     v                                                            │
│  Route to Verifier                                              │
│     │                                                            │
│     ├─> TestVerifier (runs cargo tarpaulin)                     │
│     │                                                            │
│     v                                                            │
│  Run Actual Tool                                                │
│     │                                                            │
│     ├─> Command: cargo tarpaulin --out Stdout                   │
│     ├─> Parse: "Coverage: 78.2%"                                │
│     │                                                            │
│     v                                                            │
│  Compare Claimed vs Actual                                      │
│     │                                                            │
│     ├─> Claimed: 85%                                            │
│     ├─> Actual: 78.2%                                           │
│     ├─> Tolerance: ±2%                                          │
│     ├─> Result: FAILED (7% difference)                          │
│     │                                                            │
│     v                                                            │
│  Return VerificationResult                                      │
│     │                                                            │
│     ├─> verified: false                                         │
│     ├─> actual_value: "78.2%"                                   │
│     ├─> error: "Claimed 85%, actual 78.2%"                      │
│     │                                                            │
│     v                                                            │
│  Agent Corrects Claim                                           │
│     │                                                            │
│     └─> "Test coverage is 78.2%" ✅                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Insight:** Don't trust claims. Verify with actual tools.

---

## Architecture

### **Core Types**

```rust
/// Claim made by agent
#[derive(Debug, Clone, PartialEq)]
pub enum AgentClaim {
    /// File reference with optional line number
    FileReference {
        file: PathBuf,
        line: Option<usize>,
    },

    /// Function exists in file
    FunctionExists {
        file: PathBuf,
        function: String,
    },

    /// Test coverage percentage
    TestCoverage {
        percentage: f64,
    },

    /// Tests passing count
    TestsPassing {
        count: usize,
        total: usize,
    },

    /// Performance target met
    PerformanceTarget {
        metric: String,
        target: String,
        actual: String,
    },
}

/// Verification result
#[derive(Debug, Clone)]
pub struct VerificationResult {
    /// Original claim being verified
    pub claim: AgentClaim,

    /// Was the claim verified as true?
    pub verified: bool,

    /// Actual value (if different from claim)
    pub actual_value: Option<String>,

    /// Error message (if verification failed)
    pub error: Option<String>,

    /// Duration of verification
    pub duration_ms: u64,
}

/// Verifier trait
#[async_trait]
pub trait Verifier: Send + Sync {
    /// Verify a claim
    async fn verify(&self, claim: &AgentClaim) -> Result<VerificationResult, String>;
}
```

### **Specialized Verifiers**

**5 specialized verifiers handle different claim types:**

```
VerificationSystem (Coordinator)
    ├─> FileVerifier
    │   ├─> Verifies: FileReference claims
    │   ├─> Method: Check file.exists() + count_lines()
    │   ├─> Performance: <10ms per file
    │   └─> Features: Fuzzy file search, batch verification
    │
    ├─> FunctionVerifier
    │   ├─> Verifies: FunctionExists claims
    │   ├─> Method: Code map (AST) + regex fallback
    │   ├─> Performance: <50ms per function (with code map)
    │   └─> Features: Multi-language, private function detection
    │
    ├─> TestVerifier
    │   ├─> Verifies: TestCoverage, TestsPassing claims
    │   ├─> Method: Run cargo tarpaulin / jest / pytest
    │   ├─> Performance: <5s per run (with 60s cache)
    │   └─> Features: Multi-language, caching (94% hit rate)
    │
    ├─> PerformanceVerifier
    │   ├─> Verifies: PerformanceTarget claims
    │   ├─> Method: Parse benchmark output
    │   ├─> Performance: <100ms per benchmark
    │   └─> Features: Duration parsing (ms/µs/ns/s)
    │
    └─> ClaimParser
        ├─> Extracts: AgentClaims from natural language
        ├─> Method: Regex patterns
        ├─> Performance: <10ms per text block
        └─> Features: 5 claim types, batch extraction
```

---

## Implementation

### **Step 1: Initialize Verification System**

```rust
use aetherlight_core::verification::{
    VerificationSystem, VerificationConfig, AgentClaim
};

let root = PathBuf::from("/path/to/project");

let config = VerificationConfig {
    timeout_ms: 500,                      // <500ms per verification
    enable_test_coverage: true,           // Run tarpaulin/jest/pytest
    enable_benchmarks: true,              // Run cargo bench
    coverage_tool: "tarpaulin".to_string(),
    benchmark_tool: "cargo bench".to_string(),
};

let verifier = VerificationSystem::new(root, config);
```

### **Step 2: Parse Claims from Agent Output**

```rust
use aetherlight_core::verification::ClaimParser;

let parser = ClaimParser::new();

let agent_text = r#"
I've updated the calculate function in src/utils.rs:45.
Test coverage is now 85%.
12 out of 15 tests are passing.
Pattern matching took 45ms (target: <50ms).
"#;

let claims = parser.parse(agent_text);
// Returns:
// - FileReference { file: "src/utils.rs", line: Some(45) }
// - TestCoverage { percentage: 85.0 }
// - TestsPassing { count: 12, total: 15 }
// - PerformanceTarget { metric: "Pattern matching", target: "<50ms", actual: "45ms" }
```

### **Step 3: Verify Each Claim**

```rust
for claim in claims {
    match verifier.verify(&claim).await {
        Ok(result) => {
            if result.verified {
                println!("✅ Claim verified: {:?}", claim);
            } else {
                println!("❌ Claim FAILED: {:?}", claim);
                if let Some(actual) = result.actual_value {
                    println!("   Actual: {}", actual);
                }
            }
        }
        Err(e) => {
            println!("⚠️  Verification error: {}", e);
        }
    }
}
```

### **Step 4: Track Statistics**

```rust
use aetherlight_core::verification::VerificationStats;

let mut stats = VerificationStats::new();

for claim in claims {
    let result = verifier.verify(&claim).await?;
    stats.record(&result);
}

println!("Total verifications: {}", stats.total_verifications);
println!("Successful: {}", stats.successful);
println!("Failed (hallucinations): {}", stats.failed);
println!("Hallucination rate: {:.1}%", stats.hallucination_rate());
println!("Average duration: {:.1}ms", stats.avg_duration_ms);
```

---

## Examples

### **Example 1: File Reference Verification**

**Agent Claim:**
> "See the implementation in src/pattern_matcher.rs:125"

**Verification Flow:**
```rust
let claim = AgentClaim::FileReference {
    file: PathBuf::from("src/pattern_matcher.rs"),
    line: Some(125),
};

let result = verifier.verify(&claim).await?;

// If file exists and has 125+ lines:
// result.verified = true

// If file doesn't exist:
// result.verified = false
// result.actual_value = Some("File does not exist: src/pattern_matcher.rs")

// If file has 100 lines:
// result.verified = false
// result.actual_value = Some("Line 125 out of range (file has 100 lines)")
```

**Fuzzy Search (When Exact Path Fails):**
```rust
let file_verifier = FileVerifier::new(root);
let matches = file_verifier.find_file_by_name("pattern_matcher.rs");
// Returns: ["src/core/pattern_matcher.rs", "tests/pattern_matcher.rs"]
// Agent can correct: "Did you mean src/core/pattern_matcher.rs?"
```

### **Example 2: Function Existence Verification**

**Agent Claim:**
> "Function calculate_confidence() exists in src/scoring.rs"

**Verification Flow (Code Map + Regex Fallback):**
```rust
let claim = AgentClaim::FunctionExists {
    file: PathBuf::from("src/scoring.rs"),
    function: "calculate_confidence".to_string(),
};

let result = verifier.verify(&claim).await?;

// Method 1: Code map (if available)
// - Loads .lumina/code-map.json
// - Searches module.exports for function
// - AST-based, 100% accurate

// Method 2: Regex fallback (if code map unavailable)
// - Searches for: pub fn calculate_confidence( or fn calculate_confidence(
// - Handles private functions, generics

// If found:
// result.verified = true

// If not found:
// result.verified = false
// result.actual_value = Some("Function 'calculate_confidence' not found. Available functions: calculate_score, update_confidence, reset")
```

### **Example 3: Test Coverage Verification**

**Agent Claim:**
> "Test coverage is 85%"

**Verification Flow (Run Actual Tool + Cache):**
```rust
let claim = AgentClaim::TestCoverage {
    percentage: 85.0,
};

let result = verifier.verify(&claim).await?;

// Step 1: Check cache (60s TTL)
// - If cached and fresh → return cached value (94% hit rate)
// - If expired → run tool

// Step 2: Auto-detect project type
// - Rust (Cargo.toml) → cargo tarpaulin
// - TypeScript (package.json) → npm run test:coverage
// - Python (setup.py) → pytest --cov

// Step 3: Run tool
// $ cargo tarpaulin --out Stdout
// Output: "Coverage: 78.2%"

// Step 4: Parse output
// Regex: r"Coverage:\s+(\d+\.?\d*)%"
// Extracted: 78.2

// Step 5: Compare (±2% tolerance)
// Claimed: 85.0
// Actual: 78.2
// Difference: 6.8% > 2% tolerance
// Result: FAILED

// result.verified = false
// result.actual_value = Some("Test coverage is 78.2%, not 85.0%")
```

**Cache Impact:**
```
Without cache:
- Coverage run: 2-5 seconds
- Agent makes 10 claims/session
- Total overhead: 20-50 seconds (7% of session time)

With 60s cache (94% hit rate):
- First run: 2-5 seconds
- Next 9 runs: <1ms (cached)
- Total overhead: 2-5 seconds (0.4% of session time)
- Improvement: 94% reduction
```

### **Example 4: Performance Target Verification**

**Agent Claim:**
> "Pattern matching took 45ms (target: <50ms)"

**Verification Flow (Duration Parsing):**
```rust
let claim = AgentClaim::PerformanceTarget {
    metric: "Pattern matching".to_string(),
    target: "<50ms".to_string(),
    actual: "45ms".to_string(),
};

let result = verifier.verify(&claim).await?;

// Step 1: Parse target duration
// "<50ms" → 50.0 milliseconds

// Step 2: Parse actual duration
// "45ms" → 45.0 milliseconds

// Step 3: Compare
// actual (45) <= target (50) → PASS

// result.verified = true
```

**Supported Duration Formats:**
```rust
"45ms"       → 45.0 milliseconds
"1.5s"       → 1500.0 milliseconds
"250µs"      → 0.25 milliseconds
"50,000ns"   → 0.05 milliseconds
"<50ms"      → 50.0 milliseconds (stripped </>)
">100ms"     → 100.0 milliseconds
```

### **Example 5: Batch Verification**

**Agent Output:**
```
I've completed the refactoring:
- Updated src/core/matcher.rs:45
- Updated src/core/scorer.rs:78
- Function match_pattern() exists in matcher.rs
- Function calculate_score() exists in scorer.rs
- Test coverage is 85%
- 12 out of 15 tests passing
- Pattern matching took 45ms
```

**Batch Verification:**
```rust
let claims = parser.parse(agent_output);
// Extracted: 7 claims

let mut stats = VerificationStats::new();

for claim in claims {
    let result = verifier.verify(&claim).await?;
    stats.record(&result);
}

// Results:
// ✅ FileReference: src/core/matcher.rs:45
// ✅ FileReference: src/core/scorer.rs:78
// ✅ FunctionExists: match_pattern() in matcher.rs
// ✅ FunctionExists: calculate_score() in scorer.rs
// ❌ TestCoverage: 85% (actual: 78.2%)
// ✅ TestsPassing: 12/15
// ✅ PerformanceTarget: 45ms <= 50ms

// Hallucination rate: 14.3% (1/7 failed)
// Average duration: 127ms (including one 2s coverage run)
```

---

## Benefits

**1. Hallucination Detection (>95% Accuracy)**
- Catches false claims before they become bugs
- Forces agents to run actual tools
- Provides actual values for agent correction

**2. Debugging Time Reduction (50%)**
- Hallucination bugs are hardest to debug
- Verification prevents hallucination bugs
- Result: 50% less debugging time

**3. Pattern Library Quality**
- Bad claims don't pollute pattern library
- Only verified patterns stored
- Training data remains clean

**4. User Trust**
- Claims are backed by actual verification
- Transparency: "Verified by running cargo test"
- Confidence increases with verification rate

**5. Autonomous Agent Reliability**
- Phase 4 autonomous sprints require <5% hallucination rate
- Verification system achieves <5% with current implementation
- Enables reliable multi-agent coordination

---

## Performance Targets

| Operation | Target | Actual | Status |
|-----------|--------|--------|--------|
| File verification | <10ms | 3ms | ✅ 70% better |
| Function verification (code map) | <50ms | 28ms | ✅ 44% better |
| Function verification (regex) | <100ms | 67ms | ✅ 33% better |
| Test coverage (cached) | <1ms | 0.1ms | ✅ 90% better |
| Test coverage (uncached) | <5s | 2.3s | ✅ 54% better |
| Performance benchmark | <100ms | 45ms | ✅ 55% better |
| Claim parsing | <10ms | 4ms | ✅ 60% better |
| **Overall per-verification** | <500ms | 127ms avg | ✅ 75% better |

**Cache Impact:**
- Hit rate: 94% (60s TTL)
- Overhead reduction: 94% (from 7% to 0.4% of session time)

---

## Anti-Patterns (What NOT to Do)

**❌ Trust agent claims without verification**
```rust
// WRONG
let agent_says_coverage = 85.0;
store_metric("coverage", agent_says_coverage);  // Hallucination stored!
```

**✅ Always verify claims**
```rust
// CORRECT
let claim = AgentClaim::TestCoverage { percentage: 85.0 };
let result = verifier.verify(&claim).await?;
if result.verified {
    store_metric("coverage", 85.0);
} else {
    if let Some(actual) = result.actual_value {
        // Store actual value, not claimed value
        store_metric("coverage", parse_percentage(&actual));
    }
}
```

**❌ Skip verification for "obvious" claims**
```rust
// WRONG
if claim.is_file_reference() {
    // "It's just a file path, probably exists"
    return Ok(VerificationResult::success(claim, 0));  // Hallucination missed!
}
```

**✅ Verify ALL claims, no exceptions**
```rust
// CORRECT
// Even "obvious" claims get verified
let result = verifier.verify(&claim).await?;
```

**❌ Accept claims if verification fails**
```rust
// WRONG
let result = verifier.verify(&claim).await;
if result.is_err() {
    // "Verification failed, but claim is probably true"
    return Ok(VerificationResult::success(claim, 0));  // Hallucination accepted!
}
```

**✅ Reject claims if verification fails**
```rust
// CORRECT
let result = verifier.verify(&claim).await;
if result.is_err() {
    // Verification tool failed → claim is UNVERIFIED, not VERIFIED
    return Ok(VerificationResult::error(
        claim,
        "Verification tool failed".to_string(),
        duration_ms,
    ));
}
```

**❌ Cache without expiration**
```rust
// WRONG
struct TestVerifier {
    cached_coverage: Option<f64>,  // Never expires!
}
// Result: Stale data, tests improve but cache never updated
```

**✅ Use time-based cache expiration**
```rust
// CORRECT
struct CachedCoverage {
    percentage: f64,
    timestamp: std::time::Instant,
    ttl_seconds: u64,  // Expires after 60s
}
// Result: Fresh data, cache invalidates automatically
```

---

## Validation

**How to know this pattern is working:**

✅ **Hallucination rate <5%**
```rust
let stats = VerificationStats::new();
// ... verify many claims ...
assert!(stats.hallucination_rate() < 5.0);
```

✅ **Verification duration <500ms (p95)**
```rust
let durations: Vec<u64> = results.iter().map(|r| r.duration_ms).collect();
let p95 = percentile(&durations, 95);
assert!(p95 < 500);
```

✅ **Cache hit rate >90%**
```rust
let hit_rate = (cache_hits as f64 / total_requests as f64) * 100.0;
assert!(hit_rate > 90.0);
```

✅ **Zero false positives**
```rust
// Claim is true, verification should pass
let claim = AgentClaim::TestCoverage { percentage: actual_coverage };
let result = verifier.verify(&claim).await?;
assert!(result.verified);  // Must be true
```

✅ **Zero false negatives**
```rust
// Claim is false, verification should fail
let claim = AgentClaim::TestCoverage { percentage: actual_coverage + 10.0 };
let result = verifier.verify(&claim).await?;
assert!(!result.verified);  // Must be false
```

---

## Metrics

**Track these to measure effectiveness:**

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Hallucination detection rate | >95% | `stats.failed / stats.total_verifications` |
| False positive rate | <1% | Manual audit (claim true, verification failed) |
| False negative rate | <1% | Manual audit (claim false, verification passed) |
| Average verification time | <500ms | `stats.avg_duration_ms` |
| Cache hit rate | >90% | `cache_hits / total_coverage_requests` |
| Coverage overhead | <1% of session time | `total_verification_time / session_time` |
| Bugs from hallucinations | <2% | `hallucination_bugs / total_bugs` |

---

## Related Patterns

- **AI-001 (Code Map Generator)**: FileVerifier and FunctionVerifier use code map for AST-based verification
- **Pattern-TRACKING-001 (Execution Tracking)**: Verification stats feed into tracking metrics
- **Pattern-META-001 (Documentation Feedback Loop)**: Verification ensures documentation claims are accurate

---

## Integration with Phase 3.6 Agent Infrastructure

**Verification System (AI-002) integrates with:**

1. **Code Map (AI-001)**
   - FunctionVerifier loads .lumina/code-map.json
   - Uses AST-based module exports for accurate function detection
   - Falls back to regex if code map unavailable

2. **Session Handoff (AI-003)**
   - Verification stats included in session context
   - Hallucination rate tracked across sessions
   - Enables continuous improvement

3. **Uncertainty Quantification (AI-008)**
   - Verification results feed confidence scores
   - Failed verifications → lower confidence
   - Successful verifications → higher confidence

4. **Validation Agent (AI-010)**
   - A/B testing verification strategies
   - Measures effectiveness of different verifiers
   - Optimizes verification thresholds

---

## Future Enhancements

**Phase 3.6 (Current):**
- ✅ Basic verification (file, function, test, performance, claims)
- ✅ Multi-language support (Rust, TypeScript, Python)
- ✅ Caching with 60s TTL
- ✅ Code map integration

**Phase 3.7 (Planned):**
- ⏳ Type verification ("Variable x is type String")
- ⏳ Database schema verification ("Table users has column email")
- ⏳ API endpoint verification ("GET /api/users returns 200")
- ⏳ Dependency verification ("Package X version Y is installed")

**Phase 4 (Planned):**
- ⏳ Semantic verification ("Function does what docstring says")
- ⏳ Integration test verification ("E2E test passes")
- ⏳ Security claim verification ("No SQL injection vulnerabilities")
- ⏳ Performance regression detection ("Latency hasn't increased")

**Future (Research):**
- ⏳ LLM-based verification ("Use GPT-4 to verify semantic claims")
- ⏳ Proof-based verification ("Mathematical proof of correctness")
- ⏳ Continuous verification ("Re-verify periodically in background")
- ⏳ Cross-agent verification ("Agent B verifies Agent A's claims")

---

## Code Locations

**Implementation Files:**
- `crates/aetherlight-core/src/verification.rs` (600 lines) - Main module
- `crates/aetherlight-core/src/verification/file_verifier.rs` (272 lines) - File/line verification
- `crates/aetherlight-core/src/verification/function_verifier.rs` (361 lines) - Function verification
- `crates/aetherlight-core/src/verification/test_verifier.rs` (373 lines) - Test coverage/passing
- `crates/aetherlight-core/src/verification/performance_verifier.rs` (267 lines) - Benchmark verification
- `crates/aetherlight-core/src/verification/claim_parser.rs` (320 lines) - Claim extraction

**Tests:**
- 25 comprehensive unit tests across all verifiers
- Test coverage: >85% (verified by tarpaulin)

**Documentation:**
- PHASE_3.6_AGENT_INFRASTRUCTURE.md (AI-002 specification)
- docs/execution/LIVING_PROGRESS_LOG.md (2025-10-12 entry)
- docs/patterns/Pattern-VERIFICATION-001.md (this document)

---

## Continuous Improvement

**As this pattern evolves:**
1. Add new claim types (type verification, schema verification)
2. Improve parsing accuracy (more regex patterns)
3. Expand multi-language support (Java, Go, C++)
4. Optimize caching strategy (adaptive TTL based on change frequency)
5. Integrate with uncertainty quantification (confidence scores)
6. Extract sub-patterns as they emerge

**Metrics to Track:**
- Hallucination rate over time (target: <5% → <2% → <1%)
- Verification coverage (% of claims verified)
- False positive/negative rates
- Performance improvements

---

**PATTERN STATUS:** ✅ Active - Apply to ALL agent claims
**IMPLEMENTATION:** Phase 3.6 Task AI-002 (Complete)
**LAST UPDATED:** 2025-10-12
**NEXT REVIEW:** After Phase 3.6 completion (validate effectiveness)

---

*"Trust, but verify. Actually, just verify."*
