import Foundation

@MainActor
final class VendorBusinessPageViewModel: ObservableObject {
    @Published var vendor: VendorSummary?
    @Published var shopifyHighlights: [ShopifyProductRecord] = []
    @Published var isLoading = false
    @Published var errorMessage = ""

    private let syncEngine: SyncEngine
    private let session: SessionViewModel

    init(syncEngine: SyncEngine, session: SessionViewModel) {
        self.syncEngine = syncEngine
        self.session = session
    }

    func load(username: String) async {
        guard let baseURL = session.baseURL else { return }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            vendor = try await syncEngine.refreshVendorProfile(
                baseURL: baseURL,
                username: username,
                currentUserID: session.currentUser?.id ?? 0
            )
            do {
                shopifyHighlights = try await syncEngine.refreshShopify(baseURL: baseURL)
            } catch {
                shopifyHighlights = (try? syncEngine.topShopifyProducts()) ?? []
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func toggleFollow() async {
        guard let vendor, let baseURL = session.baseURL else { return }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            self.vendor = try await syncEngine.toggleFollow(
                baseURL: baseURL,
                vendor: vendor,
                currentUserID: session.currentUser?.id ?? 0
            )
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
