# iOS app (SwiftUI + PencilKit)

A native iPad/iPhone notetaking app: a library of folders and notebooks, and an editor with a real
PencilKit canvas (pen, marker, eraser, lasso, colors via Apple's tool picker), paper templates,
and a page strip. Everything is in memory with sample content; it doesn't talk to the backend yet.

Requires a Mac with Xcode 15 or newer. Deployment target: iOS 16.0 or newer.

## One-time setup

1. In Xcode: File > New > Project > iOS > App. Name it `Notes`, Interface: SwiftUI,
   Language: Swift, Storage: None. Save it inside this `ios/` folder.
2. Delete the two default files Xcode created (`ContentView.swift` and `NotesApp.swift`;
   choose Move to Trash).
3. In the project's General tab, set Minimum Deployments to iOS 16.0.
4. Drag every file from `ios/Sources/` into the Xcode project navigator. Leave "Copy items if needed"
   unchecked so the files stay in the repo folder, choose "Create groups", and make sure the `Notes`
   target is ticked.

## Run

- Pick an iPad simulator (for example iPad Pro 11-inch) and press Run (Cmd+R). In the simulator you
  can draw with the mouse because the canvas accepts any input.
- On a real iPad with an Apple Pencil: plug it in, select it as the run destination, and set your
  Team under Signing & Capabilities (a free Apple ID works; the install expires after about 7 days).
- For the real app, change `canvas.drawingPolicy = .anyInput` to `.pencilOnly` in
  `PageCanvasView.swift` so fingers don't draw.

## Files

| File | What it does |
|---|---|
| `NotesApp.swift` | App entry, navigation, holds the mock library |
| `Models.swift` | Folder / Notebook / NotePage (a page holds a PencilKit `PKDrawing`) |
| `SampleData.swift` | Fake handwritten sample pages built from real PencilKit strokes |
| `PaperView.swift` | Paper templates and the page thumbnail view |
| `PageCanvasView.swift` | PencilKit canvas wrapper + tool picker |
| `FolderView.swift` | Folder/notebook grid |
| `EditorView.swift` | Page canvas, toolbar, page strip |
| `NewNotebookSheet.swift` | New-notebook sheet |
