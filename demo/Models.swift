import SwiftUI
import PencilKit

/// Logical page size. Drawings live in these coordinates and the page is scaled to fit the screen.
enum PageSize {
    static let width: CGFloat = 820
    static let height: CGFloat = 1100
    static let ratio: CGFloat = width / height
}

enum PageTemplate: String, CaseIterable, Identifiable {
    case blank, lined, grid, dotted
    var id: String { rawValue }
    var label: String { rawValue.capitalized }
}

struct NotePage: Identifiable {
    let id = UUID()
    var template: PageTemplate = .blank
    var drawing = PKDrawing()
}

final class Notebook: ObservableObject, Identifiable {
    let id = UUID()
    @Published var title: String
    @Published var coverColor: Color
    @Published var pages: [NotePage]

    init(title: String, coverColor: Color, pages: [NotePage] = [NotePage()]) {
        self.title = title
        self.coverColor = coverColor
        self.pages = pages
    }
}

final class Folder: ObservableObject, Identifiable {
    let id = UUID()
    @Published var name: String
    @Published var folders: [Folder]
    @Published var notebooks: [Notebook]

    init(name: String, folders: [Folder] = [], notebooks: [Notebook] = []) {
        self.name = name
        self.folders = folders
        self.notebooks = notebooks
    }
}

// Hashable by identity so they can be used as NavigationStack values.
extension Folder: Hashable {
    static func == (lhs: Folder, rhs: Folder) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
}

extension Notebook: Hashable {
    static func == (lhs: Notebook, rhs: Notebook) -> Bool { lhs.id == rhs.id }
    func hash(into hasher: inout Hasher) { hasher.combine(id) }
}

enum NotebookPalette {
    static let colors: [Color] = [
        Color(red: 0.25, green: 0.32, blue: 0.71),
        Color(red: 0.00, green: 0.54, blue: 0.48),
        Color(red: 0.90, green: 0.22, blue: 0.21),
        Color(red: 0.98, green: 0.66, blue: 0.15),
        Color(red: 0.56, green: 0.14, blue: 0.67),
        Color(red: 0.27, green: 0.35, blue: 0.39),
    ]
}
