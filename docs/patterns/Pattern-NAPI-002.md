# Pattern-NAPI-002: FFI Error Handling Without Orphan Rules

**CREATED:** 2025-11-02
**CATEGORY:** Uncategorized
**LANGUAGE:** JavaScript
**QUALITY SCORE:** 0.80
**APPLICABILITY:** All Rust FFI projects with external error types
**STATUS:** Validated (used in all FFI method implementations)
**RELATED:** PATTERN-NAPI-001

---




## PROBLEM

Cannot implement `From<CoreError> for napi::Error` because both types are from external crates, violating Rust's **orphan rule**:

```rust
// ❌ COMPILATION ERROR
impl From<aetherlight_core::Error> for napi::Error {
    fn from(err: aetherlight_core::Error) -> Self {
        napi::Error::new(napi::Status::GenericFailure, err.to_string())
    }
}

// Error: cannot implement foreign trait for foreign type (orphan rule violation)
```

**ROOT CAUSE:**
Rust's coherence rules prevent implementing traits from external crates on types from other external crates. This prevents conflicts if both crates later add the same implementation.

**WHY THIS MATTERS:**
FFI layers need to convert core library errors to FFI framework errors. Without `From` trait, error conversion is verbose and repetitive.

---

## SOLUTION

**Use a helper function instead of trait implementation:**

```rust
/**
 * Convert Rust core errors to NAPI errors
 *
 * DESIGN DECISION: Helper function instead of From trait to avoid orphan rules
 * WHY: Cannot implement From<CoreError> for napi::Error (both are external types)
 *
 * REASONING CHAIN:
 * 1. Rust panics cannot cross FFI boundary safely (undefined behavior)
 * 2. All Rust errors returned as Result (no panics in library code)
 * 3. NAPI-RS converts Result::Err to JavaScript Error automatically
 * 4. Error messages preserved from Rust (user-facing, no internal details)
 * 5. JavaScript consumers can catch errors with try/catch
 * 6. Helper function pattern avoids orphan rule violation
 *
 * PATTERN: Pattern-NAPI-002 (FFI Error Handling Without Orphan Rules)
 * RELATED: aetherlight_core::Error
 */
fn convert_error(err: aetherlight_core::Error) -> napi::Error {
    napi::Error::new(napi::Status::GenericFailure, err.to_string())
}
```

**Usage in FFI functions:**

```rust
#[napi]
impl PatternMatcher {
    #[napi]
    pub fn add_pattern(&mut self, pattern: Pattern) -> napi::Result<()> {
        self.inner
            .add_pattern(pattern.inner)
            .map_err(convert_error) // ✅ Use helper function
    }

    #[napi]
    pub fn find_matches(&self, query: String, max_results: u32) -> napi::Result<Vec<MatchResult>> {
        let results = self.inner
            .find_matches(&query, max_results as usize)
            .map_err(convert_error)?; // ✅ Use helper function with ?

        Ok(results.into_iter().map(|r| r.into()).collect())
    }
}
```

---

## WHEN TO USE

### Use Helper Function Pattern When:
- Converting errors between external crates (both are foreign types)
- Core library errors need translation to FFI framework errors
- Error types are not under your control
- Trait implementation would violate orphan rules

### Use From/Into Traits When:
- At least one type is local to your crate (orphan rule satisfied)
- Example: `impl From<CoreError> for MyFFIError` (MyFFIError is local)
- Example: `impl From<MyDomainError> for CoreError` (MyDomainError is local)

---

## IMPLEMENTATION

### Full Pattern: Error Conversion Helper

```rust
use napi::bindgen_prelude::*;
use aetherlight_core::{Error as CoreError, Result as CoreResult};

/**
 * Convert core library errors to NAPI errors
 *
 * DESIGN DECISION: Preserve error message but map to generic status
 * WHY: NAPI-RS has limited status codes; error message provides specifics
 *
 * REASONING CHAIN:
 * 1. CoreError contains user-facing error messages (Display trait)
 * 2. NAPI Status enum has limited variants (GenericFailure is catch-all)
 * 3. JavaScript Error object receives full error message
 * 4. Specific error types (PatternNotFound, etc.) mapped to same status
 * 5. Future: Add status code mapping for specific error types
 *
 * PATTERN: Pattern-NAPI-002
 */
fn convert_error(err: CoreError) -> napi::Error {
    // Extract error message (uses Display trait)
    let message = err.to_string();

    // Map to NAPI status (could be more granular in future)
    let status = match err {
        CoreError::PatternNotFound(_) => napi::Status::InvalidArg,
        CoreError::DuplicatePattern(_) => napi::Status::InvalidArg,
        CoreError::EmptyLibrary => napi::Status::InvalidArg,
        CoreError::InvalidQuery(_) => napi::Status::InvalidArg,
        CoreError::PatternValidation(_) => napi::Status::InvalidArg,
        CoreError::ConfidenceCalculation(_) => napi::Status::GenericFailure,
        _ => napi::Status::GenericFailure,
    };

    napi::Error::new(status, message)
}
```

### Advanced: Bidirectional Error Conversion

```rust
// Convert NAPI errors to core errors (if needed for callbacks)
fn convert_napi_error(err: napi::Error) -> CoreError {
    // Create generic error with NAPI error message
    CoreError::External(err.to_string())
}

// Usage in async callback scenarios
#[napi]
pub async fn process_with_callback(
    callback: napi::JsFunction
) -> napi::Result<()> {
    // Call JavaScript callback
    let result: napi::Result<String> = callback.call(None, &[]);

    // Convert NAPI error to core error if callback fails
    let value = result.map_err(convert_napi_error)?;

    // Continue processing with core library
    process_internal(&value).map_err(convert_error)
}
```

---

## ALTERNATIVES CONSIDERED

### Alternative 1: Newtype Wrapper
**Description:** Wrap external error type in local newtype to satisfy orphan rule.

```rust
struct MyError(aetherlight_core::Error);

impl From<aetherlight_core::Error> for MyError {
    fn from(err: aetherlight_core::Error) -> Self {
        MyError(err)
    }
}

impl From<MyError> for napi::Error {
    fn from(err: MyError) -> Self {
        napi::Error::new(napi::Status::GenericFailure, err.0.to_string())
    }
}
```

**Pros:**
- Uses trait system (idiomatic Rust)
- Enables `?` operator with automatic conversion

**Cons:**
- Adds unnecessary indirection (MyError wrapper)
- Requires two conversions (CoreError → MyError → napi::Error)
- More boilerplate code

**Why Rejected:** Helper function achieves same result with less complexity.

### Alternative 2: Add NAPI Dependency to Core Library
**Description:** Re-export `napi::Error` from core library, making it a "local" type.

```rust
// In aetherlight-core/Cargo.toml
[dependencies]
napi = { version = "2", optional = true }

// In aetherlight-core/src/lib.rs
#[cfg(feature = "napi")]
pub use napi::Error as NapiError;

#[cfg(feature = "napi")]
impl From<Error> for NapiError {
    fn from(err: Error) -> Self {
        NapiError::new(napi::Status::GenericFailure, err.to_string())
    }
}
```

**Pros:**
- Trait implementation allowed (NapiError re-exported from core)
- Automatic conversion with `?` operator

**Cons:**
- **Pollutes core library with FFI dependency** (violates separation of concerns)
- Core library shouldn't know about NAPI (what about Flutter FFI? WebAssembly?)
- Increases compile times for all consumers (even non-NAPI)

**Why Rejected:** Violates architectural principle (core library should be FFI-agnostic).

### Alternative 3: Macro-Generated Error Conversion
**Description:** Use declarative macro to generate conversion functions.

```rust
macro_rules! convert_error {
    ($err:expr) => {
        napi::Error::new(napi::Status::GenericFailure, $err.to_string())
    };
}

// Usage
.map_err(|e| convert_error!(e))
```

**Pros:**
- Shorter syntax at call sites
- Declarative error handling

**Cons:**
- Macro hygiene issues (can capture wrong variables)
- Harder to debug (macro expansion errors are cryptic)
- Less explicit than function call

**Why Rejected:** Explicit function is clearer and easier to debug.

---

## RELATED PATTERNS

- **Pattern-007:** Language Bindings via NAPI (parent pattern)
- **Pattern-NAPI-001:** Object vs Constructor Pattern (related FFI pattern)
- **Pattern-001:** Rust Core + Language Bindings (architecture)

---

## EXAMPLES IN CODEBASE

### Error Conversion Helper
- **File:** `packages/aetherlight-node/src/lib.rs:84-86`
- **Definition:** `fn convert_error(err: CoreError) -> napi::Error`

### Usage in FFI Methods
- **File:** `packages/aetherlight-node/src/lib.rs:150-180`
- **Example:** `PatternMatcher::add_pattern()` uses `.map_err(convert_error)`
- **Example:** `PatternMatcher::find_matches()` uses `.map_err(convert_error)?`

### Error Types
- **Core errors:** `crates/aetherlight-core/src/error.rs`
- **NAPI errors:** Generated by NAPI-RS framework

---

## DEBUGGING TIPS

### If You See "orphan rule" Compilation Error:
1. Check if both types are external (not defined in your crate)
2. Use helper function pattern instead of trait implementation
3. Verify helper function signature: `fn convert_error(ExternalError) -> OtherExternalError`

### If JavaScript Errors Lose Context:
1. Verify error conversion preserves `.to_string()` message
2. Check CoreError implements Display trait
3. Test error propagation: Rust error → NAPI error → JavaScript Error

### If Errors Are Swallowed:
1. Check `.map_err(convert_error)?` syntax (don't forget `?`)
2. Verify NAPI-RS proc macro on function: `#[napi]`
3. Test error handling in JavaScript: `try { ... } catch (err) { console.error(err.message); }`

---

## TESTING STRATEGY

### Rust-Side Testing:
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_conversion() {
        let core_err = CoreError::PatternNotFound("test-id".to_string());
        let napi_err = convert_error(core_err);

        // Verify error message preserved
        assert!(napi_err.reason.contains("Pattern not found"));
        assert!(napi_err.reason.contains("test-id"));
    }
}
```

### JavaScript-Side Testing:
```javascript
import { PatternMatcher } from '@aetherlight/node';

// Test: Error propagates to JavaScript
try {
    const matcher = new PatternMatcher();
    matcher.findMatches("", 5); // Invalid query (empty string)
    assert.fail("Should have thrown error");
} catch (err) {
    assert(err.message.includes("empty")); // Error message preserved
}

// Test: Error type is Error
try {
    const matcher = new PatternMatcher();
    matcher.findMatches("test", 5); // Empty library
    assert.fail("Should have thrown error");
} catch (err) {
    assert(err instanceof Error); // NAPI error converted to JavaScript Error
    assert(err.message.includes("Empty library"));
}
```

---

## FUTURE IMPROVEMENTS

### Potential Enhancements:
1. **Granular status mapping:** Map specific CoreError variants to specific napi::Status codes
2. **Error stack traces:** Preserve Rust backtraces in JavaScript errors (NAPI-RS feature)
3. **Custom error properties:** Add custom fields to JavaScript Error objects (error codes, etc.)

### Known Limitations:
1. Status code granularity limited by NAPI-RS Status enum (few variants)
2. Cannot implement custom traits on external types (orphan rule fundamental)
3. Error conversion adds small overhead (~1-2μs per error)

---

## RELATED DOCUMENTATION

### Rust Orphan Rules:
- [Rust Book: Advanced Traits](https://doc.rust-lang.org/book/ch19-03-advanced-traits.html#using-the-newtype-pattern-to-implement-external-traits-on-external-types)
- [Coherence rules](https://github.com/rust-lang/rfcs/blob/master/text/2451-re-rebalancing-coherence.md)

### NAPI-RS Error Handling:
- [NAPI-RS Error Handling](https://napi.rs/docs/concepts/error-handling)
- [NAPI Status Codes](https://napi.rs/docs/concepts/error-handling#error-status)

---

**LAST UPDATED:** 2025-10-04
**PATTERN ID:** NAPI-002
**STATUS:** Validated (used in all FFI method implementations)
**RELATED TASKS:** P1-008 (Node.js Bindings)

---

**Chain of Thought:**
This pattern was discovered while implementing error handling in NAPI-RS bindings (P1-008). Initial attempt to implement `From<CoreError> for napi::Error` failed with orphan rule compilation error. Root cause analysis revealed Rust coherence rules. Helper function pattern identified as cleanest solution that maintains architectural separation between core library and FFI layer.

**Impact:** Enabled proper error propagation across FFI boundary without polluting core library with FFI-specific dependencies. Pattern is reusable for Flutter FFI, WebAssembly, and any future language bindings.
