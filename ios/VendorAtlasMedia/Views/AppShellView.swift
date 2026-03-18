import SwiftData
import SwiftUI

struct AppShellView: View {
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var session: SessionViewModel

    var body: some View {
        Group {
            if session.currentUser == nil {
                SignInView()
            } else {
                roleShell
            }
        }
        .task {
            if session.currentUser == nil {
                await session.restoreSession()
            }
        }
    }

    @ViewBuilder
    private var roleShell: some View {
        if let user = session.currentUser {
            let syncEngine = SyncEngine(apiClient: session.apiClient, modelContext: modelContext)
            switch user.role {
            case .vendor:
                NavigationStack {
                    VendorShareControlsView(viewModel: VendorShareControlsViewModel(syncEngine: syncEngine, session: session))
                }
            case .market, .shopper:
                TabView {
                    NavigationStack {
                        FollowingFeedView(viewModel: FollowingFeedViewModel(syncEngine: syncEngine, session: session))
                    }
                    .tabItem {
                        Label("Following", systemImage: "person.2.fill")
                    }

                    NavigationStack {
                        VendorBusinessPageView(
                            initialUsername: "",
                            viewModel: VendorBusinessPageViewModel(syncEngine: syncEngine, session: session)
                        )
                    }
                    .tabItem {
                        Label("Vendor Page", systemImage: "storefront.fill")
                    }
                }
            }
        }
    }
}
