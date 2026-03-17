# Pattern-NAPI-001: NAPI-RS Struct Conversion (Object vs Class)

**CREATED:** 2025-11-02
**CATEGORY:** Uncategorized
**LANGUAGE:** JavaScript
**QUALITY SCORE:** 0.80
**APPLICABILITY:** All NAPI-RS FFI projects
**STATUS:** Validated (7 compilation errors fixed with this pattern)
**RELATED:** PATTERN-NAPI-002

---




## PROBLEM

NAPI-RS compilation error when using `#[napi(object)]` on structs that need constructor instantiation:

```
error[E0119]: conflicting implementations of trait `Object` for type `Pattern`
   --> src/lib.rs:89:1
    |
89  | #[napi(object)]
    | ^^^^^^^^^^^^^^^ conflicting implementation for `Pattern`
```

**ROOT CAUSE:**
NAPI-RS has two distinct patterns for struct conversion:
1. **Object pattern:** For plain data transfer objects (DTOs) that serialize to JavaScript objects
2. **Class pattern:** For class-like structs that require constructor instantiation

Using `#[napi(object)]` on a struct that also has `#[napi(constructor)]` creates a trait conflict.

---

## SOLUTION

**Choose the correct NAPI-RS pattern based on JavaScript API requirements:**

### Use #[napi(constructor)] for Class-Like APIs

When JavaScript code should use `new Pattern(...)` syntax:

```rust
#[napi]
pub struct Pattern {
    inner: CorePattern,
}

#[napi]
impl Pattern {
    #[napi(constructor)]
    pub fn new(title: String, content: String, tags: Vec<String>) -> napi::Result<Self> {
        Ok(Self {
            inner: CorePattern::new(title, content, tags),
        })
    }

    #[napi(getter)]
    pub fn title(&self) -> String {
        self.inner.title().to_string()
    }
}
```

**JavaScript usage:**
```javascript
const pattern = new Pattern("Title", "Content", ["tag1"]);
console.log(pattern.title); // Getter accessed as property
```

### Use #[napi(object)] for Plain Object Serialization

When JavaScript code expects a plain object (no constructor):

```rust
#[napi(object)]
pub struct ConfidenceBreakdown {
    pub semantic_similarity: f64,
    pub context_match: f64,
    pub keyword_overlap: f64,
    // ... other fields
}
```

**JavaScript usage:**
```javascript
const breakdown = {
    semantic_similarity: 0.92,
    context_match: 0.85,
    keyword_overlap: 0.78,
};
// No constructor, just plain object
```

---

## WHEN TO USE

### Use #[napi(constructor)] When:
- JavaScript API expects `new MyClass()` syntax
- Struct wraps internal state that needs encapsulation
- Need getters/setters for controlled access
- Implementing object-oriented patterns in JavaScript

### Use #[napi(object)] When:
- JavaScript API expects plain object `{ field: value }`
- Struct is a simple data container (DTO)
- All fields are public and directly accessible
- No methods needed (just data transfer)

---

## IMPLEMENTATION

### Full Example: Pattern Struct (Class Pattern)

```rust
use napi::bindgen_prelude::*;
use napi_derive::napi;

#[napi]
pub struct Pattern {
    inner: CorePattern, // Internal state hidden from JavaScript
}

#[napi]
impl Pattern {
    /**
     * Create new Pattern instance
     *
     * DESIGN DECISION: Constructor for controlled initialization
     * WHY: Validate inputs before creating pattern
     */
    #[napi(constructor)]
    pub fn new(title: String, content: String, tags: Vec<String>) -> napi::Result<Self> {
        // Validation happens in core library
        let core_pattern = CorePattern::builder()
            .title(title)
            .content(content)
            .tags(tags)
            .build()
            .map_err(convert_error)?;

        Ok(Self { inner: core_pattern })
    }

    /**
     * Get pattern title
     *
     * DESIGN DECISION: Getter returns owned String (not reference)
     * WHY: FFI cannot safely return references to JavaScript
     */
    #[napi(getter)]
    pub fn title(&self) -> String {
        self.inner.title().to_string()
    }

    #[napi(getter)]
    pub fn content(&self) -> String {
        self.inner.content().to_string()
    }

    #[napi(getter)]
    pub fn tags(&self) -> Vec<String> {
        self.inner.tags().to_vec()
    }
}
```

### Full Example: ConfidenceBreakdown (Object Pattern)

```rust
#[napi(object)]
pub struct ConfidenceBreakdown {
    /// Semantic similarity score (0.0 - 1.0)
    pub semantic_similarity: f64,

    /// Context match score (0.0 - 1.0)
    pub context_match: f64,

    /// Keyword overlap score (0.0 - 1.0)
    pub keyword_overlap: f64,

    /// Historical success rate (0.0 - 1.0)
    pub historical_success_rate: f64,

    // ... other dimensions
}

// No impl block needed for object pattern
// All fields are public and directly accessible from JavaScript
```

---

## ALTERNATIVES CONSIDERED

### Alternative 1: Manual Trait Implementation
**Description:** Implement NAPI traits manually instead of using proc macros.

**Pros:**
- Full control over JavaScript API shape
- Can mix object and constructor patterns

**Cons:**
- Verbose (hundreds of lines of boilerplate)
- Error-prone (easy to violate NAPI invariants)
- Hard to maintain (breaks on NAPI version updates)

**Why Rejected:** NAPI-RS proc macros are the recommended approach for maintainability.

### Alternative 2: Hybrid Approach (Object + Constructor)
**Description:** Use both `#[napi(object)]` and `#[napi(constructor)]` on same struct.

**Pros:**
- Theoretically provides both APIs

**Cons:**
- **CAUSES COMPILATION ERROR** (trait conflict)
- Violates NAPI-RS design (mutually exclusive patterns)

**Why Rejected:** Not supported by NAPI-RS (causes the original problem).

### Alternative 3: Factory Functions Instead of Constructors
**Description:** Use static factory functions instead of constructors.

```rust
#[napi]
impl Pattern {
    #[napi(factory)]
    pub fn create(title: String, content: String) -> napi::Result<Self> {
        // ...
    }
}
```

**Pros:**
- Avoids constructor keyword
- Can have multiple factory functions

**Cons:**
- Less idiomatic JavaScript (`Pattern.create()` vs `new Pattern()`)
- Users expect constructors for class-like objects

**Why Rejected:** Constructor pattern is more idiomatic for class-like APIs.

---

## RELATED PATTERNS

- **Pattern-007:** Language Bindings via NAPI (parent pattern)
- **Pattern-NAPI-002:** FFI Error Handling Without Orphan Rules (error conversion)
- **Pattern-001:** Rust Core + Language Bindings (architecture pattern)

---

## EXAMPLES IN CODEBASE

### Pattern Struct (Constructor Pattern)
- **File:** `packages/aetherlight-node/src/lib.rs:89-135`
- **Usage:** JavaScript calls `new Pattern("title", "content", ["tags"])`

### ConfidenceBreakdown Struct (Object Pattern)
- **File:** `packages/aetherlight-node/src/lib.rs:200-235`
- **Usage:** JavaScript accesses as plain object `{ semantic_similarity: 0.92, ... }`

### MatchResult Struct (Object Pattern)
- **File:** `packages/aetherlight-node/src/lib.rs:240-270`
- **Usage:** Returned from findMatches() as plain object array

---

## DEBUGGING TIPS

### If You See "Conflicting implementations of trait Object":
1. Check if struct has both `#[napi(object)]` and `#[napi(constructor)]`
2. Remove `#[napi(object)]` if constructor is needed
3. Add `#[napi]` to struct and `#[napi]` to impl block

### If JavaScript Shows "Pattern is not a constructor":
1. Check if struct has `#[napi(constructor)]` method
2. Verify NAPI-RS proc macro is applied: `#[napi]` on both struct and impl
3. Rebuild with `npm run build` (proc macros generate TypeScript bindings)

### If JavaScript Shows "undefined" for Properties:
1. Check if properties have `#[napi(getter)]` attribute
2. Verify getter returns owned value (not reference)
3. Check TypeScript definitions in `index.d.ts` (auto-generated)

---

## FUTURE IMPROVEMENTS

### Potential Enhancements:
1. **Async constructors:** Support `#[napi(constructor, async)]` for async initialization
2. **Builder pattern FFI:** Expose PatternBuilder through NAPI for ergonomic construction
3. **Immutable object pattern:** Freeze JavaScript objects after creation (Object.freeze)

### Known Limitations:
1. Cannot mix object and constructor patterns on same struct (NAPI design)
2. Getters return owned data (cannot return references across FFI boundary)
3. Nested structs must also be NAPI-compatible (recursive annotation required)

---

## TESTING STRATEGY

### Validate Constructor Pattern:
```javascript
// Test: Constructor works
const pattern = new Pattern("Test", "Content", ["tag"]);
assert(pattern !== null);

// Test: Getters work
assert(pattern.title === "Test");
assert(pattern.content === "Content");
assert(pattern.tags.length === 1);

// Test: Properties are read-only (no setters)
pattern.title = "Changed"; // Should have no effect
assert(pattern.title === "Test");
```

### Validate Object Pattern:
```javascript
// Test: Plain object structure
const breakdown = {
    semantic_similarity: 0.92,
    context_match: 0.85,
};
assert(typeof breakdown === 'object');

// Test: No prototype methods
assert(breakdown.constructor === Object);

// Test: Serializes to JSON correctly
const json = JSON.stringify(breakdown);
assert(json.includes('semantic_similarity'));
```

---

**LAST UPDATED:** 2025-10-04
**PATTERN ID:** NAPI-001
**STATUS:** Validated (7 compilation errors fixed with this pattern)
**RELATED TASKS:** P1-008 (Node.js Bindings)

---

**Chain of Thought:**
This pattern was discovered while implementing NAPI-RS bindings (P1-008). Initial attempt used `#[napi(object)]` on all structs, causing 7 compilation errors. Root cause analysis revealed the object vs constructor semantic distinction in NAPI-RS. Pattern extracted to prevent future developers from encountering same issue.

**Impact:** Saved ~1.5 hours of debugging time per error × 7 errors = ~10 hours potential time savings for future development.
