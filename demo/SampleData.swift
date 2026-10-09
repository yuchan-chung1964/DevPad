import SwiftUI
import PencilKit

/// Fake "handwritten" content built from real PencilKit strokes, so the demo looks lived-in.
enum SampleInk {
    static let ink = UIColor(red: 0.10, green: 0.14, blue: 0.49, alpha: 1)
    static let red = UIColor(red: 0.78, green: 0.16, blue: 0.16, alpha: 1)
    static let amber = UIColor(red: 1.0, green: 0.70, blue: 0.0, alpha: 1)

    private static func noise(_ i: Int) -> CGFloat {
        let x = sin(Double(i) * 12.9898) * 43758.5453
        return CGFloat(x - floor(x)) - 0.5
    }

    static func stroke(_ points: [CGPoint],
                       color: UIColor = ink,
                       width: CGFloat = 3,
                       inkType: PKInk.InkType = .pen) -> PKStroke {
        let controlPoints = points.enumerated().map { i, p in
            PKStrokePoint(location: p,
                          timeOffset: TimeInterval(i) * 0.01,
                          size: CGSize(width: width, height: width),
                          opacity: 1,
                          force: 1,
                          azimuth: 0,
                          altitude: .pi / 2)
        }
        let path = PKStrokePath(controlPoints: controlPoints, creationDate: Date())
        return PKStroke(ink: PKInk(inkType, color: color), path: path)
    }

    static func wave(x: CGFloat, y: CGFloat, length: CGFloat,
                     color: UIColor = ink, width: CGFloat = 3) -> PKStroke {
        var pts: [CGPoint] = []
        var dx: CGFloat = 0
        while dx <= length {
            let dy = sin(dx * 0.28) * 4 + sin(dx * 0.11) * 2 + noise(Int(x + dx + y)) * 1.5
            pts.append(CGPoint(x: x + dx, y: y + dy))
            dx += 3
        }
        return stroke(pts, color: color, width: width)
    }

    /// A line of squiggly "words" separated by gaps.
    static func textLine(x: CGFloat, y: CGFloat, words: [CGFloat],
                         color: UIColor = ink, width: CGFloat = 3) -> [PKStroke] {
        var out: [PKStroke] = []
        var cx = x
        for w in words {
            out.append(wave(x: cx, y: y, length: w, color: color, width: width))
            cx += w + 16
        }
        return out
    }

    static func circle(center: CGPoint, rx: CGFloat, ry: CGFloat, color: UIColor) -> PKStroke {
        var pts: [CGPoint] = []
        var a: CGFloat = 0
        while a <= .pi * 2.1 {
            pts.append(CGPoint(x: center.x + cos(a) * rx, y: center.y + sin(a) * ry))
            a += 0.15
        }
        return stroke(pts, color: color)
    }

    static func line(_ a: CGPoint, _ b: CGPoint, color: UIColor, width: CGFloat = 3) -> PKStroke {
        let steps = 14
        let pts = (0...steps).map { i -> CGPoint in
            let t = CGFloat(i) / CGFloat(steps)
            return CGPoint(x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t)
        }
        return stroke(pts, color: color, width: width)
    }

    static func arrow(from: CGPoint, to: CGPoint, color: UIColor) -> [PKStroke] {
        let angle = atan2(to.y - from.y, to.x - from.x)
        func wing(_ da: CGFloat) -> CGPoint {
            CGPoint(x: to.x - cos(angle + da) * 14, y: to.y - sin(angle + da) * 14)
        }
        return [line(from, to, color: color),
                line(to, wing(0.5), color: color),
                line(to, wing(-0.5), color: color)]
    }

    static func edge(_ a: CGPoint, _ b: CGPoint, r: CGFloat) -> PKStroke {
        let d = hypot(b.x - a.x, b.y - a.y)
        let ux = (b.x - a.x) / d
        let uy = (b.y - a.y) / d
        return line(CGPoint(x: a.x + ux * r, y: a.y + uy * r),
                    CGPoint(x: b.x - ux * r, y: b.y - uy * r),
                    color: ink)
    }

    static func highlight(x: CGFloat, y: CGFloat, length: CGFloat) -> PKStroke {
        var pts: [CGPoint] = []
        var dx: CGFloat = 0
        while dx <= length {
            pts.append(CGPoint(x: x + dx, y: y))
            dx += 6
        }
        return stroke(pts, color: amber, width: 24, inkType: .marker)
    }
}

enum SampleData {
    private static func codePage() -> NotePage {
        func ly(_ k: Int) -> CGFloat { 120 + 36 * CGFloat(k) - 8 } // text sitting on ruled line k
        var s: [PKStroke] = []
        s += SampleInk.textLine(x: 110, y: 100, words: [150, 90], width: 4)
        s += SampleInk.textLine(x: 110, y: ly(2), words: [40, 120, 40])
        s += SampleInk.textLine(x: 150, y: ly(3), words: [30, 80, 20, 60])
        s += SampleInk.textLine(x: 150, y: ly(4), words: [60, 40, 110])
        s += SampleInk.textLine(x: 190, y: ly(5), words: [60, 130])
        s += SampleInk.textLine(x: 150, y: ly(6), words: [60, 180, 40])
        s.append(SampleInk.highlight(x: 150, y: ly(4) - 6, length: 220))
        s.append(SampleInk.circle(center: CGPoint(x: 250, y: ly(3) - 4), rx: 80, ry: 18, color: SampleInk.red))
        s += SampleInk.arrow(from: CGPoint(x: 520, y: ly(3)), to: CGPoint(x: 338, y: ly(3)), color: SampleInk.red)
        s += SampleInk.textLine(x: 530, y: ly(3) - 4, words: [70, 60], color: SampleInk.red)
        return NotePage(template: .lined, drawing: PKDrawing(strokes: s))
    }

    private static func treePage() -> NotePage {
        var s: [PKStroke] = []
        s += SampleInk.textLine(x: 110, y: 100, words: [140, 80, 100], width: 4)
        let r: CGFloat = 30
        let root = CGPoint(x: 410, y: 260)
        let l = CGPoint(x: 250, y: 420)
        let rr = CGPoint(x: 570, y: 420)
        let ll = CGPoint(x: 160, y: 580)
        let lm = CGPoint(x: 340, y: 580)
        let rl = CGPoint(x: 480, y: 580)
        let rm = CGPoint(x: 660, y: 580)
        let edges: [(CGPoint, CGPoint)] = [(root, l), (root, rr), (l, ll), (l, lm), (rr, rl), (rr, rm)]
        for (a, b) in edges { s.append(SampleInk.edge(a, b, r: r)) }
        for n in [root, l, rr, ll, lm, rl, rm] {
            s.append(SampleInk.circle(center: n, rx: r, ry: r, color: SampleInk.ink))
            s.append(SampleInk.wave(x: n.x - 10, y: n.y, length: 20))
        }
        s += SampleInk.textLine(x: 640, y: 250, words: [90, 70], color: SampleInk.red)
        s += SampleInk.arrow(from: CGPoint(x: 700, y: 275), to: CGPoint(x: 600, y: 385), color: SampleInk.red)
        s += SampleInk.textLine(x: 110, y: 760, words: [200, 120, 80])
        s += SampleInk.textLine(x: 110, y: 800, words: [150, 220])
        return NotePage(template: .grid, drawing: PKDrawing(strokes: s))
    }

    private static func notesPage() -> NotePage {
        var s: [PKStroke] = []
        s += SampleInk.textLine(x: 80, y: 110, words: [120, 160], color: SampleInk.red, width: 4)
        s.append(SampleInk.line(CGPoint(x: 80, y: 128), CGPoint(x: 380, y: 128), color: SampleInk.red))
        let lengths: [[CGFloat]] = [[140, 100, 60], [90, 170], [200, 80, 120], [110, 150]]
        for (i, words) in lengths.enumerated() {
            let y = 210 + CGFloat(i) * 72
            s.append(SampleInk.circle(center: CGPoint(x: 90, y: y - 4), rx: 4, ry: 4, color: SampleInk.ink))
            s += SampleInk.textLine(x: 120, y: y, words: words)
        }
        s.append(SampleInk.highlight(x: 120, y: 276, length: 260))
        return NotePage(template: .dotted, drawing: PKDrawing(strokes: s))
    }

    static func makeLibrary() -> Folder {
        let palette = NotebookPalette.colors
        let cs = Folder(name: "CS Notes", notebooks: [
            Notebook(title: "Recursion", coverColor: palette[0], pages: [codePage(), treePage(), notesPage()]),
            Notebook(title: "Trees & Graphs", coverColor: palette[1], pages: [treePage(), notesPage()]),
        ])
        let math = Folder(name: "Math", notebooks: [
            Notebook(title: "Linear Algebra", coverColor: palette[4], pages: [notesPage()]),
        ])
        return Folder(name: "Library", folders: [cs, math], notebooks: [
            Notebook(title: "Lecture 1", coverColor: palette[2], pages: [codePage(), notesPage()]),
            Notebook(title: "Scratch", coverColor: palette[5], pages: [NotePage()]),
        ])
    }
}
