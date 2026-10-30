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
    var id = UUID()            // the server's page id once the page exists there
    var cellId: UUID?          // the server cell that holds this page's strokes (nil until first saved)
    var title = ""             // empty = untitled
    var template: PageTemplate = .blank
    var drawing = PKDrawing()
    var isLoaded = true        // false until the page's strokes have been fetched
}

final class Notebook: ObservableObject, Identifiable {
    let id: UUID
    @Published var title: String
    @Published var coverColor: Color
    @Published var pages: [NotePage]
    @Published var pagesLoaded: Bool
    /// Page count as the server reported it, for notebooks whose pages haven't been fetched yet.
    @Published var knownPageCount: Int

    var pageCount: Int { pagesLoaded ? pages.count : knownPageCount }

    init(id: UUID = UUID(), title: String, coverColor: Color, pages: [NotePage] = [NotePage()],
         pagesLoaded: Bool = true, knownPageCount: Int = 1) {
        self.id = id
        self.title = title
        self.coverColor = coverColor
        self.pages = pages
        self.pagesLoaded = pagesLoaded
        self.knownPageCount = knownPageCount
    }
}

final class Folder: ObservableObject, Identifiable {
    let id: UUID
    let isRoot: Bool           // the library root exists only locally; on the server it is "parent = nil"
    @Published var name: String
    @Published var folders: [Folder]
    @Published var notebooks: [Notebook]
    @Published var isLoaded: Bool

    init(id: UUID = UUID(), name: String, folders: [Folder] = [], notebooks: [Notebook] = [],
         isRoot: Bool = false, isLoaded: Bool = true) {
        self.id = id
        self.name = name
        self.folders = folders
        self.notebooks = notebooks
        self.isRoot = isRoot
        self.isLoaded = isLoaded
    }
}

extension Color {
    /// "#RRGGBB" or "#RRGGBBAA"; anything unparseable becomes black.
    init(hex: String) {
        self = Color(StrokeCodec.color(fromHex: hex))
    }

    var hexString: String { StrokeCodec.hex(UIColor(self)) }
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
