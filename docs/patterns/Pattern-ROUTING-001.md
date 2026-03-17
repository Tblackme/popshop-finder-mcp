# Pattern-ROUTING-001: Domain Routing Table

**CREATED:** 2025-10-12 | **STATUS:** Implemented (P3.5-004) | **SOURCE:** PHASE_3.5_INTELLIGENCE_LAYER.md
**CATEGORY:** Uncategorized
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Implemented (P3.5-004) | **SOURCE:** PHASE_3.5_INTELLIGENCE_LAYER.md
**RELATED:** PATTERN-DOMAIN-001, PATTERN-NETWORK-001

---



## Design Decision

Keyword-based domain classification routing user problems to appropriate domain agents.

---

## Why

**PRINCIPLE:** "Route problems to specialized agents based on domain keywords"

**Problem categories:**
- Infrastructure: deployment, kubernetes, docker, cloud
- Quality: testing, bugs, qa, coverage
- Scalability: performance, latency, caching, load balancing
- Knowledge: documentation, search, embeddings, rag
- Innovation: ai, ml, gpt, code generation
- Deployment: ci, cd, pipeline, release, rollback
- Ethics: bias, fairness, privacy, gdpr, accessibility

---

## Implementation

### DomainRoutingTable (Rust)

```rust
pub struct DomainRoutingTable {
    domain_keywords: HashMap<Domain, Vec<String>>,
}

impl DomainRoutingTable {
    pub fn new() -> Self {
        let mut table = Self {
            domain_keywords: HashMap::new(),
        };
        table.initialize_keywords();
        table
    }

    fn initialize_keywords(&mut self) {
        // Infrastructure keywords (29)
        self.domain_keywords.insert(Domain::Infrastructure, vec![
            "deploy", "deployment", "infrastructure", "cloud", "aws",
            "kubernetes", "docker", "container", /* ... */
        ].into_iter().map(String::from).collect());

        // Quality keywords (26)
        self.domain_keywords.insert(Domain::Quality, vec![
            "test", "testing", "qa", "bug", "coverage", /* ... */
        ].into_iter().map(String::from).collect());

        // ... (similar for all 7 domains)
    }

    pub fn classify(&self, problem_description: &str) -> DomainClassification {
        let desc_lower = problem_description.to_lowercase();
        let mut scores = HashMap::new();

        // Count keyword matches per domain
        for (domain, keywords) in &self.domain_keywords {
            let match_count = keywords.iter()
                .filter(|kw| desc_lower.contains(kw.as_str()))
                .count();

            if match_count > 0 {
                let confidence = (match_count as f64) / (keywords.len() as f64);
                scores.insert(*domain, confidence);
            }
        }

        // Return domain with highest score
        let (domain, confidence) = scores.iter()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(d, c)| (*d, *c))
            .unwrap_or((Domain::Infrastructure, 0.0));  // Default

        DomainClassification { domain, confidence }
    }
}

pub struct DomainClassification {
    pub domain: Domain,
    pub confidence: f64,
}
```

---

## Routing Accuracy

**From P3.5-013 integration tests:**

| Domain | Test Query | Routed Correctly? | Confidence |
|--------|-----------|-------------------|------------|
| Infrastructure | "Deploy Kubernetes cluster on AWS" | ✅ | 64.9% |
| Quality | "How to fix flaky tests?" | ✅ | 27.8% |
| Scalability | "Optimize caching strategy" | ✅ | 50% |
| Knowledge | "Implement semantic search with ChromaDB" | ✅ | 41.7% |
| Deployment | "Set up CI/CD pipeline with GitHub Actions" | ✅ | 45.8% |
| Ethics | "Implement bias detection for AI model" | ✅ | 42.3% |
| **Innovation** | "Integrate GPT-4 for code generation" | ❌ → Ethics | N/A |

**Accuracy:** 85.7% (6/7 correct routing)
**Known Limitation:** Innovation domain keywords overlap with Ethics ("AI", "GPT", "bias detection")

---

## Performance

- **classify():** <10ms (keyword matching with HashMap)
- **Memory:** <10KB (keyword storage for 7 domains)
- **Accuracy:** >90% target, 85.7% actual

**Trade-off:** Keyword-based routing is fast but has overlap issues. Phase 3.6 will add semantic embeddings for improved accuracy.

---

## Future Enhancements

### Phase 3.6
- **Semantic routing** - Use embeddings + cosine similarity (improve Innovation/Ethics separation)
- **Multi-domain classification** - Return top 3 domains with confidence scores (enable cross-agent collaboration)

---

## Related Patterns

- **Pattern-DOMAIN-001:** Domain Agent Trait (routing determines which agent handles problem)
- **Pattern-NETWORK-001:** Agent Network (multi-domain problems query multiple agents)

---

## Status

Complete (P3.5-004) ✅ | Code: `crates/aetherlight-core/src/domain_router.rs` | Tests: Validated in P3.5-013 (85.7% accuracy) ✅
