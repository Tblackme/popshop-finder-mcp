import Foundation
import SwiftData

@Model
final class UserRecord {
    @Attribute(.unique) var id: String
    var email: String
    var username: String
    var role: String
    var createdAt: Date

    init(id: String, email: String, username: String, role: String, createdAt: Date = .now) {
        self.id = id
        self.email = email
        self.username = username
        self.role = role
        self.createdAt = createdAt
    }
}

@Model
final class VendorProfileRecord {
    @Attribute(.unique) var id: String
    var userID: String
    var businessName: String
    var username: String
    var bioText: String
    var category: String
    var location: String
    var instagramURL: String
    var websiteURL: String
    var shopifyURL: String
    var updatedAt: Date

    init(id: String, userID: String, businessName: String, username: String, bioText: String, category: String, location: String, instagramURL: String = "", websiteURL: String = "", shopifyURL: String = "", updatedAt: Date = .now) {
        self.id = id
        self.userID = userID
        self.businessName = businessName
        self.username = username
        self.bioText = bioText
        self.category = category
        self.location = location
        self.instagramURL = instagramURL
        self.websiteURL = websiteURL
        self.shopifyURL = shopifyURL
        self.updatedAt = updatedAt
    }
}

@Model
final class FollowRecord {
    @Attribute(.unique) var id: String
    var followerUserID: String
    var vendorUserID: String
    var followedAt: Date

    init(id: String, followerUserID: String, vendorUserID: String, followedAt: Date = .now) {
        self.id = id
        self.followerUserID = followerUserID
        self.vendorUserID = vendorUserID
        self.followedAt = followedAt
    }
}

@Model
final class EventRecord {
    @Attribute(.unique) var id: String
    var organizerID: String
    var title: String
    var details: String
    var category: String
    var location: String
    var startDate: Date?
    var endDate: Date?
    var vendorFee: Double
    var applicationURL: String
    var isClaimed: Bool
    var createdAt: Date

    init(id: String, organizerID: String = "", title: String, details: String = "", category: String = "", location: String = "", startDate: Date? = nil, endDate: Date? = nil, vendorFee: Double = 0, applicationURL: String = "", isClaimed: Bool = false, createdAt: Date = .now) {
        self.id = id
        self.organizerID = organizerID
        self.title = title
        self.details = details
        self.category = category
        self.location = location
        self.startDate = startDate
        self.endDate = endDate
        self.vendorFee = vendorFee
        self.applicationURL = applicationURL
        self.isClaimed = isClaimed
        self.createdAt = createdAt
    }
}

@Model
final class VendorEventVisibilityRecord {
    @Attribute(.unique) var id: String
    var vendorUserID: String
    var eventID: String
    var visibleToFollowers: Bool
    var createdAt: Date

    init(id: String, vendorUserID: String, eventID: String, visibleToFollowers: Bool, createdAt: Date = .now) {
        self.id = id
        self.vendorUserID = vendorUserID
        self.eventID = eventID
        self.visibleToFollowers = visibleToFollowers
        self.createdAt = createdAt
    }
}

@Model
final class NotificationRecord {
    @Attribute(.unique) var id: String
    var kind: String
    var title: String
    var body: String
    var relatedUserID: String
    var relatedEventID: String
    var createdAt: Date
    var readAt: Date?

    init(id: String, kind: String, title: String, body: String, relatedUserID: String = "", relatedEventID: String = "", createdAt: Date = .now, readAt: Date? = nil) {
        self.id = id
        self.kind = kind
        self.title = title
        self.body = body
        self.relatedUserID = relatedUserID
        self.relatedEventID = relatedEventID
        self.createdAt = createdAt
        self.readAt = readAt
    }
}

@Model
final class ShopifyConnectionRecord {
    @Attribute(.unique) var id: String
    var shopDomain: String
    var connected: Bool
    var updatedAt: Date

    init(id: String = "me", shopDomain: String = "", connected: Bool = false, updatedAt: Date = .now) {
        self.id = id
        self.shopDomain = shopDomain
        self.connected = connected
        self.updatedAt = updatedAt
    }
}

@Model
final class ShopifyProductRecord {
    @Attribute(.unique) var id: String
    var name: String
    var handle: String
    var price: Double
    var inventoryQuantity: Int
    var imageURL: String
    var updatedAt: Date

    init(id: String, name: String, handle: String, price: Double, inventoryQuantity: Int, imageURL: String = "", updatedAt: Date = .now) {
        self.id = id
        self.name = name
        self.handle = handle
        self.price = price
        self.inventoryQuantity = inventoryQuantity
        self.imageURL = imageURL
        self.updatedAt = updatedAt
    }
}
