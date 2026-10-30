import SwiftUI

struct NewNotebookSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var title = "Untitled"
    @State private var color = NotebookPalette.colors[0]
    @State private var template: PageTemplate = .lined

    /// Called with the chosen title, cover color and first-page paper; the caller creates the notebook.
    let onCreate: (String, Color, PageTemplate) -> Void

    var body: some View {
        NavigationStack {
            Form {
                TextField("Title", text: $title)
                Section("Cover") {
                    HStack(spacing: 14) {
                        ForEach(NotebookPalette.colors, id: \.self) { c in
                            Circle()
                                .fill(c)
                                .frame(width: 32, height: 32)
                                .overlay(Circle().stroke(Color.primary, lineWidth: c == color ? 3 : 0))
                                .onTapGesture { color = c }
                        }
                    }
                    .padding(.vertical, 4)
                }
                Section("Paper") {
                    Picker("Paper", selection: $template) {
                        ForEach(PageTemplate.allCases) { t in
                            Text(t.label).tag(t)
                        }
                    }
                    .pickerStyle(.segmented)
                }
            }
            .navigationTitle("New notebook")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Create") {
                        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
                        onCreate(trimmed.isEmpty ? "Untitled" : trimmed, color, template)
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }
}
