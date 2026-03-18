import Foundation

enum UserRole: String, Codable, CaseIterable {
    case vendor
    case market
    case shopper

    var title: String {
        switch self {
        case .vendor:
            return "Vendor"
        case .market:
            return "Organizer"
        case .shopper:
            return "Shopper"
        }
    }
}

struct SessionUser: Codable, Equatable {
    let id: Int
    let name: String
    let email: String
    let username: String
    let role: UserRole
}

struct AuthEnvelope: Codable {
    let ok: Bool
    let user: SessionUser
}

struct VendorEvent: Codable, Identifiable, Hashable {
    let id: String
    let name: String
    let city: String?
    let state: String?
    let date: String?
    let boothPrice: Double?
    let applicationLink: String?
    let visibleToFollowers: Bool?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case city
        case state
        case date
        case boothPrice = "booth_price"
        case applicationLink = "application_link"
        case visibleToFollowers = "visible_to_followers"
    }

    var locationLine: String {
        [city, state].compactMap { value in
            guard let value, !value.isEmpty else { return nil }
            return value
        }.joined(separator: ", ")
    }
}

struct VendorSummary: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let username: String
    let bio: String?
    let category: String?
    let isFollowing: Bool
    let upcomingEvents: [VendorEvent]

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case username
        case bio
        case category
        case isFollowing = "is_following"
        case upcomingEvents = "upcoming_events"
    }
}

struct VendorProfileEnvelope: Codable {
    let ok: Bool
    let vendor: VendorSummary
}

struct NotificationItem: Codable, Identifiable, Hashable {
    let id: String
    let kind: String
    let title: String
    let body: String
    let relatedUserID: Int?
    let relatedEventID: String?
    let createdAt: String
    let readAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case kind
        case title
        case body
        case relatedUserID = "related_user_id"
        case relatedEventID = "related_event_id"
        case createdAt = "created_at"
        case readAt = "read_at"
    }
}

struct FeedEvent: Codable, Identifiable, Hashable {
    struct FeedVendor: Codable, Hashable {
        let id: Int
        let name: String
        let username: String
    }

    let id: String
    let name: String
    let city: String?
    let state: String?
    let date: String?
    let vendor: FeedVendor?
}

struct FollowingFeedEnvelope: Codable {
    let ok: Bool
    let vendors: [VendorSummary]
    let events: [FeedEvent]
    let notifications: [NotificationItem]
}

struct VendorFollowerEventsEnvelope: Codable {
    let ok: Bool
    let events: [VendorEvent]
}

struct VendorFollowerEventUpdateResponse: Codable {
    let ok: Bool
    let eventID: String
    let visibleToFollowers: Bool

    enum CodingKeys: String, CodingKey {
        case ok
        case eventID = "event_id"
        case visibleToFollowers = "visible_to_followers"
    }
}

struct ShopifyConnectionState: Codable {
    let connected: Bool
    let shop: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case connected
        case shop
        case updatedAt = "updated_at"
    }
}

struct ShopifyProduct: Codable, Identifiable, Hashable {
    let id: Int
    let title: String
    let handle: String
    let price: Double?
    let inventoryQuantity: Int?
    let imageURL: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case handle
        case price
        case inventoryQuantity = "inventory_quantity"
        case imageURL = "image_url"
        case updatedAt = "updated_at"
    }
}

struct ShopifyProductsEnvelope: Codable {
    let ok: Bool?
    let products: [ShopifyProduct]
}

struct APIErrorEnvelope: Codable, Error {
    let ok: Bool?
    let error: String?
    let detail: String?

    var message: String {
        error ?? detail ?? "Request failed."
    }
}

enum DevLoginRole: String, CaseIterable {
    case vendor
    case market
    case shopper

    var title: String {
        switch self {
        case .vendor:
            return "Test Vendor"
        case .market:
            return "Test Organizer"
        case .shopper:
            return "Test Shopper"
        }
    }
}
