import SwiftUI

/// Library screen: a grid of folders and notebooks. Used for the root and for every sub-folder.
struct FolderView: View {
    @ObservedObject var folder: Folder

    @State private var showNewNotebook = false
    @State private var showNewFolder = false
    @State private var showRenameFolder = false
    @State private var showRenameNotebook = false
    @State private var renameFolderTarget: Folder?
    @State private var renameNotebookTarget: Notebook?
    @State private var nameDraft = ""

    private let columns = [GridItem(.adaptive(minimum: 160), spacing: 24, alignment: .top)]

    var body: some View {
        ScrollView {
            if folder.folders.isEmpty && folder.notebooks.isEmpty {
                Text("Nothing here yet. Tap + to create a notebook.")
                    .foregroundColor(.secondary)
                    .padding(.top, 80)
            }
            LazyVGrid(columns: columns, spacing: 28) {
                ForEach(folder.folders) { f in
                    NavigationLink(value: f) { FolderCard(folder: f) }
                        .buttonStyle(.plain)
                        .contextMenu {
                            Button("Rename") {
                                nameDraft = f.name
                                renameFolderTarget = f
                                showRenameFolder = true
                            }
                            Button("Delete", role: .destructive) {
                                folder.folders.removeAll { $0.id == f.id }
                            }
                        }
                }
                ForEach(folder.notebooks) { nb in
                    NavigationLink(value: nb) { NotebookCard(notebook: nb) }
                        .buttonStyle(.plain)
                        .contextMenu {
                            Button("Rename") {
                                nameDraft = nb.title
                                renameNotebookTarget = nb
                                showRenameNotebook = true
                            }
                            Button("Delete", role: .destructive) {
                                folder.notebooks.removeAll { $0.id == nb.id }
                            }
                        }
                }
            }
            .padding(24)
        }
        .navigationTitle(folder.name)
        .toolbar {
            ToolbarItemGroup(placement: .navigationBarTrailing) {
                Button {
                    nameDraft = ""
                    showNewFolder = true
                } label: { Image(systemName: "folder.badge.plus") }
                Button { showNewNotebook = true } label: { Image(systemName: "plus") }
            }
        }
        .sheet(isPresented: $showNewNotebook) {
            NewNotebookSheet { folder.notebooks.append($0) }
        }
        .alert("New folder", isPresented: $showNewFolder) {
            TextField("Name", text: $nameDraft)
            Button("Create") {
                let n = nameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                if !n.isEmpty { folder.folders.append(Folder(name: n)) }
            }
            Button("Cancel", role: .cancel) {}
        }
        .alert("Rename folder", isPresented: $showRenameFolder) {
            TextField("Name", text: $nameDraft)
            Button("Save") {
                let n = nameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                if !n.isEmpty { renameFolderTarget?.name = n }
            }
            Button("Cancel", role: .cancel) {}
        }
        .alert("Rename notebook", isPresented: $showRenameNotebook) {
            TextField("Name", text: $nameDraft)
            Button("Save") {
                let n = nameDraft.trimmingCharacters(in: .whitespacesAndNewlines)
                if !n.isEmpty { renameNotebookTarget?.title = n }
            }
            Button("Cancel", role: .cancel) {}
        }
    }
}

struct FolderCard: View {
    @ObservedObject var folder: Folder

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color(red: 1.0, green: 0.88, blue: 0.51))
                Image(systemName: "folder.fill")
                    .font(.system(size: 56))
                    .foregroundColor(Color(red: 0.98, green: 0.66, blue: 0.15))
            }
            .aspectRatio(PageSize.ratio, contentMode: .fit)
            Text(folder.name).fontWeight(.semibold).lineLimit(1)
            Text("\(folder.folders.count + folder.notebooks.count) items")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

struct NotebookCard: View {
    @ObservedObject var notebook: Notebook

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 0) {
                Rectangle().fill(notebook.coverColor).frame(width: 8)
                if let first = notebook.pages.first {
                    PageThumbnail(page: first)
                }
            }
            .aspectRatio(PageSize.ratio, contentMode: .fit)
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .shadow(color: .black.opacity(0.2), radius: 6, y: 3)
            Text(notebook.title).fontWeight(.semibold).lineLimit(1)
            Text(notebook.pages.count == 1 ? "1 page" : "\(notebook.pages.count) pages")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}
