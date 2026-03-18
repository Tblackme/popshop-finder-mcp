import SwiftData
import SwiftUI

struct FollowingFeedView: View {
    @Environment(\.modelContext) private var modelContext
    @EnvironmentObject private var session: SessionViewModel
    @StateObject var viewModel: FollowingFeedViewModel

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Following feed")
                        .font(.title2.weight(.semibold))
                    Text("See which vendors you follow, what they shared, and what needs attention soon.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 8)
            }

            if viewModel.isLoading {
                Section {
                    HStack {
                        ProgressView()
                        Text("Refreshing your feed...")
                    }
                }
            }

            Section("Vendors you follow") {
                if viewModel.followedVendors.isEmpty {
                    EmptyStateRow(title: "No vendors followed yet", message: "Look up a vendor by username to start building your feed.")
                } else {
                    ForEach(viewModel.followedVendors, id: \.id) { vendor in
                        NavigationLink(value: vendor.username) {
                            VStack(alignment: .leading, spacing: 6) {
                                Text(vendor.businessName)
                                    .font(.headline)
                                Text("@\(vendor.username)")
                                    .foregroundStyle(.secondary)
                                if !vendor.category.isEmpty {
                                    Text(vendor.category)
                                        .font(.subheadline)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }

            Section("Upcoming shared events") {
                if viewModel.feedEvents.isEmpty {
                    EmptyStateRow(title: "Nothing shared yet", message: "Your feed stays stable even when vendors have not shared any events yet.")
                } else {
                    ForEach(viewModel.feedEvents, id: \.id) { event in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(event.title)
                                .font(.headline)
                            Text(event.location)
                                .foregroundStyle(.secondary)
                            if let startDate = event.startDate {
                                Text(startDate.formatted(date: .abbreviated, time: .omitted))
                                    .font(.subheadline)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section("Notifications") {
                if viewModel.notifications.isEmpty {
                    EmptyStateRow(title: "No notifications yet", message: "New followers, vendor shares, and upcoming event reminders will show up here.")
                } else {
                    ForEach(viewModel.notifications, id: \.id) { item in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(item.title)
                                .font(.headline)
                            Text(item.body)
                                .foregroundStyle(.secondary)
                        }
                        .padding(.vertical, 4)
                    }
                }
            }

            Section("Quick vendor lookup") {
                TextField("Enter vendor username", text: $viewModel.vendorLookupUsername)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                NavigationLink("Open vendor page", value: viewModel.vendorLookupUsername.trimmingCharacters(in: .whitespacesAndNewlines))
                    .disabled(viewModel.vendorLookupUsername.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
        }
        .navigationTitle(session.currentUser?.role == .market ? "Organizer Feed" : "Following")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Sign Out") {
                    Task { await session.signOut() }
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Refresh") {
                    Task { await viewModel.refresh() }
                }
            }
        }
        .navigationDestination(for: String.self) { username in
            VendorBusinessPageView(
                initialUsername: username,
                viewModel: VendorBusinessPageViewModel(
                    syncEngine: SyncEngine(apiClient: session.apiClient, modelContext: modelContext),
                    session: session
                )
            )
        }
        .task {
            viewModel.loadCached()
            await viewModel.refresh()
        }
        .overlay(alignment: .bottom) {
            if !viewModel.errorMessage.isEmpty {
                ErrorBanner(message: viewModel.errorMessage)
            }
        }
    }
}

private struct EmptyStateRow: View {
    let title: String
    let message: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.headline)
            Text(message)
                .foregroundStyle(.secondary)
        }
        .padding(.vertical, 8)
    }
}

private struct ErrorBanner: View {
    let message: String

    var body: some View {
        Text(message)
            .foregroundStyle(.red)
            .padding()
            .frame(maxWidth: .infinity)
            .background(.thinMaterial)
    }
}
