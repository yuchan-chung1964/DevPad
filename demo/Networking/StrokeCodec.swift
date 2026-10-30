import PencilKit
import UIKit

/// Converts between PencilKit drawings and the API's stroke format.
///
/// Coordinates are page coordinates (see `PageSize`), same as the canvas, so no scaling is needed.
/// The API has no ink types beyond pen/highlighter/eraser, so on a round trip: marker -> highlighter,
/// everything else -> pen. Erased strokes don't exist in a `PKDrawing`, so `eraser` is never produced.
enum StrokeCodec {
    static func apiStrokes(from drawing: PKDrawing) -> [APIStroke] {
        drawing.strokes.compactMap { stroke in
            let points: [APIPoint] = stroke.path.map { p in
                APIPoint(
                    x: Double(p.location.x),
                    y: Double(p.location.y),
                    t: p.timeOffset,
                    pressure: min(max(Double(p.force), 0), 1)
                )
            }
            guard !points.isEmpty else { return nil }
            let widths = stroke.path.map { Double($0.size.width) }
            return APIStroke(
                points: points,
                tool: stroke.ink.inkType == .marker ? .highlighter : .pen,
                color: hex(stroke.ink.color),
                width: max(widths.reduce(0, +) / Double(widths.count), 0.1)
            )
        }
    }

    static func drawing(from strokes: [APIStroke]) -> PKDrawing {
        PKDrawing(strokes: strokes.compactMap(pkStroke))
    }

    // MARK: -

    private static func pkStroke(_ s: APIStroke) -> PKStroke? {
        guard s.tool != .eraser, !s.points.isEmpty else { return nil }
        let size = CGSize(width: s.width, height: s.width)
        let points = s.points.map {
            PKStrokePoint(
                location: CGPoint(x: $0.x, y: $0.y),
                timeOffset: $0.t,
                size: size,
                opacity: 1,
                force: CGFloat($0.pressure),
                azimuth: 0,
                altitude: .pi / 2
            )
        }
        let path = PKStrokePath(controlPoints: points, creationDate: Date())
        let ink = PKInk(s.tool == .highlighter ? .marker : .pen, color: color(fromHex: s.color))
        return PKStroke(ink: ink, path: path)
    }

    /// "#RRGGBB", or "#RRGGBBAA" when the color isn't fully opaque.
    static func hex(_ color: UIColor) -> String {
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        color.getRed(&r, green: &g, blue: &b, alpha: &a)
        func byte(_ v: CGFloat) -> Int { Int((min(max(v, 0), 1) * 255).rounded()) }
        let rgb = String(format: "#%02X%02X%02X", byte(r), byte(g), byte(b))
        return a >= 0.999 ? rgb : rgb + String(format: "%02X", byte(a))
    }

    static func color(fromHex hex: String) -> UIColor {
        let digits = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        guard digits.count == 6 || digits.count == 8, let value = UInt64(digits, radix: 16) else { return .black }
        let hasAlpha = digits.count == 8
        let r = CGFloat((value >> (hasAlpha ? 24 : 16)) & 0xFF) / 255
        let g = CGFloat((value >> (hasAlpha ? 16 : 8)) & 0xFF) / 255
        let b = CGFloat((value >> (hasAlpha ? 8 : 0)) & 0xFF) / 255
        let a = hasAlpha ? CGFloat(value & 0xFF) / 255 : 1
        return UIColor(red: r, green: g, blue: b, alpha: a)
    }
}
