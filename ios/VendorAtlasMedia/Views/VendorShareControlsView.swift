import SwiftUI

struct VendorShareControlsView: View {
    @EnvironmentObject private var session: SessionViewModel
    @StateObject var viewModel: VendorShareControlsViewModel

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Share events with followers")
                        .font(.title2.weight(.semibold))
                    Text("Choose which saved events appear on your public business page and in follower feeds.")
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 8)
            }

            if viewModel.isLoading {
                Section {
                    HStack {
                        ProgressView()
                        Text("Loading shared events…")
                    }
                }
            }

            Section("Saved events") {
                if viewModel.events.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("No saved events yet")
                            .font(.headline)
                        Text("Once you save events on the vendor side, you can decide which ones are public here.")
                            .foregroundStyle(.secondary)
                    }
                    .padding(.vertical, 8)
                } else {
                    ForEach(viewModel.events) { event in
                        VStack(alignment: .leading, spacing: 10) {
                            Text(event.name)
                                .font(.headline)
                            Text(event.locationLine)
                                .foregroundStyle(.secondary)
                            if let date = event.date {
                                Text(date)
                                    .font(.subheadline)
                            }
                            Toggle("Visible to followers", isOn: Binding(
                                get: { event.visibleToFollowers ?? false },
                                set: { value in
                                    Task { await viewModel.updateVisibility(eventID: event.id, isVisible: value) }
                                }
                            ))
                        }
                        .padding(.vertical, 6)
                    }
                }
            }
        }
        .navigationTitle("Vendor Controls")
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button("Sign Out") {
                    Task { await session.signOut() }
                }
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Refresh") {
                    Task { await viewModel.load() }
                }
            }
        }
        .task {
            await viewModel.load()
        }
        .overlay(alignment: .bottom) {
            if !viewModel.errorMessage.isEmpty {
                Text(viewModel.errorMessage)
                    .foregroundStyle(.red)
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(.thinMaterial)
            }
        }
    }
}
