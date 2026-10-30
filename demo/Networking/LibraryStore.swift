import SwiftUI
import PencilKit

/// Owns the library: loads it from the backend, applies changes there, and autosaves drawings.
///
/// Folders and notebooks load one level at a time (`loadFolder`), a notebook's pages load when it is opened
/// (`loadPages`), and a page's strokes load when it is shown (`loadPage`). Creates, renames and deletes are applied
/// locally only after the server accepts them; drawing is saved ~1s after the last stroke.
///
/// A page's ink lives in the page's first cell of kind `ink`. Other cells (typed text, code blocks from other
/// clients) are left untouched.
@MainActor
final class LibraryStore: ObservableObject {
    /// The library root. It exists only locally; on the server, root items have no parent.
    let root = Folder(name: "Library", isRoot: true, isLoaded: false)

    @Published var errorMessage: String?
    /// Pages whose strokes failed to load, so the editor can offer a retry.
    @Published private(set) var failedPages: Set<UUID> = []
    var onUnauthorized: (() -> Void)?

    private let api: APIClient
    private let saveDelay: UInt64
    private var saveTimers: [UUID: Task<Void, Never>] = [:]
    private var saving: Set<UUID> = []
    private var dirty: Set<UUID> = []
    private var pageOwners: [UUID: Notebook] = [:]

    private static let pageSize = 500

    init(api: APIClient, saveDelay: TimeInterval = 1) {
        self.api = api
        self.saveDelay = UInt64(saveDelay * 1_000_000_000)
    }

    // MARK: - Folders and notebooks

    func loadFolder(_ folder: Folder) async {
        let parent = folder.isRoot ? nil : folder.id
        do {
            let subfolders = try await allPages { try await self.api.listFolders(parentId: parent, limit: Self.pageSize, offset: $0) }
            let notebooks = try await allPages { try await self.api.listNotebooks(folderId: parent, limit: Self.pageSize, offset: $0) }

            // Reuse existing objects so navigation values and loaded state survive a refresh.
            let knownFolders = Dictionary(folder.folders.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
            folder.folders = subfolders.map { dto in
                let f = knownFolders[dto.id] ?? Folder(id: dto.id, name: dto.name, isLoaded: false)
                f.name = dto.name
                return f
            }
            let knownNotebooks = Dictionary(folder.notebooks.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
            folder.notebooks = notebooks.map { dto in
                let nb = knownNotebooks[dto.id] ?? Notebook(
                    id: dto.id, title: dto.title, coverColor: Color(hex: dto.coverColor),
                    pages: [], pagesLoaded: false, knownPageCount: dto.pageOrder.count)
                nb.title = dto.title
                nb.coverColor = Color(hex: dto.coverColor)
                if !nb.pagesLoaded { nb.knownPageCount = dto.pageOrder.count }
                return nb
            }
            folder.isLoaded = true
        } catch {
            report(error)
        }
    }

    func createFolder(named name: String, in parent: Folder) async {
        await perform {
            let dto = try await self.api.createFolder(FolderCreate(name: name, parentId: parent.isRoot ? nil : parent.id))
            parent.folders.append(Folder(id: dto.id, name: dto.name))
        }
    }

    func renameFolder(_ folder: Folder, to name: String) async {
        await perform {
            let dto = try await self.api.updateFolder(folder.id, FolderUpdate(name: name))
            folder.name = dto.name
        }
    }

    /// Only empty folders can be deleted; the server's 409 is shown as an error.
    func deleteFolder(_ folder: Folder, from parent: Folder) async {
        await perform {
            try await self.api.deleteFolder(folder.id)
            parent.folders.removeAll { $0.id == folder.id }
        }
    }

    func createNotebook(title: String, color: Color, template: PageTemplate, in parent: Folder) async {
        await perform {
            let dto = try await self.api.createNotebook(NotebookCreate(
                title: title,
                folderId: parent.isRoot ? nil : parent.id,
                coverColor: color.hexString,
                template: Self.apiTemplate(template)))
            let firstPage = dto.pageOrder.first.map { [NotePage(id: $0, template: template)] } ?? []
            parent.notebooks.append(Notebook(
                id: dto.id, title: dto.title, coverColor: color, pages: firstPage,
                pagesLoaded: !firstPage.isEmpty, knownPageCount: dto.pageOrder.count))
        }
    }

    func renameNotebook(_ notebook: Notebook, to title: String) async {
        await perform {
            let dto = try await self.api.updateNotebook(notebook.id, NotebookUpdate(title: title))
            notebook.title = dto.title
        }
    }

    func deleteNotebook(_ notebook: Notebook, from parent: Folder) async {
        await perform {
            try await self.api.deleteNotebook(notebook.id)
            for page in notebook.pages { self.forget(page.id) }
            parent.notebooks.removeAll { $0.id == notebook.id }
        }
    }

    // MARK: - Pages

    /// Fetches the notebook's page list (no strokes yet) the first time it is opened.
    func loadPages(_ notebook: Notebook) async {
        guard !notebook.pagesLoaded else { return }
        do {
            let dto = try await api.notebook(notebook.id)
            let summaries = try await api.listPages(notebookId: notebook.id)
            let byId = Dictionary(summaries.map { ($0.id, $0) }, uniquingKeysWith: { a, _ in a })
            notebook.pages = dto.pageOrder.compactMap { id in
                byId[id].map { NotePage(id: id, title: $0.title, template: Self.template($0.template), isLoaded: false) }
            }
            notebook.pagesLoaded = true
        } catch {
            report(error)
        }
    }

    /// Fetches one page's strokes. The editor shows the canvas only once `isLoaded` is true.
    func loadPage(_ notebook: Notebook, pageId: UUID) async {
        guard let i = notebook.pages.firstIndex(where: { $0.id == pageId }), !notebook.pages[i].isLoaded else { return }
        failedPages.remove(pageId)
        do {
            let dto = try await api.page(notebookId: notebook.id, pageId: pageId)
            guard let j = notebook.pages.firstIndex(where: { $0.id == pageId }) else { return }  // deleted meanwhile
            let cell = dto.cells.first { $0.kind == .ink }
            notebook.pages[j].cellId = cell?.id
            notebook.pages[j].title = dto.title
            notebook.pages[j].template = Self.template(dto.template)
            notebook.pages[j].drawing = StrokeCodec.drawing(from: cell?.strokes ?? [])
            notebook.pages[j].isLoaded = true
        } catch {
            failedPages.insert(pageId)
            report(error)
        }
    }

    /// Inserts a blank page at `index` and returns where it landed, or nil if the server refused.
    func addPage(to notebook: Notebook, at index: Int, template: PageTemplate) async -> Int? {
        var landed: Int?
        await perform {
            let at = min(max(index, 0), notebook.pages.count)
            let dto = try await self.api.createPage(notebookId: notebook.id, PageCreate(template: Self.apiTemplate(template), position: at))
            let insertAt = min(at, notebook.pages.count)
            notebook.pages.insert(NotePage(id: dto.id, template: template), at: insertAt)
            landed = insertAt
        }
        return landed
    }

    /// A notebook must keep at least one page; the server enforces it too.
    func deletePage(from notebook: Notebook, pageId: UUID) async -> Bool {
        guard notebook.pages.count > 1 else { return false }
        saveTimers[pageId]?.cancel()
        var deleted = false
        await perform {
            try await self.api.deletePage(notebookId: notebook.id, pageId: pageId)
            notebook.pages.removeAll { $0.id == pageId }
            self.forget(pageId)
            deleted = true
        }
        return deleted
    }

    func renamePage(_ pageId: UUID, to title: String, in notebook: Notebook) async {
        await perform {
            let dto = try await self.api.updatePage(notebookId: notebook.id, pageId: pageId, PageUpdate(title: title))
            if let i = notebook.pages.firstIndex(where: { $0.id == pageId }) { notebook.pages[i].title = dto.title }
        }
    }

    /// Optimistic: the paper changes immediately and reverts if the server refuses.
    func setTemplate(_ template: PageTemplate, for pageId: UUID, in notebook: Notebook) {
        guard let i = notebook.pages.firstIndex(where: { $0.id == pageId }) else { return }
        let previous = notebook.pages[i].template
        notebook.pages[i].template = template
        Task {
            do { _ = try await api.updatePage(notebookId: notebook.id, pageId: pageId, PageUpdate(template: Self.apiTemplate(template))) }
            catch {
                if let j = notebook.pages.firstIndex(where: { $0.id == pageId }) { notebook.pages[j].template = previous }
                report(error)
            }
        }
    }

    // MARK: - Autosave

    /// Call whenever the canvas changes; the page is saved after `saveDelay` of quiet.
    func drawingChanged(in notebook: Notebook, pageId: UUID) {
        pageOwners[pageId] = notebook
        saveTimers[pageId]?.cancel()
        saveTimers[pageId] = Task { [weak self, saveDelay] in
            try? await Task.sleep(nanoseconds: saveDelay)
            guard !Task.isCancelled else { return }
            await self?.save(pageId: pageId)
        }
    }

    /// Saves any pending drawing right now (leaving the editor, app going to the background).
    func flush(_ notebook: Notebook) async {
        let pending = notebook.pages.map(\.id).filter { saveTimers[$0] != nil || dirty.contains($0) || saving.contains($0) }
        for id in pending {
            saveTimers[id]?.cancel()
            await save(pageId: id)
            var waited = 0
            while saving.contains(id), waited < 100 {   // wait up to ~5s for an in-flight save
                try? await Task.sleep(nanoseconds: 50_000_000)
                waited += 1
            }
        }
    }

    private func save(pageId: UUID) async {
        saveTimers[pageId] = nil
        if saving.contains(pageId) { dirty.insert(pageId); return }   // the running save will go again
        saving.insert(pageId)
        defer { saving.remove(pageId) }

        repeat {
            dirty.remove(pageId)
            guard let notebook = pageOwners[pageId], let i = notebook.pages.firstIndex(where: { $0.id == pageId }) else { return }
            let page = notebook.pages[i]
            let strokes = StrokeCodec.apiStrokes(from: page.drawing)
            do {
                if let cellId = page.cellId {
                    _ = try await api.replaceStrokes(notebookId: notebook.id, pageId: pageId, cellId: cellId, strokes)
                } else if !strokes.isEmpty {
                    let cell = try await api.createCell(notebookId: notebook.id, pageId: pageId,
                                                        CellCreate(kind: .ink, language: "text", strokes: strokes))
                    if let j = notebook.pages.firstIndex(where: { $0.id == pageId }) { notebook.pages[j].cellId = cell.id }
                }
            } catch {
                report(error)
                if (error as? APIError)?.isTransient == true { scheduleRetry(pageId) }
                return
            }
        } while dirty.contains(pageId)
    }

    private func scheduleRetry(_ pageId: UUID) {
        saveTimers[pageId] = Task { [weak self] in
            try? await Task.sleep(nanoseconds: 5_000_000_000)
            guard !Task.isCancelled else { return }
            await self?.save(pageId: pageId)
        }
    }

    // MARK: - Helpers

    private func forget(_ pageId: UUID) {
        saveTimers[pageId]?.cancel()
        saveTimers[pageId] = nil
        dirty.remove(pageId)
        pageOwners[pageId] = nil
        failedPages.remove(pageId)
    }

    private func perform(_ work: () async throws -> Void) async {
        do { try await work() } catch { report(error) }
    }

    private func report(_ error: Error) {
        if error is CancellationError { return }
        if let api = error as? APIError, case .unauthorized = api { onUnauthorized?(); return }
        errorMessage = error.localizedDescription
    }

    private func allPages<T>(_ fetch: (Int) async throws -> [T]) async throws -> [T] {
        var all: [T] = []
        var offset = 0
        while true {
            let batch = try await fetch(offset)
            all += batch
            if batch.count < Self.pageSize { return all }
            offset += Self.pageSize
        }
    }

    private static func template(_ t: APITemplate) -> PageTemplate { PageTemplate(rawValue: t.rawValue) ?? .blank }
    private static func apiTemplate(_ t: PageTemplate) -> APITemplate { APITemplate(rawValue: t.rawValue) ?? .blank }
}
