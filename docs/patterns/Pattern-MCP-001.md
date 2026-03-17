# Pattern-MCP-001: Neural Network Routing Architecture

**CREATED:** 2025-10-04
**CATEGORY:** MCP Protocol, Neural Routing
**LANGUAGE:** TypeScript
**QUALITY SCORE:** 0.75
**APPLICABILITY:** General use
**STATUS:** Architectural Design
**RELATED:** - DISTRIBUTED_PATTERN_NETWORK.md (overall architecture)

---




## Design Decision

Use **neural network mesh routing** via MCP servers instead of hierarchical tiers (local → team → global).

---

## Why

**PRINCIPLE:** "Putting boundaries on knowledge is MORE dangerous than bad knowledge."

**Reasoning:**
1. **Bad knowledge can be flagged and corrected** (confidence scoring, validation)
2. **Boundaries prevent discovery** of solutions user doesn't know exist
3. **Regional/domain knowledge doesn't fit hierarchy** (agriculture-midwest ≠ "team tier")
4. **User context determines relevance** (not fixed percentages like 50/30/20)

**Problem with hierarchical tiers:**
- Iowa farmer doesn't know Palo Alto tech exists (but needs IoT sensors for crops)
- EU developer doesn't know Texas agriculture patterns (but building farm app)
- Alaska resident doesn't know permafrost construction techniques (not in "global" tier)
- GDPR compliance is regional legal knowledge (not "team knowledge")

**Neural mesh solution:**
- Query activates relevant domain/region nodes based on semantic analysis
- Cross-domain links surface patterns from unrelated fields
- No artificial boundaries - knowledge flows where needed

---

## Reasoning Chain

1. **User voice input:** "Help me store customer data"
2. **Semantic analysis:** Generate embedding, detect user context (location, domain, history)
3. **Neural activation:** Score ALL domain/region MCP nodes for relevance (not fixed tiers)
   - legal-eu-gdpr: 95% relevance (user in EU)
   - tech-databases: 80% relevance (technical domain)
   - security-encryption: 75% relevance (data protection)
   - agriculture-midwest: 0% relevance (wrong domain)
4. **Parallel queries:** Fetch patterns from top N relevant nodes simultaneously
5. **Confidence aggregation:** Multi-dimensional scoring (domain + region + cross-links)
6. **Cross-domain expansion:** Follow links to related patterns user didn't ask for
7. **Return results:** Patterns ranked by aggregated confidence

---

## Implementation

### Neural Router (Core)

```typescript
/**
 * ÆtherLight Neural Network Router
 *
 * DESIGN DECISION: Dynamic relevance scoring (not fixed tier weights)
 * WHY: User context determines which knowledge nodes activate
 *
 * REASONING CHAIN:
 * 1. Analyze user query semantically (embeddings)
 * 2. Score ALL MCP nodes for relevance (0.0-1.0)
 * 3. Activate top N nodes (threshold >0.5 relevance)
 * 4. Query in parallel (network mesh, not chain)
 * 5. Aggregate results with weighted confidence
 * 6. Follow cross-domain links (discover unknown patterns)
 *
 * PATTERN: Pattern-MCP-001 (Neural Network Routing)
 */

class AetherlightNeuralRouter {
  mcpNodes: Map<string, MCPNodeInfo>;  // All registered MCP nodes
  dht: KademliaDHT;                     // DHT for pattern discovery

  async routeQuery(userPrompt: string, userContext: UserContext): Promise<Pattern[]> {
    // 1. Semantic analysis
    const embedding = await this.generateEmbedding(userPrompt);

    // 2. Score ALL nodes for relevance (not just 3 tiers)
    const relevanceScores = await this.scoreAllNodes(embedding, userContext);
    // Example result:
    // [
    //   { node: "legal-eu-gdpr", relevance: 0.95 },
    //   { node: "tech-databases", relevance: 0.80 },
    //   { node: "security-encryption", relevance: 0.75 },
    //   { node: "legal-us-state", relevance: 0.20 },
    //   { node: "agriculture-midwest", relevance: 0.01 }
    // ]

    // 3. Activate nodes above threshold (>0.5 relevance)
    const activeNodes = relevanceScores.filter(s => s.relevance > 0.5);

    // 4. Query active nodes in parallel (mesh network)
    const mcpResults = await Promise.all(
      activeNodes.map(score =>
        this.queryMCPNode(score.node, userPrompt, score.relevance)
      )
    );

    // 5. Aggregate patterns with weighted confidence
    const aggregatedPatterns = await this.aggregatePatterns(mcpResults);

    // 6. Follow cross-domain links (discover related patterns)
    const expandedPatterns = await this.followCrossLinks(aggregatedPatterns);

    // 7. Return top patterns
    return expandedPatterns.sort((a, b) => b.confidence - a.confidence).slice(0, 10);
  }

  private async scoreAllNodes(
    embedding: number[],
    userContext: UserContext
  ): Promise<Array<{ node: string; relevance: number }>> {
    const scores = [];

    for (const [nodeId, nodeInfo] of this.mcpNodes) {
      // Multi-dimensional relevance scoring
      const domainScore = await this.scoreDomainRelevance(embedding, nodeInfo.domain);
      const regionScore = await this.scoreRegionRelevance(userContext.location, nodeInfo.region);
      const historyScore = await this.scoreHistoricalSuccess(userContext.userId, nodeInfo);

      // Weighted combination (NOT fixed 50/30/20)
      const relevance =
        domainScore * 0.60 +    // Domain most important
        regionScore * 0.30 +    // Region secondary
        historyScore * 0.10;    // Past success tertiary

      scores.push({ node: nodeId, relevance });
    }

    return scores.sort((a, b) => b.relevance - a.relevance);
  }

  private async followCrossLinks(patterns: Pattern[]): Promise<Pattern[]> {
    const expanded = [...patterns];

    for (const pattern of patterns) {
      // Follow cross-domain links (e.g., agriculture → weather)
      for (const link of pattern.crossLinks || []) {
        const linkedPattern = await this.fetchPatternByLink(link);
        if (linkedPattern && !expanded.find(p => p.cid === linkedPattern.cid)) {
          expanded.push(linkedPattern);
        }
      }
    }

    return expanded;
  }
}
```

### MCP Node Registration

```typescript
/**
 * Register domain/region MCP nodes
 *
 * DESIGN DECISION: Nodes self-register with metadata
 * WHY: Decentralized network, no central authority
 */

interface MCPNodeInfo {
  nodeId: string;
  mcpUrl: string;
  domain: string;          // agriculture, tech, legal, medical, etc.
  region?: string;         // us-midwest, eu, asia, global, etc.
  patterns: PatternMetadata[];
  crossLinks: string[];    // Links to other domains
}

// Example: Agriculture MCP node
const agricultureMidwestNode: MCPNodeInfo = {
  nodeId: "agriculture-us-midwest",
  mcpUrl: "mcp://agriculture-midwest.aetherlight.network",
  domain: "agriculture",
  region: "us-midwest",
  patterns: [
    {
      cid: "pattern-corn-rotation-iowa",
      name: "Corn rotation schedules for Iowa farms",
      confidence: 0.94
    }
  ],
  crossLinks: [
    "weather://us-midwest/frost-dates",     // Cross-domain to weather
    "tech-iot://agriculture/soil-sensors",  // Cross-domain to tech
    "soil-science://global/nitrogen"        // Cross-domain to science
  ]
};

// Example: Legal EU GDPR node
const legalEUNode: MCPNodeInfo = {
  nodeId: "legal-eu-gdpr",
  mcpUrl: "mcp://legal-eu.aetherlight.network",
  domain: "legal",
  region: "eu",
  patterns: [
    {
      cid: "pattern-gdpr-data-storage",
      name: "GDPR-compliant data storage patterns",
      confidence: 0.96
    }
  ],
  crossLinks: [
    "tech-databases://global/encryption",   // Cross-domain to tech
    "security://eu/data-protection"         // Cross-domain to security
  ]
};
```

---

## Pattern References

**USES:**
- **Pattern-DHT-001** (Content-Addressed Pattern Storage) - DHT discovery layer
- **Pattern-TRUST-001** (Circle of Trust Key Sharing) - Privacy on network

**RELATED:**
- DISTRIBUTED_PATTERN_NETWORK.md (overall architecture)
- MCP Protocol Specification (Anthropic open standard)

**REPLACES:**
- Three-tier hierarchy (local 50% → team 30% → global 20%) - DEPRECATED

---

## Future Improvements

### Phase 1 (Current): Hybrid Routing
- Neural routing for discovery
- Still use Git-like sync for convenience (backward compatible)
- MCP servers as optional protocol (can use REST APIs initially)

### Phase 2 (Post-Launch): Full MCP Network
- All pattern sharing via MCP protocol
- DHT for complete decentralization
- Deprecate centralized index (aetherlight.ai becomes discovery portal only)

### Phase 3 (Long-Term): DAO Governance
- Community votes on new domain/region nodes
- Pattern validation via DAO (staking mechanism)
- Decentralized quality control (see DISTRIBUTED_PATTERN_NETWORK.md)

---

## Related Tasks

- **P3.5-001:** Build MCP server SDK (Node.js, Python, Rust)
- **P3.5-002:** Implement neural router (semantic scoring)
- **P3.8-001:** GitHub MCP servers for pre-training domains

---

## Success Metrics

**Performance:**
- Query latency: <200ms (parallel MCP queries)
- Relevance accuracy: >85% (correct domain activation)
- Cross-domain discovery: >30% of results include linked patterns

**Quality:**
- User satisfaction: "Found solution I didn't know existed" feedback
- Diversity: Patterns from >3 domains per complex query
- Precision: Top result confidence >80%

---

## Example Queries

### Query 1: Iowa Farmer (Agriculture + Tech)

**Input:** "My corn yield is low this year"

**Neural Activation:**
- agriculture-us-midwest: 0.98 (direct match)
- weather-us-midwest: 0.85 (correlated)
- soil-science-global: 0.70 (relevant)
- tech-iot-agriculture: 0.60 (IoT sensors trend)

**Cross-Links Followed:**
- agriculture → weather (frost dates, rainfall)
- agriculture → tech-iot (soil nitrogen sensors) ← USER DIDN'T KNOW THIS EXISTS

**Result:** User discovers IoT sensors for soil monitoring (from tech domain)

---

### Query 2: EU Developer (Legal + Tech)

**Input:** "Build authentication for SaaS app"

**Neural Activation:**
- tech-auth-global: 0.90 (direct match)
- legal-eu-gdpr: 0.85 (user in EU = regional trigger)
- security-encryption: 0.75 (related)

**Cross-Links Followed:**
- tech-auth → legal-gdpr (GDPR compliance requirements)
- legal-gdpr → security (encryption standards)

**Result:** User gets GDPR-compliant auth pattern (legal domain surfaced automatically)

---

**STATUS:** Design complete, implementation in Phase 3.5
**NEXT:** Create Pattern-DHT-001 (DHT discovery implementation)
