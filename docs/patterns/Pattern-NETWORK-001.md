# Pattern-NETWORK-001: Agent Network for Cross-Agent Collaboration

**CREATED:** 2025-10-12 | **STATUS:** Implemented (P3.5-007) | **SOURCE:** PHASE_3.5_INTELLIGENCE_LAYER.md
**CATEGORY:** Uncategorized
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Implemented (P3.5-007) | **SOURCE:** PHASE_3.5_INTELLIGENCE_LAYER.md
**RELATED:** PATTERN-DOMAIN-001, PATTERN-ESCALATION-001, PATTERN-ROUTING-001

---



## Design Decision

Centralized agent network enabling cross-agent queries and multi-domain problem solving via Mentor layer.

---

## Why

**PRINCIPLE:** "Agents collaborate when single-domain expertise is insufficient"

**Problem without cross-agent collaboration:**
- Infrastructure agent can't answer performance questions
- Quality agent can't advise on deployment strategies
- Single-domain solutions miss multi-domain insights

**Network solution:**
- **Agent registry** - All agents register with network on startup
- **Cross-agent queries** - Agents query each other via agent_network.query()
- **Confidence aggregation** - Combine insights from multiple agents
- **Mentor layer** - Level 4 in breadcrumb escalation

---

## Implementation

### AgentNetwork (Rust)

```rust
pub struct AgentNetwork {
    agents: HashMap<Domain, Box<dyn DomainAgent>>,
}

impl AgentNetwork {
    pub fn new() -> Self {
        Self {
            agents: HashMap::new(),
        }
    }

    pub fn register(&mut self, domain: Domain, agent: Box<dyn DomainAgent>) {
        self.agents.insert(domain, agent);
    }

    pub async fn query(&self, domain: Domain, problem: &Problem) -> Result<Solution, String> {
        match self.agents.get(&domain) {
            Some(agent) => agent.solve_with_escalation(problem.clone()).await,
            None => Err(format!("Agent not found for domain: {:?}", domain)),
        }
    }

    pub fn query_multiple(&self, domains: Vec<Domain>, problem: &Problem)
        -> Vec<Result<Solution, String>> {
        domains.iter()
            .map(|domain| self.query(*domain, problem).await)
            .collect()
    }
}
```

---

## Usage Example

**Multi-Domain Query:**

```rust
// Problem requires Infrastructure + Scalability + Deployment expertise
let problem = Problem {
    description: "Deploy high-traffic API with zero downtime".to_string(),
    context: vec![
        "10k requests/second".to_string(),
        "Zero downtime requirement".to_string(),
    ],
    domain_hints: vec![
        Domain::Infrastructure,
        Domain::Scalability,
        Domain::Deployment,
    ],
};

// Infrastructure agent queries network at Mentor level
let mentor_solutions = agent_network.query_multiple(
    vec![Domain::Scalability, Domain::Deployment],
    &problem
).await;

// Aggregate insights:
// - Scalability: "Use load balancer + autoscaling"
// - Deployment: "Use blue-green deployment"
// Combined confidence: 88% (> 85% threshold)
```

---

## Performance

- **Agent registration:** O(1) HashMap insert
- **Single agent query:** <100ms (agent's solve_with_escalation)
- **Multiple agent queries:** <100ms (parallel execution with tokio)
- **Network overhead:** <5ms (in-process HashMap lookup)

**From P3.5-013 integration tests:**
- Agent-to-agent query: <50ms (50% faster than 100ms target) ✅

---

## Related Patterns

- **Pattern-DOMAIN-001:** Domain Agent Trait (implements query_mentor() using AgentNetwork)
- **Pattern-ESCALATION-001:** Breadcrumb Escalation (Mentor is Level 4)
- **Pattern-ROUTING-001:** Domain Routing Table (determines which agents to query)

---

## Status

Complete (P3.5-007) ✅ | Code: `crates/aetherlight-core/src/agent_network.rs` | Tests: Validated in P3.5-013 ✅
