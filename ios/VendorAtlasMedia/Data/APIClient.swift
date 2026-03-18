import Foundation

final class APIClient {
    enum APIClientError: LocalizedError {
        case invalidURL
        case invalidResponse
        case server(String)

        var errorDescription: String? {
            switch self {
            case .invalidURL:
                return "The backend URL is invalid."
            case .invalidResponse:
                return "The server returned an unexpected response."
            case let .server(message):
                return message
            }
        }
    }

    private let decoder = JSONDecoder()
    private let encoder = JSONEncoder()
    private let session: URLSession

    init() {
        let configuration = URLSessionConfiguration.default
        configuration.httpCookieStorage = .shared
        configuration.httpShouldSetCookies = true
        session = URLSession(configuration: configuration)
    }

    func signIn(baseURL: URL, identifier: String, password: String) async throws -> SessionUser {
        let payload = ["identifier": identifier, "password": password]
        let response: AuthEnvelope = try await request(baseURL: baseURL, path: "/api/auth/signin", method: "POST", body: payload)
        return response.user
    }

    func devLogin(baseURL: URL, role: DevLoginRole) async throws -> SessionUser {
        let payload = ["role": role.rawValue]
        let response: AuthEnvelope = try await request(baseURL: baseURL, path: "/api/auth/dev-login", method: "POST", body: payload)
        return response.user
    }

    func me(baseURL: URL) async throws -> SessionUser {
        let response: AuthEnvelope = try await request(baseURL: baseURL, path: "/api/auth/me")
        return response.user
    }

    func logout(baseURL: URL) async throws {
        struct Empty: Codable {}
        let _: APIErrorEnvelope = try await request(baseURL: baseURL, path: "/api/auth/logout", method: "POST", body: Empty())
    }

    func vendorProfile(baseURL: URL, username: String) async throws -> VendorSummary {
        let response: VendorProfileEnvelope = try await request(baseURL: baseURL, path: "/api/vendors/\(username.lowercased())")
        return response.vendor
    }

    func followVendor(baseURL: URL, vendorID: Int) async throws {
        struct Empty: Codable {}
        let _: APIErrorEnvelope = try await request(baseURL: baseURL, path: "/api/vendors/\(vendorID)/follow", method: "POST", body: Empty())
    }

    func unfollowVendor(baseURL: URL, vendorID: Int) async throws {
        let _: APIErrorEnvelope = try await request(baseURL: baseURL, path: "/api/vendors/\(vendorID)/follow", method: "DELETE")
    }

    func followingFeed(baseURL: URL) async throws -> FollowingFeedEnvelope {
        try await request(baseURL: baseURL, path: "/api/shopper/following")
    }

    func followerEvents(baseURL: URL) async throws -> [VendorEvent] {
        let response: VendorFollowerEventsEnvelope = try await request(baseURL: baseURL, path: "/api/vendor/follower-events")
        return response.events
    }

    func setFollowerEventVisibility(baseURL: URL, eventID: String, visible: Bool) async throws -> VendorFollowerEventUpdateResponse {
        let payload = ["event_id": eventID, "visible_to_followers": visible] as [String: Any]
        return try await request(baseURL: baseURL, path: "/api/vendor/follower-events", method: "POST", bodyAny: payload)
    }

    func shopifyConnection(baseURL: URL) async throws -> ShopifyConnectionState {
        try await request(baseURL: baseURL, path: "/api/shopify/me")
    }

    func shopifyProducts(baseURL: URL) async throws -> [ShopifyProduct] {
        let response: ShopifyProductsEnvelope = try await request(baseURL: baseURL, path: "/api/shopify/products")
        return response.products
    }

    private func request<T: Decodable>(baseURL: URL, path: String, method: String = "GET") async throws -> T {
        var request = try makeRequest(baseURL: baseURL, path: path, method: method)
        return try await perform(request)
    }

    private func request<T: Decodable, Body: Encodable>(baseURL: URL, path: String, method: String, body: Body) async throws -> T {
        var request = try makeRequest(baseURL: baseURL, path: path, method: method)
        request.httpBody = try encoder.encode(body)
        return try await perform(request)
    }

    private func request<T: Decodable>(baseURL: URL, path: String, method: String, bodyAny: [String: Any]) async throws -> T {
        var request = try makeRequest(baseURL: baseURL, path: path, method: method)
        request.httpBody = try JSONSerialization.data(withJSONObject: bodyAny)
        return try await perform(request)
    }

    private func makeRequest(baseURL: URL, path: String, method: String) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIClientError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        return request
    }

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        guard (200 ... 299).contains(http.statusCode) else {
            if let errorPayload = try? decoder.decode(APIErrorEnvelope.self, from: data) {
                throw APIClientError.server(errorPayload.message)
            }
            throw APIClientError.server("Request failed with status \(http.statusCode).")
        }
        if data.isEmpty, let payload = APIErrorEnvelope(ok: true, error: nil, detail: nil) as? T {
            return payload
        }
        return try decoder.decode(T.self, from: data)
    }
}
