import Foundation

// Wire types for the DevPad API. Property names are camelCase; APIClient converts to/from the
// backend's snake_case. Mirrors backend/app/schemas.py.

enum APITool: String, Codable { case pen, highlighter, eraser }
enum APITemplate: String, Codable { case blank, lined, grid, dotted }
/// What a cell is: code, typed text (the text is in `code`), or freehand ink. Fixed when the cell is created.
enum APICellKind: String, Codable { case code, text, ink }

struct APIPoint: Codable, Equatable {
    var x: Double
    var y: Double
    var t: Double = 0          // seconds since the stroke began
    var pressure: Double = 1   // 0...1 (the server rejects anything outside)
}

struct APIStroke: Codable, Identifiable, Equatable {
    var id: UUID = UUID()
    var points: [APIPoint]
    var tool: APITool = .pen
    var color: String = "#000000"   // #RRGGBB or #RRGGBBAA
    var width: Double = 2
}

struct APICell: Codable, Identifiable, Equatable {
    let id: UUID
    let pageId: UUID
    let kind: APICellKind
    var language: String
    var code: String
    var strokes: [APIStroke]
    let createdAt: Date
    let updatedAt: Date
}

struct APIPage: Codable, Identifiable, Equatable {
    let id: UUID
    let notebookId: UUID
    var title: String            // empty = untitled
    var template: APITemplate
    var cells: [APICell]
    let createdAt: Date
    let updatedAt: Date
}

struct APIPageSummary: Codable, Identifiable, Equatable {
    let id: UUID
    let notebookId: UUID
    var title: String
    var template: APITemplate
    var cellCount: Int
    let updatedAt: Date
}

struct APINotebook: Codable, Identifiable, Equatable {
    let id: UUID
    var folderId: UUID?          // nil = library root
    var title: String
    var coverColor: String       // "#RRGGBB"
    var pageOrder: [UUID]
    let createdAt: Date
    let updatedAt: Date
}

struct APIFolder: Codable, Identifiable, Equatable {
    let id: UUID
    var parentId: UUID?          // nil = library root
    var name: String
    let createdAt: Date
    let updatedAt: Date
}

// MARK: - Request bodies

struct FolderCreate: Encodable {
    var name: String
    var parentId: UUID?
}

struct NotebookCreate: Encodable {
    var title: String = "Untitled"
    var folderId: UUID?
    var coverColor: String = "#4A6FA5"
    var template: APITemplate = .blank
}

struct PageCreate: Encodable {
    var title: String = ""
    var template: APITemplate = .blank
    var position: Int?
}

struct CellCreate: Encodable {
    var kind: APICellKind = .code
    var language: String = "python"
    var code: String = ""
    var strokes: [APIStroke] = []
    var position: Int?
}

/// PATCH bodies. Omitted fields are left alone. For fields that can be moved to the library root,
/// `.set(nil)` sends an explicit JSON null, which is different from leaving the field out.
enum Patch<Value> {
    case unchanged
    case set(Value)
}

struct FolderUpdate: Encodable {
    var name: String?
    var parentId: Patch<UUID?> = .unchanged

    private enum CodingKeys: String, CodingKey { case name, parentId }
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encodeIfPresent(name, forKey: .name)
        if case .set(let v) = parentId { try c.encode(v, forKey: .parentId) }   // encodes null for nil
    }
}

struct NotebookUpdate: Encodable {
    var title: String?
    var folderId: Patch<UUID?> = .unchanged
    var coverColor: String?
    var pageOrder: [UUID]?       // the full new order

    private enum CodingKeys: String, CodingKey { case title, folderId, coverColor, pageOrder }
    func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encodeIfPresent(title, forKey: .title)
        if case .set(let v) = folderId { try c.encode(v, forKey: .folderId) }
        try c.encodeIfPresent(coverColor, forKey: .coverColor)
        try c.encodeIfPresent(pageOrder, forKey: .pageOrder)
    }
}

struct PageUpdate: Encodable {
    var title: String?
    var template: APITemplate?
    var cellOrder: [UUID]?       // the full new order
}

struct CellUpdate: Encodable {
    var language: String?
    var code: String?
}
