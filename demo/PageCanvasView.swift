import SwiftUI
import PencilKit

/// Lets the toolbar reach the active PencilKit canvas (for undo/redo).
final class CanvasController: ObservableObject {
    weak var canvas: PKCanvasView?
    func undo() { canvas?.undoManager?.undo() }
    func redo() { canvas?.undoManager?.redo() }
}

/// A PencilKit canvas for one page. The canvas is created once per page (the editor gives it
/// `.id(page.id)`), so the drawing only flows from the canvas up to the binding.
struct PageCanvasView: UIViewRepresentable {
    @Binding var drawing: PKDrawing
    let controller: CanvasController

    func makeUIView(context: Context) -> PKCanvasView {
        let canvas = PKCanvasView()
        canvas.drawing = drawing
        canvas.drawingPolicy = .anyInput   // lets you draw with a finger/mouse in the demo; use .pencilOnly later
        canvas.backgroundColor = .clear
        canvas.isOpaque = false
        canvas.overrideUserInterfaceStyle = .light
        canvas.isScrollEnabled = false
        canvas.delegate = context.coordinator

        let picker = PKToolPicker()
        picker.addObserver(canvas)
        picker.setVisible(true, forFirstResponder: canvas)
        context.coordinator.toolPicker = picker

        controller.canvas = canvas
        DispatchQueue.main.async { canvas.becomeFirstResponder() }
        return canvas
    }

    func updateUIView(_ canvas: PKCanvasView, context: Context) {
        context.coordinator.parent = self
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, PKCanvasViewDelegate {
        var parent: PageCanvasView
        var toolPicker: PKToolPicker?

        init(_ parent: PageCanvasView) { self.parent = parent }

        func canvasViewDrawingDidChange(_ canvasView: PKCanvasView) {
            parent.drawing = canvasView.drawing
        }
    }
}
