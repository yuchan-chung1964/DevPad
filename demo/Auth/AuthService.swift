import Foundation
import Supabase

/// Supabase project settings, read from Info.plist (`SUPABASE_URL`, `SUPABASE_ANON_KEY`).
/// The anon key is public by design (it ships in every app); row access is enforced by the user's JWT.
struct SupabaseConfiguration {
    let url: URL
    let anonKey: String

    static func fromBundle(_ bundle: Bundle = .main) -> SupabaseConfiguration? {
        guard
            let rawURL = bundle.object(forInfoDictionaryKey: "SUPABASE_URL") as? String,
            let url = URL(string: rawURL), url.host != nil,
            let key = bundle.object(forInfoDictionaryKey: "SUPABASE_ANON_KEY") as? String, !key.isEmpty
        else { return nil }
        return SupabaseConfiguration(url: url, anonKey: key)
    }
}

/// Thin wrapper over the Supabase SDK. The SDK stores the session in the Keychain and refreshes it itself.
final class AuthService: Sendable {
    let client: SupabaseClient

    init(configuration: SupabaseConfiguration) {
        client = SupabaseClient(supabaseURL: configuration.url, supabaseKey: configuration.anonKey)
    }

    /// A valid access token (refreshed if it's about to expire), or nil when nobody is signed in.
    /// Other failures (e.g. offline during a refresh) are thrown so they aren't mistaken for a sign-out.
    func accessToken() async throws -> String? {
        do { return try await client.auth.session.accessToken }
        catch AuthError.sessionMissing { return nil }
    }
}
