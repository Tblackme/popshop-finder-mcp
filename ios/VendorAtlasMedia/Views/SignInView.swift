import SwiftUI

struct SignInView: View {
    @EnvironmentObject private var session: SessionViewModel
    @State private var identifier = ""
    @State private var password = ""

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text("Vendor Atlas Media")
                            .font(.largeTitle.weight(.bold))
                        Text("Follow vendors, watch shared event updates, and keep the organizer side of the network easy to scan.")
                            .foregroundStyle(.secondary)
                    }

                    VStack(alignment: .leading, spacing: 16) {
                        TextField("Backend URL", text: $session.backendURLText)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .textFieldStyle(.roundedBorder)

                        TextField("Username or Email", text: $identifier)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .textFieldStyle(.roundedBorder)

                        SecureField("Password", text: $password)
                            .textFieldStyle(.roundedBorder)

                        Button {
                            Task { await session.signIn(identifier: identifier, password: password) }
                        } label: {
                            HStack {
                                Spacer()
                                if session.isLoading {
                                    ProgressView()
                                } else {
                                    Text("Sign In")
                                        .fontWeight(.semibold)
                                }
                                Spacer()
                            }
                        }
                        .buttonStyle(.borderedProminent)
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Test access")
                            .font(.headline)
                        Text("Use these local shortcuts while the app is still in MVP mode.")
                            .foregroundStyle(.secondary)
                        ForEach(DevLoginRole.allCases, id: \.rawValue) { role in
                            Button(role.title) {
                                Task { await session.devLogin(role: role) }
                            }
                            .buttonStyle(.bordered)
                        }
                    }

                    if !session.errorMessage.isEmpty {
                        Text(session.errorMessage)
                            .foregroundStyle(.red)
                            .padding()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(Color.red.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }
                }
                .padding(24)
            }
            .background(Color(.systemGroupedBackground))
        }
    }
}
