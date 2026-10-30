import SwiftUI

@main
struct NotesApp: App {
    @StateObject private var auth = AuthStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(auth)
                .preferredColorScheme(.light)
        }
    }
}

/// Sign-in gate: shows the sign-in form, or the library once someone is signed in.
struct RootView: View {
    @EnvironmentObject private var auth: AuthStore

    var body: some View {
        Group {
            switch auth.state {
            case .loading: ProgressView()
            case .signedOut: SignInView()
            case .signedIn: LibraryHost(auth: auth)
            }
        }
        .task { await auth.start() }
    }
}

/// One library session. A new `LibraryStore` (and API client) exists for each sign-in, so a different
/// user never sees the previous user's data.
struct LibraryHost: View {
    @StateObject private var store: LibraryStore
    @EnvironmentObject private var auth: AuthStore

    init(auth: AuthStore) {
        _store = StateObject(wrappedValue: LibraryStore(api: auth.makeAPIClient()))
    }

    var body: some View {
        NavigationStack {
            FolderView(folder: store.root)
                .navigationDestination(for: Folder.self) { FolderView(folder: $0) }
                .navigationDestination(for: Notebook.self) { EditorView(notebook: $0) }
        }
        .environmentObject(store)
        .onAppear { store.onUnauthorized = { Task { await auth.signOut() } } }
        .alert("Something went wrong", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(store.errorMessage ?? "")
        }
    }
}
