# iOS app (SwiftUI + PencilKit)

A native iPad/iPhone notetaking app: a library of folders and notebooks, and an editor with a real
PencilKit canvas (pen, marker, eraser, lasso, colors via Apple's tool picker), paper templates,
and a page strip. Users sign in with Supabase, and the library, pages and ink are stored through the
backend API (see "Backend connection" below). It has not been built yet (written on a PC with no Swift
toolchain), so expect to fix a few compiler errors on first build.

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

## Backend connection (`Networking/`)

The HTTP calls the client makes are exercised by `backend/scripts/smoke_test.py` (HS256 and Supabase-style ES256/JWKS).

1. Drag the `Networking/` and `Auth/` folders into the Xcode project, like the other sources.
2. Add the Supabase Swift SDK: File > Add Package Dependencies > `https://github.com/supabase/supabase-swift`
   (2.x), and add the `Supabase` product to the `Notes` target.
3. In Info.plist add:
   - `SUPABASE_URL`: `https://<project-ref>.supabase.co`
   - `SUPABASE_ANON_KEY`: the project's anon/publishable key (public by design, safe to ship)
   - `DEVPAD_API_URL`: the backend, default `http://localhost:8000`. The simulator reaches the Mac at
     localhost. A real iPad needs the Mac's LAN IP plus an App Transport Security exception for http,
     or a deployed https URL.
4. In Supabase: Authentication > Providers > Email. For quick testing turn off "Confirm email", or confirm
   from the email link after signing up.
5. Configure the backend for the same project (see `backend/README.md`, "Supabase").

How it fits together: `NotesApp` shows `SignInView` until `AuthStore` reports a session, then builds a
`LibraryStore` (one per sign-in) around an `APIClient` whose token comes from the Supabase SDK, which
refreshes it automatically. The views call `LibraryStore`, which applies changes on the server first and
the screen second. Drawing autosaves about a second after the last stroke, and again when you leave the
editor or the app goes to the background.

Things to know:
- The library is not one nested tree on the server: `listFolders(parentId:)` and `listNotebooks(folderId:)`
  return one level at a time (nil = library root). A folder's contents load when it is opened.
- A page's ink is stored as strokes in the page's first `ink` cell. Other cells (typed text, code) are ignored
  for now. Pages have optional titles (More menu > Rename page), shown under the thumbnails.
- Notebook cover thumbnails show blank paper until the notebook has been opened in this session.
- Ink is converted to simple strokes (position, time, pressure, color, width). Pencil tilt and the exact ink
  type are not stored: marker comes back as a marker, every other pen as a pen.
- A page holds at most 5,000 strokes and ~5 MB per save.

| File | What it does |
|---|---|
| `Networking/APIConfiguration.swift` | Base URL, token provider, timeout |
| `Networking/APIClient.swift` | One method per endpoint, bearer auth, 429 retry, error mapping |
| `Networking/APIModels.swift` | Wire types and request bodies (`Patch` sends explicit `null`) |
| `Networking/APIError.swift` | Status codes mapped to `APIError`, FastAPI error body parsing |
| `Networking/StrokeCodec.swift` | `PKDrawing` <-> API strokes |
| `Networking/LibraryStore.swift` | Loads and changes the library through the API, debounced autosave |
| `Auth/AuthService.swift` | Supabase SDK wrapper, Info.plist settings, access token |
| `Auth/AuthStore.swift` | Sign-in state for the UI |
| `Auth/SignInView.swift` | Email + password sign-in / sign-up screen |

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
