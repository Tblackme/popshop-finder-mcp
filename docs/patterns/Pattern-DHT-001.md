# Pattern-DHT-001: Content-Addressed Pattern Storage with Kademlia DHT

**CREATED:** 2025-10-04
**CATEGORY:** Uncategorized
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Architecture Design
**RELATED:** PATTERN-MCP-001, PATTERN-RUST-009, PATTERN-ASYNC-003, PATTERN-ERASURE-001, PATTERN-TRUST-001

---




## PROBLEM

**Context:**
The ÆtherLight neural network requires distributed pattern discovery across a mesh of nodes without centralized coordination. Traditional centralized registries create:
- Single points of failure
- Bottlenecks for global pattern discovery
- Privacy concerns (central authority sees all pattern queries)
- Censorship vulnerabilities (central authority can block patterns)

**Challenge:**
How do you enable pattern discovery across thousands of nodes where:
1. Patterns are content-addressed (hash-based identity)
2. No central authority controls the index
3. Discovery is fast (<100ms for 90% of queries)
4. Network is resilient to node churn (nodes joining/leaving)
5. Queries remain private (no central logging)

**User Principle:**
"Putting boundaries on knowledge is MORE dangerous than bad knowledge" - the system must resist censorship while maintaining quality through reputation, not gatekeeping.

---

## SOLUTION

**DESIGN DECISION:** Use Kademlia Distributed Hash Table (DHT) for pattern index discovery

**WHY:**
- **Proven at Scale:** Powers BitTorrent (300M+ users), IPFS, Ethereum - battle-tested for decentralized discovery
- **Fast Lookups:** O(log N) hops to find any pattern in network of N nodes
- **Self-Healing:** Automatically routes around failed nodes, handles churn
- **Privacy-Preserving:** Queries don't reveal requester identity to all nodes
- **Content-Addressed:** Natural fit for hash-based pattern identity (SHA-256)

**REASONING CHAIN:**

1. **Content Addressing Foundation:**
   - Each pattern gets unique hash: `pattern_hash = SHA256(pattern_content)`
   - Example: `a3f5c8e2...` (64 hex chars)
   - Hash serves as both identity AND lookup key
   - Immutable patterns = stable addressing

2. **Kademlia Distance Metric:**
   - XOR distance: `distance(A, B) = A XOR B`
   - Example: `distance(node_abc123, pattern_def456) = abc123 XOR def456`
   - Nodes store patterns "close" to their node ID in XOR space
   - Routing converges logarithmically

3. **Distributed Storage:**
   - Pattern stored on K closest nodes (K=20 typical)
   - Example: Pattern `a3f5c8e2...` stored on 20 nodes with IDs closest to `a3f5c8e2...`
   - Redundancy ensures availability even if 15/20 nodes fail
   - No single node is critical

4. **Lookup Process:**
   - Query for pattern `pattern_hash`
   - Ask α closest known nodes (α=3 typical)
   - Each returns closer nodes OR the pattern itself
   - Converges in log₂(N) hops (e.g., 20 hops for 1M nodes)
   - Typical latency: 50-100ms

5. **Node Joining/Leaving:**
   - New node announces with `node_id = random_256_bits`
   - Existing nodes update routing tables (K-buckets)
   - Patterns republished periodically (every 24 hours)
   - Failed nodes detected via timeouts, patterns re-replicated

**ALTERNATIVES CONSIDERED:**

- **Centralized Registry (GitHub model):**
  - **Rejected:** Single point of failure, censorship risk, privacy concerns
  - Does NOT align with "boundaries on knowledge are dangerous" principle

- **Chord DHT:**
  - **Rejected:** More complex routing, slower lookups (O(log N) but higher constant factors)
  - Kademlia has better empirical performance

- **Blockchain-Based Index:**
  - **Rejected:** High latency (block confirmation times), expensive (gas fees), overkill for discovery
  - Better suited for governance (DAO votes), not pattern lookup

- **Gossip Protocols (Epidemic Broadcast):**
  - **Rejected:** High bandwidth overhead (O(N²) messages), slower convergence
  - Good for small clusters, not global mesh

---

## IMPLEMENTATION

### Core Data Structures

```rust
/**
 * Kademlia node in the ÆtherLight neural network
 *
 * DESIGN DECISION: 256-bit node IDs matching pattern hash space
 * WHY: Enables XOR distance metric for routing, no ID collisions in practice
 *
 * REASONING CHAIN:
 * 1. Node generates random 256-bit ID on first boot (ed25519 public key hash)
 * 2. ID persists across restarts (stored in config)
 * 3. ID determines which patterns node is "close" to
 * 4. Routing table organizes contacts by XOR distance buckets
 */
use sha2::{Sha256, Digest};
use std::net::SocketAddr;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NodeId([u8; 32]); // 256 bits

impl NodeId {
    /// Generate random node ID from ed25519 public key
    pub fn generate() -> Self {
        let keypair = ed25519_dalek::Keypair::generate(&mut rand::rngs::OsRng);
        let hash = Sha256::digest(keypair.public.as_bytes());
        NodeId(hash.into())
    }

    /// XOR distance between two node IDs
    pub fn distance(&self, other: &NodeId) -> NodeId {
        let mut result = [0u8; 32];
        for i in 0..32 {
            result[i] = self.0[i] ^ other.0[i];
        }
        NodeId(result)
    }

    /// Count leading zero bits (determines K-bucket index)
    pub fn leading_zeros(&self) -> usize {
        self.0.iter()
            .take_while(|&&b| b == 0)
            .count() * 8
            + self.0.iter()
                .find(|&&b| b != 0)
                .map(|b| b.leading_zeros() as usize)
                .unwrap_or(256)
    }
}

/**
 * K-bucket: stores K contacts at specific distance range
 *
 * DESIGN DECISION: 160 buckets (for 256-bit IDs), K=20 contacts per bucket
 * WHY: Balances routing table size vs lookup speed
 *
 * PATTERN: Uses Pattern-RUST-009 (Bounded Collections with LRU eviction)
 */
#[derive(Clone, Debug)]
pub struct KBucket {
    contacts: Vec<Contact>,
    max_size: usize, // K = 20
}

#[derive(Clone, Debug)]
pub struct Contact {
    node_id: NodeId,
    addr: SocketAddr,
    last_seen: std::time::Instant,
}

impl KBucket {
    pub fn new(k: usize) -> Self {
        KBucket {
            contacts: Vec::with_capacity(k),
            max_size: k,
        }
    }

    /// Add contact, evict least-recently-seen if full
    pub fn insert(&mut self, contact: Contact) {
        if let Some(pos) = self.contacts.iter().position(|c| c.node_id == contact.node_id) {
            // Update existing contact (move to end = most recent)
            self.contacts.remove(pos);
            self.contacts.push(contact);
        } else if self.contacts.len() < self.max_size {
            // Add new contact
            self.contacts.push(contact);
        } else {
            // Evict least-recently-seen (first element)
            self.contacts.remove(0);
            self.contacts.push(contact);
        }
    }

    /// Get α closest contacts to target
    pub fn closest(&self, target: &NodeId, alpha: usize) -> Vec<Contact> {
        let mut sorted = self.contacts.clone();
        sorted.sort_by_key(|c| c.node_id.distance(target).0);
        sorted.into_iter().take(alpha).collect()
    }
}

/**
 * Routing table: 160 K-buckets organized by XOR distance
 *
 * DESIGN DECISION: Array of K-buckets indexed by leading zero bits
 * WHY: O(1) bucket lookup, efficient routing
 */
#[derive(Clone, Debug)]
pub struct RoutingTable {
    node_id: NodeId,
    buckets: [KBucket; 256], // One bucket per bit position
}
```

### Pattern Storage Layer

```rust
/**
 * Pattern metadata stored in DHT
 *
 * DESIGN DECISION: Store metadata (hash, size, creator) in DHT, full pattern via MCP
 * WHY: DHT optimized for small values (<1KB), patterns can be large (>1MB)
 *
 * REASONING CHAIN:
 * 1. DHT stores lightweight metadata (who has the pattern)
 * 2. Client retrieves metadata from DHT (fast, <100ms)
 * 3. Client fetches full pattern via MCP from listed providers (streaming)
 * 4. Separation of concerns: discovery vs transfer
 */
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PatternMetadata {
    /// Content hash (SHA-256 of pattern)
    pub hash: [u8; 32],

    /// Pattern size in bytes
    pub size: u64,

    /// Creator's public key (for attribution)
    pub creator: ed25519_dalek::PublicKey,

    /// List of nodes currently hosting this pattern
    pub providers: Vec<SocketAddr>,

    /// Confidence score (optional, for ranking results)
    pub confidence: Option<f64>,

    /// Creation timestamp
    pub created_at: u64, // Unix timestamp

    /// Digital signature (creator signs hash)
    pub signature: ed25519_dalek::Signature,
}

impl PatternMetadata {
    /// Verify signature matches creator
    pub fn verify(&self) -> bool {
        self.creator.verify(&self.hash, &self.signature).is_ok()
    }
}
```

### Lookup Algorithm

```rust
/**
 * Iterative FIND_NODE lookup (Kademlia algorithm)
 *
 * DESIGN DECISION: Iterative (not recursive) lookups
 * WHY: Requester controls routing path, better privacy, can parallelize queries
 *
 * REASONING CHAIN:
 * 1. Start with α closest known nodes to target
 * 2. Query them in parallel for closer nodes
 * 3. Add responses to candidate set
 * 4. Repeat with next α closest unqueried nodes
 * 5. Stop when no closer nodes found (converged)
 * 6. Return K closest nodes
 *
 * PATTERN: Uses Pattern-ASYNC-003 (Parallel async queries with timeout)
 */
pub async fn find_node(
    routing_table: &RoutingTable,
    target: &NodeId,
    alpha: usize,
    k: usize,
) -> Vec<Contact> {
    let mut queried = HashSet::new();
    let mut candidates = BTreeMap::new(); // Sorted by distance to target

    // Seed with α closest known nodes
    for contact in routing_table.closest(target, alpha) {
        let distance = contact.node_id.distance(target);
        candidates.insert(distance, contact);
    }

    loop {
        // Get α closest unqueried nodes
        let to_query: Vec<_> = candidates
            .values()
            .filter(|c| !queried.contains(&c.node_id))
            .take(alpha)
            .cloned()
            .collect();

        if to_query.is_empty() {
            break; // Converged
        }

        // Query in parallel
        let futures: Vec<_> = to_query.iter()
            .map(|contact| {
                queried.insert(contact.node_id.clone());
                rpc::find_node_rpc(contact.addr, target)
            })
            .collect();

        let responses = futures::future::join_all(futures).await;

        // Add new contacts to candidates
        for result in responses {
            if let Ok(contacts) = result {
                for contact in contacts {
                    let distance = contact.node_id.distance(target);
                    candidates.insert(distance, contact);
                }
            }
        }
    }

    // Return K closest
    candidates.into_values().take(k).collect()
}
```

### Pattern Lookup (High-Level API)

```rust
/**
 * Look up pattern metadata by hash
 *
 * DESIGN DECISION: Two-phase lookup (metadata from DHT, content via MCP)
 * WHY: DHT fast for small data, MCP optimized for streaming large patterns
 *
 * USAGE:
 * ```rust
 * let pattern_hash = sha256("function createUser() { ... }");
 * let metadata = dht.lookup_pattern(&pattern_hash).await?;
 * let pattern = mcp_client.fetch_pattern(&metadata).await?;
 * ```
 */
pub async fn lookup_pattern(
    &self,
    pattern_hash: &[u8; 32],
) -> Result<PatternMetadata, DhtError> {
    // 1. Find nodes closest to pattern_hash
    let target = NodeId(pattern_hash.clone());
    let closest_nodes = find_node(&self.routing_table, &target, ALPHA, K).await;

    // 2. Query those nodes for pattern metadata
    for node in closest_nodes {
        if let Ok(Some(metadata)) = rpc::get_value_rpc(node.addr, pattern_hash).await {
            // 3. Verify signature
            if metadata.verify() {
                return Ok(metadata);
            }
        }
    }

    Err(DhtError::PatternNotFound)
}
```

---

## WHEN TO USE

**Use Kademlia DHT when:**
- Building decentralized pattern discovery (no central registry)
- Network has >1000 nodes (DHT efficiency kicks in at scale)
- Patterns are immutable (content-addressed by hash)
- Privacy matters (no central query logging)
- Censorship resistance required (no single authority)

**Do NOT use when:**
- Network is small (<100 nodes) - centralized registry simpler
- Patterns are mutable - DHT assumes content = hash
- Low latency critical (<10ms) - DHT adds routing hops
- Strong consistency required - DHT is eventually consistent

---

## INTEGRATION WITH ÆTHERLIGHT

### Phase 5 Implementation (Backend, Weeks 13-14)

**Deliverables:**
1. **Kademlia DHT Node** (`aetherlight-dht` crate):
   - Node ID generation (ed25519-based)
   - Routing table (256 K-buckets)
   - RPC protocol (FIND_NODE, FIND_VALUE, STORE, PING)
   - Bootstrap process (seed nodes)

2. **Pattern Publication**:
   - When user creates pattern → compute hash
   - Store metadata on K closest nodes
   - Update local routing table
   - Announce to MCP network as provider

3. **Pattern Discovery**:
   - User queries pattern by hash or keyword
   - DHT lookup returns metadata + providers
   - MCP fetch from closest provider
   - Cache locally (become provider)

4. **Redundancy with Erasure Coding**:
   - Split pattern into N shards (e.g., N=10)
   - Apply Reed-Solomon encoding (need K=6 to reconstruct)
   - Store shards on different nodes
   - Retrieve K shards → reconstruct pattern
   - **See:** Pattern-ERASURE-001 (Reed-Solomon Pattern Storage)

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| DHT lookup latency | <100ms (p90) | time(find_node) |
| Bootstrap time | <5s | time(join network) |
| Routing table size | <10MB | memory footprint |
| Pattern availability | >99.9% (with K=20 replicas) | uptime monitoring |
| Network churn tolerance | 50% nodes offline → still works | chaos testing |

---

## EDGE CASES

### 1. **Sybil Attack (Malicious Nodes Flood Network)**
**Problem:** Attacker creates 10,000 nodes with IDs near target pattern, claims to have it but returns garbage.

**Solution:**
- **Reputation system:** Track node behavior (Pattern-TRUST-001)
- **Signature verification:** Pattern metadata must be signed by creator
- **Multi-source validation:** Fetch pattern from multiple providers, compare hashes
- **Economic cost:** Require stake to join network (future DAO governance)

### 2. **Network Partition (Internet Split)**
**Problem:** DHT splits into two disconnected networks, patterns only discoverable in one partition.

**Solution:**
- **Eventual consistency:** When partition heals, nodes republish patterns
- **Bridge nodes:** Some nodes connected to multiple regions act as bridges
- **Fallback to MCP broadcast:** If DHT lookup fails, broadcast query to known peers

### 3. **Node Churn (Rapid Join/Leave)**
**Problem:** 30% of nodes go offline simultaneously, patterns become unavailable.

**Solution:**
- **K=20 replicas:** Losing 15 nodes still leaves 5 with pattern
- **Proactive republishing:** Nodes republish patterns every 24 hours
- **Monitoring:** Detect low replica count, trigger re-replication

### 4. **Hash Collision (Two Patterns Same Hash)**
**Problem:** SHA-256 collision creates ambiguity (astronomically unlikely but theoretically possible).

**Solution:**
- **Accept impossibility:** 2^256 space makes collision chance ~0
- **If collision detected:** Store both patterns under same key, client verifies signature
- **Future-proof:** Design allows migration to SHA-3 if SHA-2 broken

---

## RELATED PATTERNS

- **Pattern-MCP-001:** Neural Network Routing Architecture (MCP layer above DHT)
- **Pattern-TRUST-001:** Circle of Trust Key Sharing (Shamir secret sharing for encrypted patterns)
- **Pattern-ERASURE-001:** Reed-Solomon Pattern Storage (to be created - redundancy via erasure coding)
- **Pattern-ASYNC-003:** Parallel Async Queries (used in find_node algorithm)

---

## REFERENCES

**Academic:**
- Maymounkov & Mazières (2002): "Kademlia: A Peer-to-Peer Information System Based on the XOR Metric"
- Baumgart & Mies (2007): "S/Kademlia: A Practicable Approach Towards Secure Key-Based Routing"

**Production Implementations:**
- **libp2p Kademlia:** IPFS DHT implementation (Rust, Go, JS)
- **BitTorrent Mainline DHT:** 20M+ nodes, proven at scale
- **Ethereum Discovery v5:** Node discovery for Ethereum network

**Code Examples:**
- `libp2p-kad` crate: https://docs.rs/libp2p-kad
- IPFS Amino DHT: https://github.com/ipfs/specs/blob/master/IPFS_DHT.md

---

## FUTURE

### Phase 5 Enhancements
- **Adaptive K:** Adjust replica count based on pattern popularity
- **Geographic awareness:** Prefer nearby nodes for faster retrieval
- **Bandwidth optimization:** Compress metadata in DHT responses

### Post-Launch (DAO Governance Era)
- **Stake-weighted routing:** Nodes with higher reputation get priority
- **Byzantine fault tolerance:** Tolerate malicious nodes via consensus
- **Cross-chain integration:** Bridge to Ethereum/Cosmos for pattern NFTs

---

## METRICS TO TRACK

**During Development (Phase 5):**
- DHT lookup success rate (target: >99%)
- Median lookup latency (target: <50ms)
- Routing table convergence time (target: <10s)
- Pattern availability under churn (target: >99.9% with K=20)

**Post-Deployment:**
- Network size (number of active nodes)
- Query volume (patterns looked up per second)
- Churn rate (nodes joining/leaving per hour)
- Average hop count (should be ~log₂(N))

---

**PATTERN CONFIDENCE:** High (Kademlia proven at 100M+ user scale)
**IMPLEMENTATION COMPLEXITY:** Medium (well-documented, libraries exist)
**RISK LEVEL:** Low (fallback to centralized discovery if DHT fails)

**STATUS:** Ready for Phase 5 Implementation

---

**LAST UPDATED:** 2025-10-04
**NEXT REVIEW:** After Phase 1-4 completion (Week 12)
