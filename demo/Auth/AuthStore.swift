import Foundation
import Supabase

/// Sign-in state for the UI.
@MainActor
final class AuthStore: ObservableObject {
    enum State: Equatable {
        case loading
        case signedOut
        case signedIn(email: String?)
    }

    @Published private(set) var state: State = .loading
    @Published private(set) var isWorking = false
    @Published var message: String?

    /// nil when Info.plist has no Supabase settings.
    let service: AuthService?

    init() {
        service = SupabaseConfiguration.fromBundle().map(AuthService.init)
    }

    var isConfigured: Bool { service != nil }

    /// Follows the SDK's session changes for the life of the app (call from `.task`).
    func start() async {
        guard let service else {
            state = .signedOut
            message = "Add SUPABASE_URL and SUPABASE_ANON_KEY to Info.plist."
            return
        }
        for await (event, session) in service.client.auth.authStateChanges {
            switch event {
            case .initialSession, .signedIn, .tokenRefreshed, .userUpdated:
                state = session != nil ? .signedIn(email: session?.user.email) : .signedOut
            case .signedOut:
                state = .signedOut
            default:
                break
            }
        }
    }

    func signIn(email: String, password: String) async {
        await run {
            try await $0.client.auth.signIn(email: email, password: password)
        }
    }

    func signUp(email: String, password: String) async {
        await run { service in
            let result = try await service.client.auth.signUp(email: email, password: password)
            if result.session == nil {
                self.message = "Check your email to confirm your account, then sign in."
            }
        }
    }

    func signOut() async {
        await run { try await $0.client.auth.signOut() }
    }

    /// A client whose requests carry the current user's token.
    func makeAPIClient() -> APIClient {
        let service = self.service
        let configuration = APIConfiguration.fromBundle { try await service?.accessToken() }
        return APIClient(configuration: configuration)
    }

    private func run(_ work: (AuthService) async throws -> Void) async {
        guard let service else { return }
        isWorking = true
        message = nil
        defer { isWorking = false }
        do { try await work(service) }
        catch { message = error.localizedDescription }
    }
}
