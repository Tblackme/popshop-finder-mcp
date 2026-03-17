# Pattern-TRUST-001: Circle of Trust Key Sharing with Shamir Secret Sharing

**CREATED:** 2025-10-04
**CATEGORY:** Uncategorized
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.90
**APPLICABILITY:** General use
**STATUS:** Architecture Design
**RELATED:** PATTERN-DHT-001, PATTERN-MCP-001, PATTERN-CRYPTO-001, PATTERN-AUDIT-001

---




## PROBLEM

**Context:**
ÆtherLight enables teams to share patterns within a "circle of trust" (e.g., legal team, marketing team, engineering squad). Patterns may contain:
- Proprietary code snippets (trade secrets)
- Domain-specific reasoning (competitive advantage)
- Sensitive context (client names in legal patterns)

**Privacy Requirements:**
1. **Team-only access:** Only circle members can decrypt patterns
2. **No single point of failure:** No single member holds the master key
3. **Member join/leave:** Add/remove members without re-encrypting all patterns
4. **Threshold recovery:** If K out of N members collaborate, can reconstruct key (e.g., 3 out of 5)
5. **Deniability:** Can't prove which members accessed pattern (privacy from surveillance)

**User Principle:**
"Putting boundaries on knowledge is MORE dangerous than bad knowledge" - the system must enable private collaboration WITHOUT enabling censorship. Circle members control access, not a central authority.

**Challenge:**
How do you encrypt patterns for a team where:
- Members can join/leave dynamically
- No central key server (decentralized trust)
- Threshold recovery (K-of-N) for key loss scenarios
- Compatible with DHT storage (Pattern-DHT-001)

---

## SOLUTION

**DESIGN DECISION:** Use Shamir Secret Sharing for symmetric key distribution + hybrid encryption

**WHY:**
- **Threshold Security:** Requires K members to collaborate (prevents single compromised device)
- **No Central Authority:** Key split among members, no server holds master key
- **Mathematically Proven:** Based on polynomial interpolation, information-theoretically secure
- **Flexible Membership:** Add/remove members by redistributing shares
- **Industry Standard:** Used in cryptocurrency wallets (multi-sig), HSM key backup, military systems

**REASONING CHAIN:**

1. **Hybrid Encryption Architecture:**
   - **Pattern encrypted with:** AES-256-GCM (symmetric, fast, authenticated)
   - **AES key encrypted with:** Shamir secret shares (one per circle member)
   - **Why hybrid:** AES fast for large patterns (1MB+), Shamir distributes key securely

2. **Shamir Secret Sharing Mathematics:**
   - **Secret:** AES-256 key (32 bytes)
   - **Threshold:** K = 3 (minimum members to reconstruct)
   - **Total shares:** N = 5 (total circle members)
   - **Algorithm:** Polynomial interpolation over finite field GF(2^256)
   - **Property:** Any 3 shares → reconstruct key, any 2 shares → zero information

3. **Circle Initialization:**
   ```
   1. Team leader creates circle (generates random AES-256 key)
   2. Split key into N=5 shares using Shamir (K=3 threshold)
   3. Distribute shares via MCP (encrypted with each member's public key)
   4. Members store shares in local keychain (OS-protected)
   5. Delete original AES key (only shares exist)
   ```

4. **Pattern Encryption Flow:**
   ```
   1. Author writes pattern → generates content hash
   2. Encrypt pattern with circle's AES-256 key
   3. Store encrypted pattern in DHT (Pattern-DHT-001)
   4. Metadata includes circle_id (identifies which key needed)
   5. Non-members see encrypted blob (can't decrypt)
   ```

5. **Pattern Decryption Flow:**
   ```
   1. Member retrieves encrypted pattern from DHT
   2. Check circle_id → knows which shares needed
   3. Collect K shares from K circle members (via MCP)
   4. Reconstruct AES key using Lagrange interpolation
   5. Decrypt pattern with AES-256-GCM
   6. Verify hash matches metadata (integrity check)
   ```

6. **Member Join/Leave:**
   - **Add member:** Generate new share, send via encrypted MCP message
   - **Remove member:** Rotate AES key, redistribute new shares to remaining members
   - **Key rotation:** Re-encrypt all patterns with new key (background job)

**ALTERNATIVES CONSIDERED:**

- **Public Key Encryption (PGP model):**
  - **Rejected:** Slow for large patterns (RSA/ECDH max 256 bytes per operation)
  - Would require chunking patterns, complex key management
  - No threshold property (all-or-nothing access)

- **Symmetric Key with Centralized Server:**
  - **Rejected:** Single point of failure, privacy risk (server sees all access)
  - Against decentralization principle
  - Vulnerable to government subpoenas

- **Multi-Signature Wallets (Blockchain):**
  - **Rejected:** Overkill (don't need blockchain consensus for key sharing)
  - High latency (block confirmation)
  - Expensive (gas fees)
  - Shamir achieves same threshold property without blockchain overhead

- **Threshold ECDH (tECDH):**
  - **Considered:** More complex, requires interactive key generation ceremony
  - Shamir simpler: non-interactive, well-understood
  - tECDH better for signing (not needed here)

---

## IMPLEMENTATION

### Core Cryptographic Primitives

```rust
/**
 * Shamir secret sharing for ÆtherLight circle of trust
 *
 * DESIGN DECISION: Use vsss-rs crate (Verifiable Secret Sharing Scheme)
 * WHY: Production-ready, includes verification (prevents malicious shares)
 *
 * REASONING CHAIN:
 * 1. Generate random polynomial of degree K-1
 * 2. Secret is y-intercept (P(0) = secret)
 * 3. Evaluate polynomial at N distinct points (shares)
 * 4. Distribute shares to circle members
 * 5. Reconstruct via Lagrange interpolation (need K shares)
 */
use vsss_rs::{Shamir, Share};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use aes_gcm::aead::{Aead, NewAead};

/**
 * Circle of trust for pattern sharing
 *
 * DESIGN DECISION: Each circle has unique AES-256 key split via Shamir
 * WHY: Enables team-specific encryption without key server
 *
 * PATTERN: Uses Pattern-CRYPTO-001 (Hybrid Encryption for Performance)
 */
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Circle {
    /// Unique circle identifier (hash of initial member public keys)
    pub id: [u8; 32],

    /// Circle name (e.g., "Legal Team - Smith & Associates")
    pub name: String,

    /// Member public keys (ed25519)
    pub members: Vec<ed25519_dalek::PublicKey>,

    /// Threshold: minimum members needed to decrypt
    pub threshold: usize,

    /// Creation timestamp
    pub created_at: u64,

    /// Current key version (increments on member removal)
    pub key_version: u32,
}

/**
 * Key share for circle member
 *
 * DESIGN DECISION: Store shares encrypted in OS keychain
 * WHY: Platform-native protection (Windows Credential Manager, macOS Keychain, Linux Secret Service)
 */
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct KeyShare {
    /// Circle this share belongs to
    pub circle_id: [u8; 32],

    /// Key version (must match circle.key_version)
    pub key_version: u32,

    /// Shamir share (x, y) coordinates
    pub share: Share,

    /// Share index (1 to N)
    pub index: usize,
}
```

### Circle Initialization

```rust
/**
 * Create new circle of trust
 *
 * DESIGN DECISION: Leader generates key + shares, distributes via MCP
 * WHY: Simple initialization, leader doesn't keep privileged access
 *
 * REASONING CHAIN:
 * 1. Generate random AES-256 key (32 bytes from CSPRNG)
 * 2. Split key using Shamir(K=3, N=5)
 * 3. Encrypt each share with recipient's public key (X25519)
 * 4. Send shares via MCP to members
 * 5. Zero out original key in memory (only shares remain)
 *
 * EDGE CASE: Leader's device compromised after creation → can't decrypt alone (needs K-1 others)
 */
pub async fn create_circle(
    name: String,
    members: Vec<ed25519_dalek::PublicKey>,
    threshold: usize,
) -> Result<Circle, CircleError> {
    // Validate: threshold <= members.len()
    if threshold > members.len() {
        return Err(CircleError::InvalidThreshold);
    }

    // 1. Generate random AES-256 key
    let mut key_bytes = [0u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut key_bytes);

    // 2. Split key using Shamir
    let shares = Shamir::split_secret(
        threshold,
        members.len(),
        &key_bytes,
    )?;

    // 3. Create circle metadata
    let circle_id = sha256(&members.concat()); // Hash of member list
    let circle = Circle {
        id: circle_id,
        name,
        members: members.clone(),
        threshold,
        created_at: unix_timestamp(),
        key_version: 1,
    };

    // 4. Encrypt and distribute shares to members
    for (i, (member_pubkey, share)) in members.iter().zip(shares).enumerate() {
        let key_share = KeyShare {
            circle_id,
            key_version: 1,
            share,
            index: i + 1,
        };

        // Encrypt share with member's public key (X25519 ECDH)
        let encrypted_share = encrypt_for_recipient(member_pubkey, &key_share)?;

        // Send via MCP
        mcp_send(member_pubkey, encrypted_share).await?;
    }

    // 5. Zero out original key (security hygiene)
    key_bytes.zeroize();

    Ok(circle)
}
```

### Pattern Encryption

```rust
/**
 * Encrypt pattern for circle
 *
 * DESIGN DECISION: AES-256-GCM for authenticated encryption
 * WHY: Fast (hardware acceleration), authenticated (prevents tampering), standard (NIST approved)
 *
 * REASONING CHAIN:
 * 1. Retrieve AES key from shares (requires K circle members)
 * 2. Generate random nonce (96 bits, unique per encryption)
 * 3. Encrypt pattern with AES-256-GCM
 * 4. Include circle_id + key_version in metadata
 * 5. Store encrypted blob in DHT (Pattern-DHT-001)
 *
 * PATTERN: Uses Pattern-DHT-001 for storage
 */
pub async fn encrypt_pattern(
    circle: &Circle,
    pattern_content: &[u8],
) -> Result<EncryptedPattern, CryptoError> {
    // 1. Collect K shares from circle members
    let shares = collect_shares(circle, circle.threshold).await?;

    // 2. Reconstruct AES key
    let key_bytes = Shamir::combine_shares(&shares)?;
    let key = Key::from_slice(&key_bytes);
    let cipher = Aes256Gcm::new(key);

    // 3. Generate random nonce
    let mut nonce_bytes = [0u8; 12];
    rand::rngs::OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    // 4. Encrypt
    let ciphertext = cipher.encrypt(nonce, pattern_content)
        .map_err(|_| CryptoError::EncryptionFailed)?;

    // 5. Create metadata
    let encrypted = EncryptedPattern {
        circle_id: circle.id,
        key_version: circle.key_version,
        nonce: nonce_bytes,
        ciphertext,
        content_hash: sha256(pattern_content), // For integrity check
    };

    // 6. Zero out reconstructed key
    key_bytes.zeroize();

    Ok(encrypted)
}

/**
 * Decrypt pattern (requires K circle members)
 *
 * DESIGN DECISION: Threshold decryption (K-of-N)
 * WHY: Prevents single member from accessing all patterns (distributed trust)
 */
pub async fn decrypt_pattern(
    circle: &Circle,
    encrypted: &EncryptedPattern,
) -> Result<Vec<u8>, CryptoError> {
    // 1. Verify key version matches
    if encrypted.key_version != circle.key_version {
        return Err(CryptoError::KeyVersionMismatch);
    }

    // 2. Collect K shares
    let shares = collect_shares(circle, circle.threshold).await?;

    // 3. Reconstruct AES key
    let key_bytes = Shamir::combine_shares(&shares)?;
    let key = Key::from_slice(&key_bytes);
    let cipher = Aes256Gcm::new(key);

    // 4. Decrypt
    let nonce = Nonce::from_slice(&encrypted.nonce);
    let plaintext = cipher.decrypt(nonce, encrypted.ciphertext.as_ref())
        .map_err(|_| CryptoError::DecryptionFailed)?;

    // 5. Verify content hash
    if sha256(&plaintext) != encrypted.content_hash {
        return Err(CryptoError::IntegrityCheckFailed);
    }

    // 6. Zero out reconstructed key
    key_bytes.zeroize();

    Ok(plaintext)
}
```

### Share Collection (Interactive)

```rust
/**
 * Collect K shares from circle members via MCP
 *
 * DESIGN DECISION: Interactive share collection (members must be online)
 * WHY: Threshold property requires K members to collaborate
 *
 * REASONING CHAIN:
 * 1. Request shares from K online members via MCP
 * 2. Members decrypt share request (verify requester is in circle)
 * 3. Members send share via encrypted MCP message
 * 4. Requester collects K shares, reconstructs key
 * 5. Timeout if <K members respond (pattern unavailable)
 *
 * EDGE CASE: Only K-1 members online → pattern inaccessible (availability vs security tradeoff)
 */
async fn collect_shares(
    circle: &Circle,
    threshold: usize,
) -> Result<Vec<Share>, CollectionError> {
    // 1. Identify online members
    let online_members = mcp_find_online_members(&circle.members).await?;

    if online_members.len() < threshold {
        return Err(CollectionError::InsufficientMembers);
    }

    // 2. Request shares from K members
    let mut shares = Vec::new();
    for member in online_members.iter().take(threshold) {
        // Send share request via MCP
        let request = ShareRequest {
            circle_id: circle.id,
            key_version: circle.key_version,
            requester: get_local_pubkey(),
        };

        let response = mcp_request_share(member, request).await?;

        // 3. Verify response signature
        if response.verify(member) {
            shares.push(response.share);
        }
    }

    if shares.len() < threshold {
        return Err(CollectionError::ShareCollectionFailed);
    }

    Ok(shares)
}
```

---

## WHEN TO USE

**Use Shamir Secret Sharing when:**
- **Team collaboration:** Patterns shared within trusted group (legal team, engineering squad)
- **Threshold security:** Want K-of-N access control (e.g., 3 out of 5 partners must approve)
- **No central authority:** Can't trust single server with master key
- **Key loss tolerance:** If 1-2 members lose their share, others can still decrypt
- **Privacy from surveillance:** Want deniability (can't prove who accessed pattern)

**Do NOT use when:**
- **Public patterns:** Everyone should see pattern (use DHT without encryption)
- **Solo developer:** No team collaboration needed (use local encryption)
- **Real-time requirements:** Can't tolerate interactive share collection latency
- **Regulatory compliance:** Law requires escrowed keys (use key escrow, not Shamir)

---

## INTEGRATION WITH ÆTHERLIGHT

### Phase 3 Implementation (Intelligence Layer, Weeks 5-6)

**Deliverables:**
1. **Circle Management UI:**
   - Create circle (select members, set threshold)
   - Invite members (send shares via MCP)
   - View circle members (who has access)
   - Leave circle (revoke own share)

2. **Pattern Privacy Controls:**
   - Toggle: Public / Team-only / Private
   - If team-only: Select circle
   - Encrypt before DHT storage
   - Decrypt when fetching pattern

3. **Key Rotation (Member Removal):**
   - Generate new AES key
   - Split into new shares (excluding removed member)
   - Re-encrypt all circle patterns (background job)
   - Distribute new shares to remaining members

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Share distribution | <5s | time(create_circle) |
| Share collection | <2s | time(collect K shares) |
| Pattern encryption | <100ms | time(encrypt 1MB pattern) |
| Pattern decryption | <150ms | time(collect shares + decrypt) |
| Key rotation | <30s per pattern | background job throughput |

---

## EDGE CASES

### 1. **Member Device Lost (Share Compromised)**
**Problem:** Member's laptop stolen, share exposed.

**Solution:**
- **Threshold protects:** Attacker needs K shares (can't decrypt alone)
- **Immediate action:** Circle admin removes member (triggers key rotation)
- **Re-encryption:** All patterns re-encrypted with new key
- **Timeline:** <1 hour from report to full rotation

### 2. **Insufficient Online Members (K-1 Available)**
**Problem:** Need 3 members, only 2 online → pattern inaccessible.

**Solution:**
- **Graceful degradation:** Show "pattern unavailable" message
- **Retry with backoff:** Periodically check for K online members
- **Lower threshold option:** Allow admin to reduce K temporarily (emergency access)
- **Backup shares:** Circle can designate offline backup holder (cold storage)

### 3. **Malicious Member (Share Used Improperly)**
**Problem:** Member leaks share to outsider.

**Solution:**
- **Detection:** Monitor unusual decryption patterns (high volume, odd times)
- **Revocation:** Admin removes member, rotates key
- **Audit log:** Track which members participated in each decryption
- **Deniability tradeoff:** Audit log reduces privacy (configurable per circle)

### 4. **Circle Admin Leaves (No One Can Add Members)**
**Problem:** Admin was only one who knew how to generate new shares.

**Solution:**
- **Multi-admin model:** Allow multiple admins (threshold for admin operations)
- **Admin share:** Special share that allows generating new shares
- **Succession plan:** Circle designates successor admin on creation

### 5. **Key Version Mismatch (Member Has Old Share)**
**Problem:** Circle rotated key, member still has old share.

**Solution:**
- **Version checking:** Metadata includes key_version
- **Automatic update:** Member requests new share from admin
- **Backward compatibility:** Old patterns decryptable with old shares (versioned storage)

---

## RELATED PATTERNS

- **Pattern-DHT-001:** Content-Addressed Pattern Storage (encrypted patterns stored in DHT)
- **Pattern-MCP-001:** Neural Network Routing Architecture (share distribution protocol)
- **Pattern-CRYPTO-001:** Hybrid Encryption for Performance (AES + Shamir combination)
- **Pattern-AUDIT-001:** Decentralized Audit Logs (track circle access patterns - to be created)

---

## REFERENCES

**Academic:**
- Shamir, Adi (1979): "How to Share a Secret" (original paper, Communications of the ACM)
- Feldman, Paul (1987): "A Practical Scheme for Non-interactive Verifiable Secret Sharing"

**Production Implementations:**
- **vsss-rs:** Rust crate for Verifiable Secret Sharing (https://crates.io/crates/vsss-rs)
- **Hashicorp Vault:** Uses Shamir for unseal keys (5 key holders, need 3 to unseal)
- **Glacier Protocol:** Bitcoin cold storage with Shamir shares (https://glacierprotocol.org/)

**Security Analysis:**
- **Threshold:** K=3, N=5 recommended (balance security vs availability)
- **Information Theory:** Any K-1 shares reveal ZERO bits about secret (perfect secrecy)
- **Computational:** Reconstruction is O(K²) via Lagrange interpolation (negligible for K<100)

---

## FUTURE

### Phase 3 Enhancements
- **Proactive secret sharing:** Re-randomize shares periodically (prevents long-term compromise)
- **Hierarchical circles:** Parent circle can decrypt child circle patterns (org structure)
- **Time-locked encryption:** Pattern auto-decrypts after timestamp (legal holds)

### Post-Launch (DAO Governance Era)
- **On-chain verification:** Publish circle commitments to blockchain (transparency without revealing key)
- **ZK-proofs:** Prove membership in circle without revealing identity (privacy + auditability)
- **Cross-circle patterns:** Pattern accessible by multiple circles (union/intersection policies)

---

## METRICS TO TRACK

**During Development (Phase 3):**
- Share distribution success rate (target: >99%)
- Share collection latency (target: <2s for K=3)
- Key rotation throughput (target: >10 patterns/sec)

**Post-Deployment:**
- Active circles (number of teams using feature)
- Average circle size (N members)
- Average threshold (K members)
- Key rotation frequency (security health metric)
- Share loss incidents (backup effectiveness)

---

## PRIVACY CONSIDERATIONS

### Threat Model

**Protected Against:**
- **DHT node operators:** Can't decrypt patterns (ciphertext only)
- **Single compromised member:** Needs K members to decrypt
- **Network eavesdroppers:** MCP encrypted, shares never in plaintext
- **Government subpoena:** No central key server to compel

**NOT Protected Against:**
- **K malicious members colluding:** Can reconstruct key and leak patterns
- **All members compromised:** Full key recovery (inherent to threshold scheme)
- **Legal team dissolved:** If <K members remain, patterns lost forever

### Privacy vs Availability Tradeoff

**Lower threshold (K=2):**
- ✅ Higher availability (only need 2 members online)
- ❌ Lower security (2 compromised devices = breach)

**Higher threshold (K=4):**
- ✅ Higher security (4 devices must be compromised)
- ❌ Lower availability (need 4 members online)

**Recommended:** K = ceil(N/2) + 1 (e.g., 3 out of 5, 4 out of 7)

---

**PATTERN CONFIDENCE:** High (Shamir proven since 1979, used in production systems)
**IMPLEMENTATION COMPLEXITY:** Medium (libraries exist, key management requires care)
**RISK LEVEL:** Low (well-understood cryptography, graceful degradation)

**STATUS:** Ready for Phase 3 Implementation

---

**LAST UPDATED:** 2025-10-04
**NEXT REVIEW:** After Phase 1-2 completion (Week 4)
