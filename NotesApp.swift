import SwiftUI

@main
struct NotesApp: App {
    // In-memory only: changes made during the demo reset when the app restarts.
    @StateObject private var root = SampleData.makeLibrary()

    var body: some Scene {
        WindowGroup {
            NavigationStack {
                FolderView(folder: root)
                    .navigationDestination(for: Folder.self) { FolderView(folder: $0) }
                    .navigationDestination(for: Notebook.self) { EditorView(notebook: $0) }
            }
            .preferredColorScheme(.light)
        }
    }
}
