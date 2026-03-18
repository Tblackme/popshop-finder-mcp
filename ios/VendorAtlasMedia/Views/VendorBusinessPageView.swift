import SwiftUI

struct VendorBusinessPageView: View {
    @EnvironmentObject private var session: SessionViewModel
    @StateObject var viewModel: VendorBusinessPageViewModel
    @State private var username: String

    init(initialUsername: String, viewModel: VendorBusinessPageViewModel) {
        _username = State(initialValue: initialUsername)
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack {
                    TextField("Search vendor username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(.roundedBorder)
                    Button("Load") {
                        Task { await viewModel.load(username: username) }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(username.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }

                if viewModel.isLoading {
                    ProgressView("Loading vendor page…")
                }

                if let vendor = viewModel.vendor {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(vendor.name)
                            .font(.largeTitle.weight(.bold))
                        Text("@\(vendor.username)")
                            .foregroundStyle(.secondary)
                        if let bio = vendor.bio, !bio.isEmpty {
                            Text(bio)
                        }
                        if let category = vendor.category, !category.isEmpty {
                            Label(category, systemImage: "tag.fill")
                                .foregroundStyle(.secondary)
                        }
                        if session.currentUser?.role != .vendor {
                            Button(vendor.isFollowing ? "Unfollow" : "Follow") {
                                Task { await viewModel.toggleFollow() }
                            }
                            .buttonStyle(.borderedProminent)
                        }
                    }
                    .padding(20)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 24))

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Upcoming shared events")
                            .font(.title3.weight(.semibold))
                        if vendor.upcomingEvents.isEmpty {
                            EmptyStateCard(title: "No public events yet", message: "This vendor has not shared any upcoming events with followers.")
                        } else {
                            ForEach(vendor.upcomingEvents) { event in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(event.name)
                                        .font(.headline)
                                    Text(event.locationLine)
                                        .foregroundStyle(.secondary)
                                    if let date = event.date {
                                        Text(date)
                                            .font(.subheadline)
                                    }
                                }
                                .padding(16)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 20))
                            }
                        }
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Inventory highlights")
                            .font(.title3.weight(.semibold))
                        Text("Top cached Shopify items, sorted by stock, with a quick low-stock callout.")
                            .foregroundStyle(.secondary)
                        if viewModel.shopifyHighlights.isEmpty {
                            EmptyStateCard(title: "No Shopify highlights yet", message: "The vendor either has not connected Shopify or inventory has not been synced yet.")
                        } else {
                            ForEach(viewModel.shopifyHighlights, id: \.id) { product in
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(product.name)
                                        .font(.headline)
                                    Text("$\(product.price, specifier: "%.2f")")
                                    Text(product.inventoryQuantity <= 5 ? "Low stock warning" : "\(product.inventoryQuantity) in stock")
                                        .foregroundStyle(product.inventoryQuantity <= 5 ? .orange : .secondary)
                                }
                                .padding(16)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 20))
                            }
                        }
                    }
                } else if !viewModel.errorMessage.isEmpty {
                    EmptyStateCard(title: "Vendor page unavailable", message: viewModel.errorMessage)
                } else {
                    EmptyStateCard(title: "Load a vendor page", message: "Enter a vendor username to open the public business page.")
                }
            }
            .padding(20)
        }
        .navigationTitle("Vendor Page")
        .onAppear {
            if !username.isEmpty, viewModel.vendor == nil {
                Task { await viewModel.load(username: username) }
            }
        }
    }
}

private struct EmptyStateCard: View {
    let title: String
    let message: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            Text(message)
                .foregroundStyle(.secondary)
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }
}
