import Foundation
import SwiftData

struct FollowingFeedSnapshot {
    let vendors: [VendorProfileRecord]
    let events: [EventRecord]
    let notifications: [NotificationRecord]
}

@MainActor
final class SyncEngine {
    private let apiClient: APIClient
    private let modelContext: ModelContext

    init(apiClient: APIClient, modelContext: ModelContext) {
        self.apiClient = apiClient
        self.modelContext = modelContext
    }

    func loadCachedFeed() throws -> FollowingFeedSnapshot {
        let vendors = try modelContext.fetch(FetchDescriptor<VendorProfileRecord>(sortBy: [SortDescriptor(\.businessName)]))
        let follows = try modelContext.fetch(FetchDescriptor<FollowRecord>(sortBy: [SortDescriptor(\.followedAt, order: .reverse)]))
        let notifications = try modelContext.fetch(FetchDescriptor<NotificationRecord>(sortBy: [SortDescriptor(\.createdAt, order: .reverse)]))
        let events = try modelContext.fetch(FetchDescriptor<EventRecord>(sortBy: [SortDescriptor(\.startDate, order: .forward)]))
        let followedVendorIDs = Set(follows.map(\.vendorUserID))
        return FollowingFeedSnapshot(
            vendors: vendors.filter { followedVendorIDs.contains($0.userID) },
            events: events.filter { followedVendorIDs.contains($0.organizerID) },
            notifications: notifications
        )
    }

    func refreshFollowingFeed(baseURL: URL, currentUserID: Int) async throws -> FollowingFeedSnapshot {
        let payload = try await apiClient.followingFeed(baseURL: baseURL)
        for vendor in payload.vendors {
            upsert(vendor: vendor, currentUserID: currentUserID)
        }
        for event in payload.events {
            upsert(feedEvent: event)
        }
        for notification in payload.notifications {
            upsert(notification: notification)
        }
        try modelContext.save()
        return try loadCachedFeed()
    }

    func refreshVendorProfile(baseURL: URL, username: String, currentUserID: Int) async throws -> VendorSummary {
        let vendor = try await apiClient.vendorProfile(baseURL: baseURL, username: username)
        upsert(vendor: vendor, currentUserID: currentUserID)
        for event in vendor.upcomingEvents {
            upsert(vendorEvent: event, vendorUserID: vendor.id)
        }
        try modelContext.save()
        return vendor
    }

    func refreshVendorShareEvents(baseURL: URL, vendorUserID: Int) async throws -> [VendorEvent] {
        let events = try await apiClient.followerEvents(baseURL: baseURL)
        for event in events {
            upsert(vendorEvent: event, vendorUserID: vendorUserID)
            upsert(visibilityEvent: event, vendorUserID: vendorUserID)
        }
        try modelContext.save()
        return events
    }

    func refreshShopify(baseURL: URL) async throws -> [ShopifyProductRecord] {
        let connection = try await apiClient.shopifyConnection(baseURL: baseURL)
        let products = try await apiClient.shopifyProducts(baseURL: baseURL)
        upsert(connection: connection)
        for product in products {
            upsert(shopifyProduct: product)
        }
        try modelContext.save()
        return try topShopifyProducts()
    }

    func topShopifyProducts(limit: Int = 10) throws -> [ShopifyProductRecord] {
        let products = try modelContext.fetch(
            FetchDescriptor<ShopifyProductRecord>(
                sortBy: [
                    SortDescriptor(\.inventoryQuantity, order: .reverse),
                    SortDescriptor(\.updatedAt, order: .reverse),
                ]
            )
        )
        return Array(products.prefix(limit))
    }

    func toggleFollow(baseURL: URL, vendor: VendorSummary, currentUserID: Int) async throws -> VendorSummary {
        if vendor.isFollowing {
            try await apiClient.unfollowVendor(baseURL: baseURL, vendorID: vendor.id)
            removeFollow(currentUserID: currentUserID, vendorUserID: vendor.id)
        } else {
            try await apiClient.followVendor(baseURL: baseURL, vendorID: vendor.id)
            upsertFollow(currentUserID: currentUserID, vendorUserID: vendor.id)
        }
        try modelContext.save()
        return try await refreshVendorProfile(baseURL: baseURL, username: vendor.username, currentUserID: currentUserID)
    }

    func setFollowerVisibility(baseURL: URL, vendorUserID: Int, eventID: String, visible: Bool) async throws {
        _ = try await apiClient.setFollowerEventVisibility(baseURL: baseURL, eventID: eventID, visible: visible)
        let identifier = "\(vendorUserID)-\(eventID)"
        if let record = try findVisibility(id: identifier) {
            record.visibleToFollowers = visible
        } else {
            modelContext.insert(VendorEventVisibilityRecord(id: identifier, vendorUserID: String(vendorUserID), eventID: eventID, visibleToFollowers: visible))
        }
        try modelContext.save()
    }

    private func upsert(vendor: VendorSummary, currentUserID: Int) {
        let vendorID = String(vendor.id)
        let existing = try? findVendor(id: vendorID)
        if let record = existing ?? nil {
            record.businessName = vendor.name
            record.userID = vendorID
            record.username = vendor.username
            record.bioText = vendor.bio ?? ""
            record.category = vendor.category ?? ""
            record.updatedAt = .now
        } else {
            modelContext.insert(
                VendorProfileRecord(
                    id: vendorID,
                    userID: vendorID,
                    businessName: vendor.name,
                    username: vendor.username,
                    bioText: vendor.bio ?? "",
                    category: vendor.category ?? "",
                    location: ""
                )
            )
        }
        if vendor.isFollowing {
            upsertFollow(currentUserID: currentUserID, vendorUserID: vendor.id)
        }
    }

    private func upsert(feedEvent: FeedEvent) {
        let existing = try? findEvent(id: feedEvent.id)
        if let record = existing ?? nil {
            record.title = feedEvent.name
            record.location = [feedEvent.city, feedEvent.state].compactMap { $0 }.joined(separator: ", ")
            record.startDate = Self.parseDate(feedEvent.date)
            record.endDate = Self.parseDate(feedEvent.date)
            record.organizerID = String(feedEvent.vendor?.id ?? 0)
        } else {
            modelContext.insert(
                EventRecord(
                    id: feedEvent.id,
                    organizerID: String(feedEvent.vendor?.id ?? 0),
                    title: feedEvent.name,
                    location: [feedEvent.city, feedEvent.state].compactMap { $0 }.joined(separator: ", "),
                    startDate: Self.parseDate(feedEvent.date),
                    endDate: Self.parseDate(feedEvent.date)
                )
            )
        }
    }

    private func upsert(vendorEvent: VendorEvent, vendorUserID: Int) {
        let existing = try? findEvent(id: vendorEvent.id)
        if let record = existing ?? nil {
            record.title = vendorEvent.name
            record.location = vendorEvent.locationLine
            record.startDate = Self.parseDate(vendorEvent.date)
            record.endDate = Self.parseDate(vendorEvent.date)
            record.vendorFee = vendorEvent.boothPrice ?? 0
            record.applicationURL = vendorEvent.applicationLink ?? ""
            record.organizerID = String(vendorUserID)
        } else {
            modelContext.insert(
                EventRecord(
                    id: vendorEvent.id,
                    organizerID: String(vendorUserID),
                    title: vendorEvent.name,
                    location: vendorEvent.locationLine,
                    startDate: Self.parseDate(vendorEvent.date),
                    endDate: Self.parseDate(vendorEvent.date),
                    vendorFee: vendorEvent.boothPrice ?? 0,
                    applicationURL: vendorEvent.applicationLink ?? ""
                )
            )
        }
    }

    private func upsert(visibilityEvent: VendorEvent, vendorUserID: Int) {
        guard let visible = visibilityEvent.visibleToFollowers else { return }
        let identifier = "\(vendorUserID)-\(visibilityEvent.id)"
        let existing = try? findVisibility(id: identifier)
        if let record = existing ?? nil {
            record.visibleToFollowers = visible
        } else {
            modelContext.insert(
                VendorEventVisibilityRecord(
                    id: identifier,
                    vendorUserID: String(vendorUserID),
                    eventID: visibilityEvent.id,
                    visibleToFollowers: visible
                )
            )
        }
    }

    private func upsert(notification: NotificationItem) {
        let existing = try? findNotification(id: notification.id)
        if let record = existing ?? nil {
            record.kind = notification.kind
            record.title = notification.title
            record.body = notification.body
            record.relatedUserID = String(notification.relatedUserID ?? 0)
            record.relatedEventID = notification.relatedEventID ?? ""
            record.createdAt = Self.parseDateTime(notification.createdAt) ?? .now
            record.readAt = Self.parseDateTime(notification.readAt)
        } else {
            modelContext.insert(
                NotificationRecord(
                    id: notification.id,
                    kind: notification.kind,
                    title: notification.title,
                    body: notification.body,
                    relatedUserID: String(notification.relatedUserID ?? 0),
                    relatedEventID: notification.relatedEventID ?? "",
                    createdAt: Self.parseDateTime(notification.createdAt) ?? .now,
                    readAt: Self.parseDateTime(notification.readAt)
                )
            )
        }
    }

    private func upsertFollow(currentUserID: Int, vendorUserID: Int) {
        let identifier = "\(currentUserID)-\(vendorUserID)"
        if (try? findFollow(id: identifier)) == nil {
            modelContext.insert(FollowRecord(id: identifier, followerUserID: String(currentUserID), vendorUserID: String(vendorUserID)))
        }
    }

    private func removeFollow(currentUserID: Int, vendorUserID: Int) {
        let identifier = "\(currentUserID)-\(vendorUserID)"
        let existing = try? findFollow(id: identifier)
        if let record = existing ?? nil {
            modelContext.delete(record)
        }
    }

    private func upsert(connection: ShopifyConnectionState) {
        let existing = try? modelContext.fetch(FetchDescriptor<ShopifyConnectionRecord>()).first
        if let record = existing ?? nil {
            record.connected = connection.connected
            record.shopDomain = connection.shop ?? ""
            record.updatedAt = Self.parseDateTime(connection.updatedAt) ?? .now
        } else {
            modelContext.insert(
                ShopifyConnectionRecord(
                    shopDomain: connection.shop ?? "",
                    connected: connection.connected,
                    updatedAt: Self.parseDateTime(connection.updatedAt) ?? .now
                )
            )
        }
    }

    private func upsert(shopifyProduct product: ShopifyProduct) {
        let identifier = String(product.id)
        let existing = try? findShopifyProduct(id: identifier)
        if let record = existing ?? nil {
            record.name = product.title
            record.handle = product.handle
            record.price = product.price ?? 0
            record.inventoryQuantity = product.inventoryQuantity ?? 0
            record.imageURL = product.imageURL ?? ""
            record.updatedAt = Self.parseDateTime(product.updatedAt) ?? .now
        } else {
            modelContext.insert(
                ShopifyProductRecord(
                    id: identifier,
                    name: product.title,
                    handle: product.handle,
                    price: product.price ?? 0,
                    inventoryQuantity: product.inventoryQuantity ?? 0,
                    imageURL: product.imageURL ?? "",
                    updatedAt: Self.parseDateTime(product.updatedAt) ?? .now
                )
            )
        }
    }

    private func findVendor(id: String) throws -> VendorProfileRecord? {
        try modelContext.fetch(FetchDescriptor<VendorProfileRecord>(predicate: #Predicate { $0.id == id })).first
    }

    private func findEvent(id: String) throws -> EventRecord? {
        try modelContext.fetch(FetchDescriptor<EventRecord>(predicate: #Predicate { $0.id == id })).first
    }

    private func findFollow(id: String) throws -> FollowRecord? {
        try modelContext.fetch(FetchDescriptor<FollowRecord>(predicate: #Predicate { $0.id == id })).first
    }

    private func findNotification(id: String) throws -> NotificationRecord? {
        try modelContext.fetch(FetchDescriptor<NotificationRecord>(predicate: #Predicate { $0.id == id })).first
    }

    private func findVisibility(id: String) throws -> VendorEventVisibilityRecord? {
        try modelContext.fetch(FetchDescriptor<VendorEventVisibilityRecord>(predicate: #Predicate { $0.id == id })).first
    }

    private func findShopifyProduct(id: String) throws -> ShopifyProductRecord? {
        try modelContext.fetch(FetchDescriptor<ShopifyProductRecord>(predicate: #Predicate { $0.id == id })).first
    }

    static func parseDate(_ value: String?) -> Date? {
        guard let value, !value.isEmpty else { return nil }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter.date(from: value)
    }

    static func parseDateTime(_ value: String?) -> Date? {
        guard let value, !value.isEmpty else { return nil }
        return ISO8601DateFormatter().date(from: value) ?? parseDate(value)
    }
}
