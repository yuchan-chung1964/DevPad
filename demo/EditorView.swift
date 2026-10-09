import SwiftUI
import PencilKit

/// Notebook editor: one PencilKit canvas per page on top of the paper template,
/// plus a page strip along the bottom.
struct EditorView: View {
    @ObservedObject var notebook: Notebook

    @State private var pageIndex = 0
    @StateObject private var controller = CanvasController()
    @State private var showRename = false
    @State private var titleDraft = ""

    private var safeIndex: Int { min(pageIndex, notebook.pages.count - 1) }

    var body: some View {
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
        .navigationTitle(notebook.title)
        .navigationBarTitleDisplayMode(.inline)
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
                Button(action: addPage) { Image(systemName: "doc.badge.plus") }
                Button(role: .destructive, action: deletePage) { Image(systemName: "trash") }
                    .disabled(notebook.pages.count <= 1)
                Menu {
                    Button("Rename") {
                        titleDraft = notebook.title
                        showRename = true
                    }
                } label: { Image(systemName: "ellipsis.circle") }
            }
        }
        .alert("Rename notebook", isPresented: $showRename) {
            TextField("Name", text: $titleDraft)
            Button("Save") {
                let n = titleDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                if !n.isEmpty { notebook.title = n }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    @ViewBuilder
    private func pageCanvas(scale: CGFloat) -> some View {
        let index = safeIndex
        let page = notebook.pages[index]
        ZStack {
            PaperView(template: page.template)
            PageCanvasView(
                drawing: Binding(
                    get: { index < notebook.pages.count ? notebook.pages[index].drawing : PKDrawing() },
                    set: { if index < notebook.pages.count { notebook.pages[index].drawing = $0 } }
                ),
                controller: controller
            )
        }
        .frame(width: PageSize.width, height: PageSize.height)
        .scaleEffect(scale, anchor: .topLeading)
        .frame(width: PageSize.width * scale, height: PageSize.height * scale, alignment: .topLeading)
        .shadow(color: .black.opacity(0.25), radius: 8)
        .id(page.id) // new canvas (and undo history) per page
    }

    private var templateBinding: Binding<PageTemplate> {
        Binding(
            get: { notebook.pages[safeIndex].template },
            set: { notebook.pages[safeIndex].template = $0 }
        )
    }

    private func addPage() {
        let newIndex = safeIndex + 1
        let template = notebook.pages[safeIndex].template
        notebook.pages.insert(NotePage(template: template), at: newIndex)
        pageIndex = newIndex
    }

    private func deletePage() {
        guard notebook.pages.count > 1 else { return }
        notebook.pages.remove(at: safeIndex)
        pageIndex = min(pageIndex, notebook.pages.count - 1)
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
                        Text("\(index + 1)").font(.caption)
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
