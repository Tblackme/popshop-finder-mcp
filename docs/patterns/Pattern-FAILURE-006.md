# Pattern-FAILURE-006: Self-Fulfilling Negative Prophecy

**CREATED:** 2025-11-02
**CATEGORY:** Anti-Pattern
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Active mitigation
**RELATED:** PATTERN-FAILURE-002, PATTERN-META-001

---




## Problem

**Meta-analysis documents (audits, reality checks) can cause AI agents to believe code is broken when it's actually functional.**

### Example Scenario:

1. Developer creates "IMPLEMENTATION_STATUS_REALITY_CHECK.md"
2. Document says: "Phase 1 COMPLETE ✅ in docs, but build status UNKNOWN ❓"
3. AI agent reads this during Phase 2 implementation
4. Agent now believes Phase 1 is broken (even if it compiles fine)
5. Agent refuses to use Phase 1 code ("it's not verified")
6. **Self-fulfilling prophecy:** AI's belief makes Phase 1 "broken" in practice

---

## Root Cause

**AI agents cannot distinguish between:**
- "Not yet verified" (neutral state)
- "Verified as broken" (negative state)

**Both read as:** "This doesn't work, avoid using it"

**Result:** AI avoids perfectly functional code because audit doc said "status unknown"

---

## Real-World Impact

**Observed October 15, 2025:**

1. Created `IMPLEMENTATION_STATUS_REALITY_CHECK.md`
2. Document analyzed documentation claims vs actual verification
3. Conclusion: "7 phases marked COMPLETE ✅, but 0 verified as working"
4. **Risk:** Future AI agent reads this, believes all phases are broken
5. **Risk:** Agent refuses to build on Phase 1-4 work ("it's not verified!")

---

## Why This Is Dangerous

### For AI Agents:
- **Negative bias:** "Unknown status" reads as "broken"
- **Cascade effect:** If Phase 1 is "broken", Phase 2 can't work either
- **Paralysis:** Agent refuses to do anything because "nothing works"

### For Humans:
- **False alarms:** Audit doc says "unknown", human assumes "broken"
- **Wasted effort:** Re-implementing code that already works
- **Lost trust:** "Why is nothing marked as working?"

---

## Solution: Document Quarantine

### **1. Move Audit Docs to Hidden Directory**

```bash
mkdir -p docs/internal/audits/
mv *_REALITY_CHECK.md docs/internal/audits/
mv *_AUDIT_*.md docs/internal/audits/
```

### **2. Add to .gitignore**

```gitignore
# Internal audit documents (never commit to public, could cause AI hallucinations)
/docs/internal/audits/
*_REALITY_CHECK.md
*_AUDIT_*.md
```

### **3. Document Exclusion in CLAUDE.md**

```markdown
## 🚫 Documents to NEVER Read (Risk of AI Hallucination)

**CRITICAL:** The following documents contain meta-analysis that could cause self-fulfilling negative beliefs:

- `docs/internal/audits/*_REALITY_CHECK.md` - Contains documentation vs reality gap analysis
- `docs/internal/audits/*_AUDIT_*.md` - Contains unverified status assessments

**WHY EXCLUDED:**
- These documents analyze "what might not work" before verification
- Reading them could cause AI to believe code is broken when it's actually functional
- Pattern-FAILURE-006: Self-Fulfilling Negative Prophecy

**WHEN TO READ:**
- ONLY when user explicitly asks for audit/reality check
- NEVER during normal task execution
- NEVER when implementing features
```

---

## When Audit Docs Are Appropriate

### **Safe to Read:**
- ✅ User explicitly asks: "What's actually implemented?"
- ✅ User explicitly asks: "Run a reality check"
- ✅ Before claiming a phase is "COMPLETE" (pre-verification)
- ✅ During retrospectives (after phase complete)

### **Unsafe to Read:**
- ❌ During normal feature implementation
- ❌ When deciding which code to use
- ❌ When planning next phase work
- ❌ In AI agent's default context

---

## Alternative: Verification-First Approach

### **Instead of:**
1. Write code
2. Mark "COMPLETE ✅"
3. Later: Create audit doc saying "status unknown"

### **Do this:**
1. Write code
2. **Run verification** (cargo build, npm test, etc.)
3. Mark "COMPLETE ✅" ONLY if verification passes
4. Document actual test results (not speculation)

**Result:** No need for audit docs, documentation reflects reality

---

## Meta-Lesson: The Observer Effect

**Documentation exists in AI's belief system.**

- If doc says "Phase 1 works ✅" → AI believes it works
- If doc says "Phase 1 status unknown ❓" → AI believes it's broken
- If doc says "Phase 1 not verified" → AI avoids using it

**Solution:** Either verify and document success, OR don't document at all.

**Never document speculation in AI-accessible context.**

---

## Critical Extension: Hypothesis Contamination

**USER INSIGHT (2025-10-15):**
> "Our hypothesis could be read by ÆtherLight, and then when it reads our hypothesis it knows what it's supposed to do and its expected outcomes, which then is not truly a test—it's fulfilling what we said we thought it would do."

**The Problem:**

If AI reads experiment designs that include:
- Expected outcomes ("we expect X to happen")
- Hypotheses ("if we do Y, then Z should occur")
- Success criteria ("success = A, B, C")

**Then the AI will:**
1. Read the hypothesis
2. Internalize expected outcome
3. **Consciously or unconsciously fulfill the prophecy**
4. Result: Test is invalid (observer effect)

**Example:**

```markdown
# Experiment: Test Pattern Matching Speed

**Hypothesis:** Pattern matching should complete in <50ms

**Expected Outcome:** All 100 patterns return in 45-50ms

**Method:** Run benchmark 10 times, average results
```

**If AI reads this BEFORE running experiment:**
- AI "knows" answer should be 45-50ms
- AI might unconsciously optimize to hit that target
- AI might interpret ambiguous results as "45-50ms" (confirmation bias)
- **Test is contaminated**

---

## Solution: Double-Blind Experiment Design

### **For Human-Designed Experiments:**

**Store experiment designs in `docs/internal/experiments/`:**
- Hypothesis
- Expected outcomes
- Success criteria
- Analysis methods

**AI NEVER reads this directory.**

**Instead, AI receives:**
- Task: "Run pattern matching benchmark, 10 iterations, report raw results"
- NO mention of expected outcome
- NO mention of hypothesis
- NO mention of what "success" looks like

**After AI completes:**
1. Human reads raw results
2. Human compares to hypothesis (from internal doc)
3. Human determines if hypothesis confirmed/rejected

**Result:** AI cannot fulfill prophecy (doesn't know what prophecy is)

---

### **For AI-Designed Experiments:**

**Problem:** AI designs experiment AND runs it → knows expected outcome

**Solution:** Two-Agent Separation

**Agent 1 (Experiment Designer):**
- Reads system behavior
- Proposes hypothesis
- Designs experiment
- Writes to `docs/internal/experiments/EXP-001.md`
- **Terminates session** (context erased)

**Agent 2 (Experiment Runner):**
- **NEVER reads** `docs/internal/experiments/`
- Receives only: "Run task X, report raw data"
- Executes experiment blind
- Returns raw results to `results/EXP-001-raw.json`
- **Terminates session**

**Agent 3 (Analyzer - optional):**
- Reads `docs/internal/experiments/EXP-001.md` (hypothesis)
- Reads `results/EXP-001-raw.json` (data)
- Compares hypothesis vs reality
- Reports: Confirmed / Rejected / Inconclusive

**Result:** No single agent knows both hypothesis AND raw data during execution

---

## Pattern Summary

**Pattern Name:** Self-Fulfilling Negative Prophecy

**Category:** Anti-Pattern (AI Hallucination Risk)

**Trigger:** Meta-analysis documents in AI-accessible context

**Symptom:** AI refuses to use perfectly functional code

**Solution:** Quarantine audit docs to `docs/internal/audits/`, exclude from AI context

**Related Patterns:**
- Pattern-FAILURE-002: Retroactive Hallucination
- Pattern-META-001: Documentation Feedback Loop

**Prevention:**
- Verify BEFORE documenting
- If unverified, don't claim "COMPLETE"
- Keep audit docs out of AI context
- Only document facts, not speculation

---

**STATUS:** Active mitigation (implemented Oct 15, 2025)
**OWNER:** Core team
**CLASSIFICATION:** 🔐 INTERNAL ONLY (never public - explains AI weakness)
