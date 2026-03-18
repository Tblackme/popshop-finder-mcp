import Foundation

@MainActor
final class VendorShareControlsViewModel: ObservableObject {
    @Published var events: [VendorEvent] = []
    @Published var isLoading = false
    @Published var errorMessage = ""

    private let syncEngine: SyncEngine
    private let session: SessionViewModel

    init(syncEngine: SyncEngine, session: SessionViewModel) {
        self.syncEngine = syncEngine
        self.session = session
    }

    func load() async {
        guard let baseURL = session.baseURL, let user = session.currentUser else { return }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            events = try await syncEngine.refreshVendorShareEvents(baseURL: baseURL, vendorUserID: user.id)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func updateVisibility(eventID: String, isVisible: Bool) async {
        guard let baseURL = session.baseURL, let user = session.currentUser else { return }
        do {
            try await syncEngine.setFollowerVisibility(baseURL: baseURL, vendorUserID: user.id, eventID: eventID, visible: isVisible)
            if let index = events.firstIndex(where: { $0.id == eventID }) {
                let current = events[index]
                events[index] = VendorEvent(
                    id: current.id,
                    name: current.name,
                    city: current.city,
                    state: current.state,
                    date: current.date,
                    boothPrice: current.boothPrice,
                    applicationLink: current.applicationLink,
                    visibleToFollowers: isVisible
                )
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
