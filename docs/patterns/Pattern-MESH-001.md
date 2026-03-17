# Pattern-MESH-001: Offline Mesh Networking

**CREATED:** 2025-10-05
**CATEGORY:** Distributed Systems / Networking
**LANGUAGE:** Rust
**QUALITY SCORE:** 0.80
**APPLICABILITY:** General use
**STATUS:** Active
**RELATED:** PATTERN-STORAGE-001, PATTERN-DHT-001, PATTERN-TRUST-001, PATTERN-BUSINESS-001

---




## Context

Users need to sync encrypted data across their devices without requiring internet connectivity, especially in scenarios where:
- Internet is unavailable (travel, wilderness, network outage)
- Privacy is critical (no data should touch cloud servers)
- Battery efficiency matters (mobile devices need low-power sync)
- Device capacity varies (desktop = high capacity, phone = low capacity)

**Problem:**
- Traditional sync requires cloud infrastructure (Dropbox, iCloud)
- Cloud sync = Privacy risk (server can decrypt data)
- Offline scenarios not supported (airplane mode, remote locations)
- Battery drain from continuous syncing (mobile problem)
- No device-aware allocation (desktop and phone treated same)

**Requirements:**
- Zero-config discovery (no manual IP addresses, no setup)
- Cross-platform (Windows, macOS, Linux, iOS, Android)
- Battery-efficient (mobile devices, low power consumption)
- Flexible storage allocation (100MB to 100GB+, user configurable)
- Device-aware (desktop = primary storage, phone = secondary)
- Works offline (no internet, no cloud)

---

## Design Decision

**DECISION:** Multi-protocol mesh networking with device-aware storage allocation

**WHY:**
1. **mDNS/Bonjour:** Zero-config local network discovery (easiest, works on all platforms)
2. **Bluetooth Mesh:** Battery-efficient mobile sync (BLE 5.0, low power)
3. **Wi-Fi Direct:** High-speed ad-hoc networking (no router required)
4. **Device-aware allocation:** Desktop = primary storage (always-on), phone = secondary (battery-efficient)
5. **User-configurable:** 100MB to 100GB+ per device (storage is cheap)

---

## Reasoning Chain

### 1. Protocol Selection: mDNS/Bonjour (Recommended)

**Purpose:** Zero-config service discovery on local networks

**How It Works:**
1. Desktop advertises "_aetherlight._tcp.local" service
2. Laptop queries mDNS for "_aetherlight._tcp" services
3. Desktop responds with IP address + port (automatic)
4. Laptop connects via TCP (ws://192.168.1.100:43216)
5. Encrypted shards synced via WebSocket

**Advantages:**
- ✅ Zero-config (no IP addresses, no setup)
- ✅ Cross-platform (macOS Bonjour, Linux Avahi, Windows Bonjour SDK)
- ✅ Fast (local network speeds: 100Mbps-1Gbps)
- ✅ Reliable (mDNS is mature, battle-tested)

**Limitations:**
- ❌ Local network only (requires Wi-Fi/Ethernet)
- ❌ No internet sync (Layer 3 DHT handles this)

**Implementation:**
```rust
use mdns::{Record, RecordKind};
use tokio::net::{TcpListener, TcpStream};

pub struct MeshNode {
    node_id: String,
    storage_allocated_bytes: u64,  // User-configurable allocation
    device_type: DeviceType,       // Desktop, Laptop, Mobile
}

#[derive(Debug, Clone)]
pub enum DeviceType {
    Desktop {
        always_on: bool,           // True if plugged in 24/7
        allocation: u64,           // 1GB-100GB+ (user configurable)
    },
    Laptop {
        battery_status: BatteryStatus,
        allocation: u64,           // 500MB-50GB (user configurable)
    },
    Mobile {
        battery_status: BatteryStatus,
        wifi_only: bool,           // True = no cellular data
        allocation: u64,           // 50MB-10GB (user configurable)
    },
}

impl MeshNode {
    pub async fn advertise_mdns(&self) -> Result<()> {
        // 1. Create mDNS responder
        let responder = mdns::Responder::new()?;

        // 2. Advertise service with device metadata
        let service = responder.register(
            "_aetherlight._tcp".to_owned(),
            self.node_id.clone(),
            43216,  // TCP port for shard sync
            &[
                format!("node_id={}", self.node_id),
                format!("device_type={}", self.device_type_str()),
                format!("storage_bytes={}", self.storage_allocated_bytes),
                format!("version=1.0"),
            ],
        );

        // 3. Keep responder alive (background task)
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(Duration::from_secs(60)).await;
                // mDNS responder handles keep-alive automatically
            }
        });

        Ok(())
    }

    pub async fn discover_peers(&self) -> Result<Vec<PeerNode>> {
        // 1. Query for ÆtherLight services
        let mdns = mdns::discover::all("_aetherlight._tcp", Duration::from_secs(5))?;

        let mut peers = Vec::new();
        for response in mdns {
            // 2. Extract IP address from response
            if let Some(addr) = response.records()
                .filter_map(self.to_ip_addr)
                .next()
            {
                // 3. Parse TXT records for metadata
                let device_type = self.parse_device_type(&response);
                let storage_bytes = self.parse_storage_bytes(&response);

                peers.push(PeerNode {
                    node_id: response.hostname.clone(),
                    local_ip: addr,
                    tcp_port: response.port,
                    device_type,
                    storage_allocated_bytes: storage_bytes,
                });
            }
        }

        Ok(peers)
    }

    pub async fn sync_to_peer(&self, peer: &PeerNode, shard_id: &str) -> Result<()> {
        // 1. Check if sync is appropriate (device-aware logic)
        if !self.should_sync_to_peer(peer).await? {
            return Ok(()); // Skip sync (battery low, cellular only, etc.)
        }

        // 2. Connect to peer via TCP
        let mut stream = TcpStream::connect((peer.local_ip, peer.tcp_port)).await?;

        // 3. Send shard ID + encrypted shard
        let shard = self.local_storage.retrieve_file(shard_id)?;
        stream.write_all(shard_id.as_bytes()).await?;
        stream.write_all(&(shard.len() as u64).to_le_bytes()).await?;
        stream.write_all(&shard).await?;

        Ok(())
    }

    async fn should_sync_to_peer(&self, peer: &PeerNode) -> Result<bool> {
        // Device-aware sync logic
        match &self.device_type {
            DeviceType::Desktop { always_on, .. } => {
                // Desktop: Always sync (unless peer is full)
                Ok(peer.has_available_storage())
            }
            DeviceType::Laptop { battery_status, .. } => {
                // Laptop: Sync if plugged in OR battery >50%
                Ok(battery_status.is_plugged_in() || battery_status.percent() > 50)
            }
            DeviceType::Mobile { battery_status, wifi_only, .. } => {
                // Mobile: Wi-Fi only, plugged in OR battery >70%
                let wifi_available = self.is_wifi_connected().await?;
                let battery_ok = battery_status.is_plugged_in() || battery_status.percent() > 70;

                Ok(wifi_available && (*wifi_only || battery_ok))
            }
        }
    }
}
```

**Key Features:**
- **Zero-config:** mDNS handles discovery (no manual IP addresses)
- **Device-aware:** Desktop syncs aggressively, mobile syncs conservatively
- **Battery-efficient:** Mobile only syncs on Wi-Fi + good battery
- **Flexible allocation:** User configures storage per device (100MB to 100GB+)

---

### 2. Protocol Selection: Bluetooth Mesh (Mobile-Friendly)

**Purpose:** Low-power sync for mobile devices without Wi-Fi

**How It Works:**
1. Phone advertises ÆtherLight BLE service (UUID)
2. Nearby phone scans for BLE services
3. Connection established via BLE GATT protocol
4. Encrypted shards transferred in 512-byte chunks (GATT limit)
5. Multi-hop routing (phone → phone → phone)

**Advantages:**
- ✅ Battery-efficient (BLE 5.0 = 10× less power than classic Bluetooth)
- ✅ Range (30-100m vs 10m for classic Bluetooth)
- ✅ Mobile-first (works on phones without Wi-Fi)
- ✅ Mesh networking (multi-hop, extends range)

**Limitations:**
- ❌ Low throughput (1-2 Mbps vs 100+ Mbps for Wi-Fi)
- ❌ Packet size limit (512 bytes per GATT write, requires chunking)
- ❌ iOS restrictions (background BLE limited, requires app foreground)

**Implementation:**
```rust
use btleplug::{api::*, platform::Manager};
use uuid::Uuid;

const AETHERLIGHT_SERVICE_UUID: Uuid =
    Uuid::parse_str("6E400001-B5A3-F393-E0A9-E50E24DCCA9E").unwrap();
const AETHERLIGHT_SHARD_CHAR_UUID: Uuid =
    Uuid::parse_str("6E400002-B5A3-F393-E0A9-E50E24DCCA9E").unwrap();

pub struct BluetoothMesh {
    manager: Manager,
    node_id: String,
    device_type: DeviceType,
}

impl BluetoothMesh {
    pub async fn advertise_ble(&self) -> Result<()> {
        // 1. Get BLE adapter
        let adapter = self.manager.adapters().await?.into_iter().next().unwrap();

        // 2. Start advertising ÆtherLight service
        let advertisement = Advertisement {
            service_uuids: vec![AETHERLIGHT_SERVICE_UUID],
            manufacturer_data: self.encode_device_metadata(),
            ..Default::default()
        };

        adapter.start_advertising(&advertisement).await?;

        Ok(())
    }

    pub async fn discover_peers(&self) -> Result<Vec<Peripheral>> {
        // 1. Start BLE scan
        let adapter = self.manager.adapters().await?.into_iter().next().unwrap();
        adapter.start_scan(ScanFilter::default()).await?;

        // 2. Scan for 5 seconds
        tokio::time::sleep(Duration::from_secs(5)).await;

        // 3. Filter for ÆtherLight nodes
        let peripherals = adapter.peripherals().await?;
        let aetherlight_nodes = peripherals.into_iter()
            .filter(|p| {
                p.properties()
                    .unwrap()
                    .services
                    .contains(&AETHERLIGHT_SERVICE_UUID)
            })
            .collect();

        Ok(aetherlight_nodes)
    }

    pub async fn sync_via_ble(&self, peer: &Peripheral, shard: &[u8]) -> Result<()> {
        // 1. Check battery status (mobile optimization)
        if let DeviceType::Mobile { battery_status, .. } = &self.device_type {
            if !battery_status.is_plugged_in() && battery_status.percent() < 70 {
                return Ok(()); // Skip sync to preserve battery
            }
        }

        // 2. Connect to peer
        peer.connect().await?;
        peer.discover_services().await?;

        // 3. Find shard characteristic
        let characteristic = peer.characteristics()
            .iter()
            .find(|c| c.uuid == AETHERLIGHT_SHARD_CHAR_UUID)
            .ok_or_else(|| anyhow!("Shard characteristic not found"))?;

        // 4. Chunk shard into 512-byte packets (GATT limit)
        for (i, chunk) in shard.chunks(512).enumerate() {
            // 5. Write chunk with retry logic
            let mut retries = 3;
            while retries > 0 {
                match peer.write(characteristic, chunk, WriteType::WithResponse).await {
                    Ok(_) => break,
                    Err(e) if retries > 1 => {
                        retries -= 1;
                        tokio::time::sleep(Duration::from_millis(100)).await;
                    }
                    Err(e) => return Err(e.into()),
                }
            }

            // 6. Progress update (for large shards)
            if i % 10 == 0 {
                log::debug!("BLE sync progress: {}/{} chunks", i, shard.chunks(512).count());
            }
        }

        // 7. Disconnect
        peer.disconnect().await?;

        Ok(())
    }

    fn encode_device_metadata(&self) -> Vec<u8> {
        // Encode device type, storage allocation, battery status
        let mut data = Vec::new();
        data.push(self.device_type_byte());
        data.extend_from_slice(&self.storage_allocated_bytes().to_le_bytes());
        data.extend_from_slice(&self.battery_percent().to_le_bytes());
        data
    }
}
```

**Key Features:**
- **Battery-efficient:** BLE 5.0 (10× less power than classic Bluetooth)
- **Mobile-optimized:** Only syncs when plugged in OR battery >70%
- **Chunked transfer:** 512-byte GATT packets (reliable)
- **Retry logic:** Handles intermittent connections

**Use Cases:**
- **Mobile-to-mobile:** Phone → phone sync without Wi-Fi
- **Emergency:** Internet down, sync via Bluetooth
- **Travel:** Airplane mode, sync between family devices

---

### 3. Protocol Selection: Wi-Fi Direct (High-Speed Ad-Hoc)

**Purpose:** High-speed peer-to-peer networking without router

**How It Works:**
1. Desktop creates Wi-Fi Direct group (becomes "group owner")
2. Laptop discovers Wi-Fi Direct groups (scans for peers)
3. Laptop joins group (negotiates connection)
4. TCP connection established (ad-hoc network)
5. High-speed shard transfer (100-300 Mbps)

**Advantages:**
- ✅ High throughput (100-300 Mbps, Wi-Fi speeds)
- ✅ No router required (peer-to-peer ad-hoc)
- ✅ Range (100-200m, Wi-Fi range)
- ✅ Simultaneous connections (up to 8 devices per group)

**Limitations:**
- ❌ Platform support (Android/Linux only, iOS doesn't support Wi-Fi Direct)
- ❌ Battery drain (higher power than BLE, lower than standard Wi-Fi)
- ❌ Complexity (group owner negotiation, IP assignment)

**Implementation:**
```rust
use wifi_direct::{WifiDirectManager, GroupOwner, Peer};

pub struct WifiDirectMesh {
    manager: WifiDirectManager,
    group: Option<GroupOwner>,
    device_type: DeviceType,
}

impl WifiDirectMesh {
    pub async fn create_group(&mut self) -> Result<()> {
        // 1. Create Wi-Fi Direct group (become group owner)
        self.group = Some(self.manager.create_group().await?);

        // 2. Start TCP listener (accept shard connections)
        let group_ip = self.group.as_ref().unwrap().ip_address();
        let listener = TcpListener::bind((group_ip, 43217)).await?;

        // 3. Accept connections in background
        tokio::spawn(async move {
            loop {
                if let Ok((stream, addr)) = listener.accept().await {
                    tokio::spawn(async move {
                        self.handle_incoming_shard(stream).await;
                    });
                }
            }
        });

        Ok(())
    }

    pub async fn discover_groups(&self) -> Result<Vec<Peer>> {
        // 1. Discover Wi-Fi Direct groups
        self.manager.discover_peers(Duration::from_secs(10)).await
    }

    pub async fn join_group(&mut self, peer: &Peer) -> Result<()> {
        // 1. Check battery status (laptop/mobile optimization)
        if !self.should_use_wifi_direct().await? {
            return Ok(()); // Skip Wi-Fi Direct (battery too low)
        }

        // 2. Join existing Wi-Fi Direct group
        self.manager.connect(peer).await?;

        Ok(())
    }

    pub async fn sync_via_wifi_direct(&self, peer: &Peer, shard: &[u8]) -> Result<()> {
        // 1. Connect to group owner via TCP
        let group_owner_ip = peer.ip_address();
        let mut stream = TcpStream::connect((group_owner_ip, 43217)).await?;

        // 2. Send shard (high-speed transfer)
        stream.write_all(shard).await?;

        Ok(())
    }

    async fn should_use_wifi_direct(&self) -> Result<bool> {
        match &self.device_type {
            DeviceType::Desktop { .. } => Ok(true),  // Always OK
            DeviceType::Laptop { battery_status, .. } => {
                // Laptop: Only if plugged in OR battery >50%
                Ok(battery_status.is_plugged_in() || battery_status.percent() > 50)
            }
            DeviceType::Mobile { battery_status, .. } => {
                // Mobile: Only if plugged in (Wi-Fi Direct drains battery)
                Ok(battery_status.is_plugged_in())
            }
        }
    }
}
```

**Key Features:**
- **High-speed:** 100-300 Mbps (Wi-Fi speeds)
- **Battery-aware:** Only used when device conditions allow
- **Ad-hoc:** No router required (peer-to-peer)
- **Multi-device:** Up to 8 devices per group

**Use Cases:**
- **Android devices:** High-speed sync between Android phones/tablets
- **Linux laptops:** Ad-hoc networking without router
- **Emergency:** No Wi-Fi router, need high-speed transfer

---

## Device-Aware Storage Allocation

**DESIGN DECISION:** Flexible, user-configurable storage allocation with device-aware defaults
**WHY:** Storage is cheap (512GB phones, 1-4TB desktops), users should control allocation

### Allocation Profiles

```rust
pub struct StorageAllocation {
    total_capacity_bytes: u64,        // Total device storage
    user_allocated_bytes: u64,        // User-configured allocation
    used_bytes: u64,                  // Current usage
    device_type: DeviceType,
}

impl StorageAllocation {
    pub fn default_allocation(device_type: DeviceType) -> u64 {
        match device_type {
            DeviceType::Desktop { .. } => {
                // Desktop default: 1GB (can go up to 100GB+)
                1_000_000_000  // 1GB
            }
            DeviceType::Laptop { .. } => {
                // Laptop default: 500MB (can go up to 50GB)
                500_000_000  // 500MB
            }
            DeviceType::Mobile { .. } => {
                // Mobile default: 100MB (can go up to 10GB)
                100_000_000  // 100MB
            }
        }
    }

    pub fn min_allocation(device_type: DeviceType) -> u64 {
        match device_type {
            DeviceType::Desktop { .. } => 100_000_000,  // 100MB min
            DeviceType::Laptop { .. } => 100_000_000,   // 100MB min
            DeviceType::Mobile { .. } => 50_000_000,    // 50MB min
        }
    }

    pub fn max_allocation(device_type: DeviceType, total_capacity: u64) -> u64 {
        match device_type {
            DeviceType::Desktop { .. } => {
                // Desktop max: 10% of total capacity OR 100GB, whichever is smaller
                (total_capacity / 10).min(100_000_000_000)
            }
            DeviceType::Laptop { .. } => {
                // Laptop max: 5% of total capacity OR 50GB
                (total_capacity / 20).min(50_000_000_000)
            }
            DeviceType::Mobile { .. } => {
                // Mobile max: 2% of total capacity OR 10GB
                (total_capacity / 50).min(10_000_000_000)
            }
        }
    }

    pub fn available_bytes(&self) -> u64 {
        self.user_allocated_bytes.saturating_sub(self.used_bytes)
    }

    pub fn utilization_percent(&self) -> f32 {
        (self.used_bytes as f32 / self.user_allocated_bytes as f32) * 100.0
    }
}
```

### User Interface (Settings)

```
Storage Allocation Settings:

Device: Desktop (Windows)
Total Capacity: 2TB (1.8TB available)

Allocated Storage: [=========>_____] 10GB / 200GB max

[Slider: 100MB ━━━━━●━━━━━━━ 200GB]

Recommended: 10GB (based on your usage)
Current Usage: 8.2GB (82% full)

⚠️ You're using 82% of allocated storage.
Consider allocating more or inviting trusted nodes.

[Increase Allocation]  [Invite Trusted Nodes]

---

Storage Distribution:
- Desktop (this device): 8.2GB (primary storage)
- Laptop (work-laptop): 2.1GB (secondary)
- Phone (iPhone): 150MB (critical data only)

Total Network Storage: 10.45GB across 3 devices
```

---

## Intelligent Shard Distribution

**DESIGN DECISION:** Distribute shards based on device capacity, availability, and battery
**WHY:** Desktop = always-on, high capacity → Primary storage. Phone = battery-sensitive → Secondary storage

### Distribution Algorithm

```rust
pub struct ShardDistributor {
    nodes: Vec<MeshNode>,
}

impl ShardDistributor {
    pub fn distribute_shards(
        &self,
        shard_count: usize,
        shard_size_bytes: u64,
    ) -> Result<HashMap<String, Vec<ShardId>>> {
        // 1. Score each node (capacity, availability, battery)
        let scored_nodes: Vec<(MeshNode, f32)> = self.nodes.iter()
            .map(|node| (node.clone(), self.calculate_node_score(node)))
            .collect();

        // 2. Sort by score (highest first)
        let mut sorted = scored_nodes;
        sorted.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        // 3. Distribute shards proportionally to scores
        let total_score: f32 = sorted.iter().map(|(_, score)| score).sum();
        let mut distribution = HashMap::new();

        for (node, score) in sorted {
            // Calculate shard allocation for this node
            let shard_ratio = score / total_score;
            let shards_for_node = (shard_count as f32 * shard_ratio).ceil() as usize;

            // Check if node has capacity
            let required_space = shards_for_node as u64 * shard_size_bytes;
            if node.available_storage() >= required_space {
                distribution.insert(node.node_id.clone(), self.allocate_shards(shards_for_node));
            }
        }

        Ok(distribution)
    }

    fn calculate_node_score(&self, node: &MeshNode) -> f32 {
        let mut score = 0.0;

        // Factor 1: Storage capacity (0-40 points)
        score += self.capacity_score(node);

        // Factor 2: Device availability (0-30 points)
        score += self.availability_score(node);

        // Factor 3: Battery status (0-20 points)
        score += self.battery_score(node);

        // Factor 4: Network connectivity (0-10 points)
        score += self.network_score(node);

        score
    }

    fn capacity_score(&self, node: &MeshNode) -> f32 {
        // Desktop with 10GB = 40 points
        // Laptop with 5GB = 30 points
        // Phone with 100MB = 5 points
        let capacity_gb = node.storage_allocated_bytes as f32 / 1_000_000_000.0;
        (capacity_gb / 10.0 * 40.0).min(40.0)
    }

    fn availability_score(&self, node: &MeshNode) -> f32 {
        match &node.device_type {
            DeviceType::Desktop { always_on, .. } => {
                if *always_on { 30.0 } else { 20.0 }
            }
            DeviceType::Laptop { .. } => 15.0,
            DeviceType::Mobile { .. } => 5.0,
        }
    }

    fn battery_score(&self, node: &MeshNode) -> f32 {
        match &node.device_type {
            DeviceType::Desktop { .. } => 20.0,  // Always plugged in
            DeviceType::Laptop { battery_status, .. } => {
                if battery_status.is_plugged_in() {
                    20.0
                } else if battery_status.percent() > 50 {
                    10.0
                } else {
                    0.0  // Low battery = don't allocate shards
                }
            }
            DeviceType::Mobile { battery_status, .. } => {
                if battery_status.is_plugged_in() {
                    15.0
                } else if battery_status.percent() > 70 {
                    5.0
                } else {
                    0.0  // Low battery = don't allocate shards
                }
            }
        }
    }

    fn network_score(&self, node: &MeshNode) -> f32 {
        match &node.device_type {
            DeviceType::Desktop { .. } => 10.0,  // Wired/Wi-Fi
            DeviceType::Laptop { .. } => 8.0,    // Wi-Fi
            DeviceType::Mobile { wifi_only, .. } => {
                if *wifi_only && self.is_wifi_connected() {
                    6.0
                } else if !*wifi_only {
                    4.0
                } else {
                    0.0  // No Wi-Fi, cellular only
                }
            }
        }
    }
}
```

### Example Distribution

**Scenario:** User has 3 devices, needs to distribute 15 shards (100MB each)

```
Device Scoring:
1. Desktop (10GB allocated, always-on, plugged in, wired)
   - Capacity: 40 points
   - Availability: 30 points
   - Battery: 20 points
   - Network: 10 points
   - Total: 100 points (50% of total)

2. Laptop (5GB allocated, intermittent, battery 60%, Wi-Fi)
   - Capacity: 30 points
   - Availability: 15 points
   - Battery: 10 points
   - Network: 8 points
   - Total: 63 points (31.5% of total)

3. Phone (100MB allocated, mobile, battery 80%, Wi-Fi only)
   - Capacity: 5 points
   - Availability: 5 points
   - Battery: 5 points
   - Network: 6 points
   - Total: 21 points (10.5% of total)

Distribution:
- Desktop: 50% → 8 shards (800MB)
- Laptop: 31.5% → 5 shards (500MB)
- Phone: 10.5% → 2 shards (200MB)
Total: 15 shards distributed
```

**Result:** Desktop hosts most data (primary storage), phone hosts critical data only (secondary)

---

## Battery Optimization Strategies

**DESIGN DECISION:** Adaptive sync based on battery status, network type, and device usage
**WHY:** Mobile devices need battery-efficient sync to avoid user frustration

### Optimization Techniques

#### 1. Battery-Aware Sync Scheduling

```rust
pub struct SyncScheduler {
    device_type: DeviceType,
    last_sync: Instant,
}

impl SyncScheduler {
    pub fn should_sync_now(&self) -> bool {
        match &self.device_type {
            DeviceType::Desktop { .. } => {
                // Desktop: Always sync (plugged in 24/7)
                true
            }
            DeviceType::Laptop { battery_status, .. } => {
                // Laptop: Sync if plugged in OR battery >50%
                battery_status.is_plugged_in() || battery_status.percent() > 50
            }
            DeviceType::Mobile { battery_status, wifi_only, .. } => {
                // Mobile: Complex logic (Wi-Fi, battery, frequency)
                let wifi_ok = !*wifi_only || self.is_wifi_connected();
                let battery_ok = battery_status.is_plugged_in() || battery_status.percent() > 70;
                let frequency_ok = self.last_sync.elapsed() > Duration::from_secs(300); // 5 min minimum

                wifi_ok && battery_ok && frequency_ok
            }
        }
    }

    pub fn sync_frequency(&self) -> Duration {
        match &self.device_type {
            DeviceType::Desktop { .. } => Duration::from_secs(60),      // 1 minute
            DeviceType::Laptop { battery_status, .. } => {
                if battery_status.is_plugged_in() {
                    Duration::from_secs(300)    // 5 minutes (plugged in)
                } else {
                    Duration::from_secs(1800)   // 30 minutes (battery)
                }
            }
            DeviceType::Mobile { battery_status, .. } => {
                if battery_status.is_plugged_in() {
                    Duration::from_secs(600)    // 10 minutes (plugged in)
                } else if battery_status.percent() > 70 {
                    Duration::from_secs(3600)   // 1 hour (good battery)
                } else {
                    Duration::from_secs(7200)   // 2 hours (low battery)
                }
            }
        }
    }
}
```

#### 2. Wi-Fi-Only Sync (Mobile)

```rust
pub async fn sync_mobile_with_wifi_check(&self) -> Result<()> {
    // 1. Check if Wi-Fi is connected
    if !self.is_wifi_connected().await? {
        log::info!("Mobile: Skipping sync (no Wi-Fi, cellular only)");
        return Ok(());
    }

    // 2. Check battery status
    let battery = self.battery_status().await?;
    if !battery.is_plugged_in() && battery.percent() < 70 {
        log::info!("Mobile: Skipping sync (battery < 70%, not plugged in)");
        return Ok(());
    }

    // 3. Proceed with sync
    self.sync_shards().await?;

    Ok(())
}
```

#### 3. Background Sync Limits (iOS/Android)

```rust
#[cfg(target_os = "ios")]
pub async fn register_background_sync(&self) -> Result<()> {
    // iOS: Background fetch (15-minute minimum interval)
    UIApplication::setMinimumBackgroundFetchInterval(900.0); // 15 minutes

    // Register background task
    BGTaskScheduler::register("com.aetherlight.sync", |task| {
        self.perform_background_sync(task).await;
    });

    Ok(())
}

#[cfg(target_os = "android")]
pub async fn register_background_sync(&self) -> Result<()> {
    // Android: WorkManager (15-minute minimum interval)
    let sync_request = PeriodicWorkRequest::Builder::new(
        SyncWorker::class,
        Duration::from_secs(900),  // 15 minutes
    )
    .setRequiredNetworkType(NetworkType::WIFI)  // Wi-Fi only
    .setRequiresBatteryNotLow(true)             // Skip if battery low
    .build();

    WorkManager::enqueue(sync_request);

    Ok(())
}
```

#### 4. Adaptive Sync (Usage Patterns)

```rust
pub struct AdaptiveSyncScheduler {
    usage_history: Vec<(DateTime<Utc>, SyncDuration)>,
}

impl AdaptiveSyncScheduler {
    pub fn predict_next_sync_window(&self) -> (DateTime<Utc>, DateTime<Utc>) {
        // 1. Analyze usage patterns (when does user typically use device?)
        let peak_hours = self.analyze_peak_usage();

        // 2. Find next peak window (user likely to be plugged in, on Wi-Fi)
        let next_peak = self.next_peak_hour(peak_hours);

        // 3. Return sync window
        (next_peak, next_peak + chrono::Duration::hours(1))
    }

    fn analyze_peak_usage(&self) -> Vec<u8> {
        // Analyze historical usage, return hours (0-23) when user is most active
        let mut hour_counts = [0u32; 24];

        for (timestamp, _) in &self.usage_history {
            hour_counts[timestamp.hour() as usize] += 1;
        }

        // Return top 3 peak hours
        let mut peaks: Vec<(usize, u32)> = hour_counts.iter()
            .enumerate()
            .map(|(hour, &count)| (hour, count))
            .collect();
        peaks.sort_by_key(|(_, count)| std::cmp::Reverse(*count));

        peaks.into_iter().take(3).map(|(hour, _)| hour as u8).collect()
    }
}
```

---

## Performance Characteristics

### Latency by Protocol

| Protocol | Latency (p50) | Latency (p95) | Throughput | Range |
|----------|---------------|---------------|------------|-------|
| mDNS + TCP | 10-50ms | 50-200ms | 100Mbps-1Gbps | 100m (Wi-Fi) |
| Bluetooth Mesh | 100-500ms | 500-2000ms | 1-2 Mbps | 30-100m |
| Wi-Fi Direct | 20-100ms | 100-300ms | 100-300 Mbps | 100-200m |

### Battery Impact (Mobile)

| Sync Frequency | Battery Drain (per hour) | Acceptable For |
|----------------|--------------------------|----------------|
| Real-time (Desktop-like) | 15-20% | Plugged in only |
| Every 5 minutes | 5-8% | Plugged in, Wi-Fi only |
| Every 15 minutes | 2-3% | Good battery (>70%), Wi-Fi |
| Every 1 hour | 0.5-1% | Normal use, background |

### Storage Allocation Recommendations

| Device Type | Minimum | Recommended | Maximum | Typical Usage |
|-------------|---------|-------------|---------|---------------|
| Desktop | 100MB | 1GB | 100GB+ | Primary storage, always-on |
| Laptop | 100MB | 500MB | 50GB | Secondary storage, intermittent |
| Phone | 50MB | 100MB | 10GB | Tertiary storage, critical data only |

---

## Implementation Checklist

### Phase 2: Desktop App (Current)

- [x] mDNS discovery (Bonjour/Avahi)
- [x] TCP-based shard sync
- [ ] Device-aware allocation (user-configurable)
- [ ] Battery status detection (desktop = always plugged in)
- [ ] Storage quota UI (settings page)

### Phase 3: Mobile Support (Next)

- [ ] Bluetooth Mesh (BLE 5.0)
- [ ] Wi-Fi-only sync enforcement
- [ ] Battery-aware sync scheduling
- [ ] Background sync limits (iOS/Android)
- [ ] Adaptive sync (usage patterns)

### Phase 4: Advanced Features (Future)

- [ ] Wi-Fi Direct (Android/Linux)
- [ ] Multi-hop routing (extend range)
- [ ] Intelligent shard distribution (capacity + battery + availability)
- [ ] Network health dashboard (node status, storage usage)

---

## Testing Strategy

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_allocation() {
        let desktop = DeviceType::Desktop { always_on: true, allocation: 0 };
        assert_eq!(StorageAllocation::default_allocation(desktop), 1_000_000_000);

        let mobile = DeviceType::Mobile {
            battery_status: BatteryStatus::new(80, false),
            wifi_only: true,
            allocation: 0,
        };
        assert_eq!(StorageAllocation::default_allocation(mobile), 100_000_000);
    }

    #[test]
    fn test_shard_distribution() {
        let nodes = vec![
            create_desktop_node(10_000_000_000, true),   // 10GB, always-on
            create_laptop_node(5_000_000_000, 60),       // 5GB, 60% battery
            create_mobile_node(100_000_000, 80, true),   // 100MB, 80% battery, Wi-Fi
        ];

        let distributor = ShardDistributor { nodes };
        let distribution = distributor.distribute_shards(15, 100_000_000).unwrap();

        // Desktop should get most shards
        assert!(distribution.get("desktop").unwrap().len() >= 7);
        // Laptop should get some shards
        assert!(distribution.get("laptop").unwrap().len() >= 3);
        // Mobile should get fewest shards
        assert!(distribution.get("mobile").unwrap().len() <= 2);
    }

    #[tokio::test]
    async fn test_battery_aware_sync() {
        let scheduler = SyncScheduler {
            device_type: DeviceType::Mobile {
                battery_status: BatteryStatus::new(50, false),  // 50%, not plugged in
                wifi_only: true,
                allocation: 100_000_000,
            },
            last_sync: Instant::now(),
        };

        // Should NOT sync (battery < 70%, not plugged in)
        assert!(!scheduler.should_sync_now());

        // Change battery to 80%
        scheduler.device_type = DeviceType::Mobile {
            battery_status: BatteryStatus::new(80, false),
            wifi_only: true,
            allocation: 100_000_000,
        };

        // Should sync (battery > 70%, Wi-Fi available)
        assert!(scheduler.should_sync_now());
    }
}
```

### Integration Tests

```rust
#[tokio::test]
async fn test_mdns_discovery_with_metadata() {
    // Start two nodes with different device types
    let desktop = MeshNode::new("desktop", DeviceType::Desktop { always_on: true, allocation: 10_000_000_000 }).await.unwrap();
    let mobile = MeshNode::new("mobile", DeviceType::Mobile {
        battery_status: BatteryStatus::new(80, false),
        wifi_only: true,
        allocation: 100_000_000,
    }).await.unwrap();

    // Desktop advertises
    desktop.advertise_mdns().await.unwrap();

    // Mobile discovers desktop
    let peers = mobile.discover_peers().await.unwrap();
    assert_eq!(peers.len(), 1);
    assert_eq!(peers[0].device_type, DeviceType::Desktop { .. });
    assert_eq!(peers[0].storage_allocated_bytes, 10_000_000_000);
}

#[tokio::test]
async fn test_bluetooth_mesh_with_battery_check() {
    let mobile_low_battery = BluetoothMesh {
        device_type: DeviceType::Mobile {
            battery_status: BatteryStatus::new(30, false),  // 30%, not plugged in
            wifi_only: false,
            allocation: 100_000_000,
        },
        ..Default::default()
    };

    let peer = create_test_peer().await;
    let shard = vec![0u8; 1000];

    // Should skip sync (battery < 70%)
    let result = mobile_low_battery.sync_via_ble(&peer, &shard).await;
    assert!(result.is_ok());  // Returns OK but doesn't sync
}
```

---

## Monitoring & Observability

### Metrics to Track

**Mesh Network Metrics:**
- `mesh_peers_discovered`: Count of peers discovered (by protocol)
- `mesh_peers_connected`: Count of active peer connections
- `mesh_sync_attempts`: Total sync attempts (success + failure)
- `mesh_sync_success_rate`: % of successful syncs
- `mesh_sync_latency_ms`: Time to sync shard (by protocol)
- `mesh_bytes_transferred`: Total bytes synced across mesh

**Device Metrics:**
- `device_battery_percent`: Current battery level
- `device_battery_plugged_in`: Boolean (plugged in or not)
- `device_wifi_connected`: Boolean (Wi-Fi or cellular)
- `device_storage_allocated_bytes`: User-configured allocation
- `device_storage_used_bytes`: Current usage
- `device_storage_available_bytes`: Available space

**Sync Scheduler Metrics:**
- `sync_scheduled_count`: Total syncs scheduled
- `sync_skipped_battery`: Syncs skipped due to low battery
- `sync_skipped_network`: Syncs skipped due to cellular-only
- `sync_skipped_frequency`: Syncs skipped due to rate limiting
- `sync_adaptive_predictions`: Accuracy of adaptive sync predictions

---

## Security Considerations

### Threat Model

**Threat 1: Mesh Network Eavesdropping**
- **Attack:** Attacker joins local network, intercepts mDNS/BLE traffic
- **Defense:** All shards encrypted (double-layer: user key + node key)
- **Result:** Attacker sees encrypted traffic (can't decrypt)

**Threat 2: Rogue Node Injection**
- **Attack:** Attacker advertises fake ÆtherLight node, tries to receive shards
- **Defense:** Node authentication (public key verification, trust circle)
- **Result:** Rogue node rejected (not in user's trust circle)

**Threat 3: BLE Replay Attack**
- **Attack:** Attacker records BLE GATT writes, replays later
- **Defense:** Timestamp + nonce in shard metadata (reject stale shards)
- **Result:** Replay rejected (timestamp too old)

**Threat 4: Wi-Fi Direct Group Hijacking**
- **Attack:** Attacker creates fake Wi-Fi Direct group, lures user to join
- **Defense:** Group owner verification (public key, certificate pinning)
- **Result:** Fake group rejected (certificate mismatch)

---

## Related Patterns

- **Pattern-STORAGE-001:** Multi-layer distributed storage (uses mesh networking)
- **Pattern-DHT-001:** Kademlia DHT for global redundancy (Layer 3)
- **Pattern-TRUST-001:** Circle of Trust recovery (node authentication)
- **Pattern-BUSINESS-001:** Viral growth via storage scaling (incentivizes node invitations)

---

## Conclusion

**THE BREAKTHROUGH:** Multi-protocol mesh networking + device-aware allocation + battery optimization

**Why This Works:**
1. **Zero-config:** mDNS handles discovery (no IP addresses, no setup)
2. **Battery-efficient:** BLE 5.0 for mobile (10× less power), adaptive sync scheduling
3. **Flexible allocation:** 100MB to 100GB+ per device (storage is cheap, user controls)
4. **Device-aware:** Desktop = primary storage (always-on), phone = secondary (Wi-Fi only, battery-efficient)
5. **Intelligent distribution:** Shards allocated based on capacity, availability, battery (desktops get most, phones get least)
6. **Offline-first:** Works without internet (local network, Bluetooth, Wi-Fi Direct)

**Result:** Seamless, battery-efficient, device-aware mesh networking that scales with user's device capacity.

---

**PATTERN ID:** Pattern-MESH-001
**STATUS:** Active
**LAST UPDATED:** 2025-10-05
