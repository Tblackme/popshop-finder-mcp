import Foundation

@MainActor
final class FollowingFeedViewModel: ObservableObject {
    @Published var followedVendors: [VendorProfileRecord] = []
    @Published var feedEvents: [EventRecord] = []
    @Published var notifications: [NotificationRecord] = []
    @Published var vendorLookupUsername = ""
    @Published var isLoading = false
    @Published var errorMessage = ""

    let syncEngine: SyncEngine
    private let session: SessionViewModel

    init(syncEngine: SyncEngine, session: SessionViewModel) {
        self.syncEngine = syncEngine
        self.session = session
    }

    func loadCached() {
        do {
            let snapshot = try syncEngine.loadCachedFeed()
            followedVendors = snapshot.vendors
            feedEvents = snapshot.events
            notifications = dedupe(snapshot.notifications)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refresh() async {
        guard let user = session.currentUser, let baseURL = session.baseURL else { return }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            let snapshot = try await syncEngine.refreshFollowingFeed(baseURL: baseURL, currentUserID: user.id)
            followedVendors = snapshot.vendors
            feedEvents = snapshot.events
            notifications = dedupe(snapshot.notifications)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func dedupe(_ items: [NotificationRecord]) -> [NotificationRecord] {
        var seen = Set<String>()
        return items.filter { seen.insert($0.id).inserted }
    }
}
