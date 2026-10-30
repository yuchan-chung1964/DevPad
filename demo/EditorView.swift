import SwiftUI
import PencilKit

/// Notebook editor: one PencilKit canvas per page on top of the paper template,
/// plus a page strip along the bottom. Pages and strokes load from the backend on demand,
/// and drawing autosaves.
struct EditorView: View {
    @ObservedObject var notebook: Notebook
    @EnvironmentObject private var store: LibraryStore
    @Environment(\.scenePhase) private var scenePhase

    @State private var pageIndex = 0
    @StateObject private var controller = CanvasController()
    @State private var showRename = false
    @State private var showRenamePage = false
    @State private var titleDraft = ""

    private var ready: Bool { notebook.pagesLoaded && !notebook.pages.isEmpty }
    private var safeIndex: Int { max(0, min(pageIndex, notebook.pages.count - 1)) }
    private var currentPageId: UUID? { ready ? notebook.pages[safeIndex].id : nil }

    var body: some View {
        Group {
            if ready {
                VStack(spacing: 0) {
                    GeometryReader { geo in
                        let pad: CGFloat = 16
                        let scale = max(0.1, min((geo.size.width - pad * 2) / PageSize.width,
                                                 (geo.size.height - pad * 2) / PageSize.height))
                        pageCanvas(scale: scale)
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                    .background(Color(white: 0.93))
                    Divider()
                    PageStrip(notebook: notebook, pageIndex: $pageIndex, onAdd: addPage)
                }
            } else {
                ProgressView().frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .navigationTitle(notebook.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await store.loadPages(notebook) }
        .task(id: currentPageId) {
            if let id = currentPageId { await store.loadPage(notebook, pageId: id) }
        }
        .onDisappear { Task { await store.flush(notebook) } }
        .onChange(of: scenePhase) { phase in
            if phase != .active { Task { await store.flush(notebook) } }
        }
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                Button { controller.undo() } label: { Image(systemName: "arrow.uturn.backward") }
                Button { controller.redo() } label: { Image(systemName: "arrow.uturn.forward") }
                Menu {
                    Picker("Paper", selection: templateBinding) {
                        ForEach(PageTemplate.allCases) { t in
                            Text(t.label).tag(t)
                        }
                    }
                } label: { Image(systemName: "square.grid.3x3") }
                    .disabled(!ready)
                Button(action: addPage) { Image(systemName: "doc.badge.plus") }
                    .disabled(!ready)
                Button(role: .destructive, action: deletePage) { Image(systemName: "trash") }
                    .disabled(!ready || notebook.pages.count <= 1)
                Menu {
                    Button("Rename notebook") {
                        titleDraft = notebook.title
                        showRename = true
                    }
                    Button("Rename page") {
                        titleDraft = ready ? notebook.pages[safeIndex].title : ""
                        showRenamePage = true
                    }
                    .disabled(!ready)
                } label: { Image(systemName: "ellipsis.circle") }
            }
        }
        .alert("Rename notebook", isPresented: $showRename) {
            TextField("Name", text: $titleDraft)
            Button("Save") {
                let n = titleDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                if !n.isEmpty { Task { await store.renameNotebook(notebook, to: n) } }
            }
            Button("Cancel", role: .cancel) {}
        }
        .alert("Rename page", isPresented: $showRenamePage) {
            TextField("Title", text: $titleDraft)   // an empty title makes the page untitled again
            Button("Save") {
                if let id = currentPageId {
                    let t = titleDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                    Task { await store.renamePage(id, to: t, in: notebook) }
                }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    @ViewBuilder
    private func pageCanvas(scale: CGFloat) -> some View {
        let page = notebook.pages[safeIndex]
        let pageId = page.id
        ZStack {
            PaperView(template: page.template)
            if page.isLoaded {
                PageCanvasView(
                    drawing: Binding(
                        get: { notebook.pages.first { $0.id == pageId }?.drawing ?? PKDrawing() },
                        set: { newDrawing in
                            guard let i = notebook.pages.firstIndex(where: { $0.id == pageId }) else { return }
                            notebook.pages[i].drawing = newDrawing
                            store.drawingChanged(in: notebook, pageId: pageId)
                        }
                    ),
                    controller: controller
                )
            } else if store.failedPages.contains(pageId) {
                VStack(spacing: 12) {
                    Text("Couldn't load this page").foregroundColor(.secondary)
                    Button("Retry") { Task { await store.loadPage(notebook, pageId: pageId) } }
                }
            } else {
                ProgressView()
            }
        }
        .frame(width: PageSize.width, height: PageSize.height)
        .scaleEffect(scale, anchor: .topLeading)
        .frame(width: PageSize.width * scale, height: PageSize.height * scale, alignment: .topLeading)
        .shadow(color: .black.opacity(0.25), radius: 8)
        .id(pageId) // new canvas (and undo history) per page
    }

    private var templateBinding: Binding<PageTemplate> {
        Binding(
            get: { ready ? notebook.pages[safeIndex].template : .blank },
            set: { newValue in
                if let id = currentPageId { store.setTemplate(newValue, for: id, in: notebook) }
            }
        )
    }

    private func addPage() {
        guard ready else { return }
        let template = notebook.pages[safeIndex].template
        let at = safeIndex + 1
        Task {
            if let landed = await store.addPage(to: notebook, at: at, template: template) { pageIndex = landed }
        }
    }

    private func deletePage() {
        guard let id = currentPageId else { return }
        Task {
            if await store.deletePage(from: notebook, pageId: id) {
                pageIndex = max(0, min(pageIndex, notebook.pages.count - 1))
            }
        }
    }
}

struct PageStrip: View {
    @ObservedObject var notebook: Notebook
    @Binding var pageIndex: Int
    let onAdd: () -> Void

    private let thumbWidth: CGFloat = 64

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(alignment: .top, spacing: 12) {
                ForEach(Array(notebook.pages.enumerated()), id: \.element.id) { index, page in
                    let selected = index == pageIndex
                    VStack(spacing: 2) {
                        PageThumbnail(page: page)
                            .frame(width: thumbWidth, height: thumbWidth / PageSize.ratio)
                            .overlay(
                                Rectangle().stroke(selected ? Color.accentColor : Color.black.opacity(0.2),
                                                   lineWidth: selected ? 3 : 1)
                            )
                            .onTapGesture { pageIndex = index }
                        Text(page.title.isEmpty ? "\(index + 1)" : page.title)
                            .font(.caption)
                            .lineLimit(1)
                            .frame(width: thumbWidth)
                    }
                }
                Button(action: onAdd) {
                    Image(systemName: "plus")
                        .frame(width: thumbWidth, height: thumbWidth / PageSize.ratio)
                        .background(Color(white: 0.93))
                        .cornerRadius(4)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        .background(Color.white)
    }
}
