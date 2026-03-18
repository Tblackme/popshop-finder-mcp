import Foundation

@MainActor
final class SessionViewModel: ObservableObject {
    @Published var currentUser: SessionUser?
    @Published var backendURLText: String
    @Published var isLoading = false
    @Published var errorMessage = ""

    let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
        backendURLText = UserDefaults.standard.string(forKey: "vendor_atlas_media_backend_url") ?? "http://localhost:3001"
    }

    var baseURL: URL? {
        URL(string: backendURLText)
    }

    func restoreSession() async {
        guard let baseURL else { return }
        do {
            currentUser = try await apiClient.me(baseURL: baseURL)
        } catch {
            currentUser = nil
        }
    }

    func signIn(identifier: String, password: String) async {
        guard let baseURL else {
            errorMessage = "Enter a valid backend URL."
            return
        }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            persistBaseURL()
            currentUser = try await apiClient.signIn(baseURL: baseURL, identifier: identifier, password: password)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func devLogin(role: DevLoginRole) async {
        guard let baseURL else {
            errorMessage = "Enter a valid backend URL."
            return
        }
        isLoading = true
        errorMessage = ""
        defer { isLoading = false }
        do {
            persistBaseURL()
            currentUser = try await apiClient.devLogin(baseURL: baseURL, role: role)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signOut() async {
        guard let baseURL else {
            currentUser = nil
            return
        }
        do {
            try await apiClient.logout(baseURL: baseURL)
        } catch {
            errorMessage = error.localizedDescription
        }
        currentUser = nil
    }

    private func persistBaseURL() {
        UserDefaults.standard.set(backendURLText, forKey: "vendor_atlas_media_backend_url")
    }
}
