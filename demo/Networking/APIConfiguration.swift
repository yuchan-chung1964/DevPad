import Foundation

/// Where the DevPad backend lives and how requests are authenticated.
struct APIConfiguration {
    var baseURL: URL
    /// Returns the current identity-provider JWT (Supabase, Auth0, Clerk, Firebase...), refreshing it if needed.
    /// Return nil when signed out; requests then fail with `APIError.unauthorized` without hitting the network.
    var tokenProvider: @Sendable () async throws -> String?
    var timeout: TimeInterval = 30
    /// How many times a 429 is retried (waiting for `Retry-After`) before giving up.
    var maxRateLimitRetries = 2

    /// Reads `DEVPAD_API_URL` from Info.plist; falls back to the local dev server.
    /// The iOS simulator can reach the host Mac at localhost. A real device needs the Mac's LAN IP
    /// (and an App Transport Security exception for plain http) or a deployed https URL.
    static func fromBundle(
        _ bundle: Bundle = .main,
        tokenProvider: @escaping @Sendable () async throws -> String?
    ) -> APIConfiguration {
        let raw = bundle.object(forInfoDictionaryKey: "DEVPAD_API_URL") as? String
        let url = raw.flatMap(URL.init(string:)) ?? URL(string: "http://localhost:8000")!
        return APIConfiguration(baseURL: url, tokenProvider: tokenProvider)
    }
}
