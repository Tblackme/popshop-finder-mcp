import SwiftData
import SwiftUI

@main
struct VendorAtlasMediaApp: App {
    @StateObject private var session = SessionViewModel(apiClient: APIClient())

    var body: some Scene {
        WindowGroup {
            AppShellView()
                .environmentObject(session)
        }
        .modelContainer(for: [
            UserRecord.self,
            VendorProfileRecord.self,
            FollowRecord.self,
            EventRecord.self,
            VendorEventVisibilityRecord.self,
            NotificationRecord.self,
            ShopifyConnectionRecord.self,
            ShopifyProductRecord.self,
        ])
    }
}
