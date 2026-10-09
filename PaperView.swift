import SwiftUI
import PencilKit

/// Draws the paper template (blank / lined / grid / dotted), scaled to whatever size it is given.
struct PaperView: View {
    let template: PageTemplate

    var body: some View {
        Canvas { ctx, size in
            let s = size.width / PageSize.width
            ctx.scaleBy(x: s, y: s)
            switch template {
            case .blank:
                break
            case .lined:
                var lines = Path()
                var y: CGFloat = 120
                while y < PageSize.height {
                    lines.move(to: CGPoint(x: 0, y: y))
                    lines.addLine(to: CGPoint(x: PageSize.width, y: y))
                    y += 36
                }
                ctx.stroke(lines, with: .color(Color(red: 0.73, green: 0.87, blue: 0.98)), lineWidth: 1.2)
                var margin = Path()
                margin.move(to: CGPoint(x: 90, y: 0))
                margin.addLine(to: CGPoint(x: 90, y: PageSize.height))
                ctx.stroke(margin, with: .color(Color(red: 0.94, green: 0.60, blue: 0.60)), lineWidth: 1.2)
            case .grid:
                var grid = Path()
                var y: CGFloat = 36
                while y < PageSize.height {
                    grid.move(to: CGPoint(x: 0, y: y))
                    grid.addLine(to: CGPoint(x: PageSize.width, y: y))
                    y += 36
                }
                var x: CGFloat = 36
                while x < PageSize.width {
                    grid.move(to: CGPoint(x: x, y: 0))
                    grid.addLine(to: CGPoint(x: x, y: PageSize.height))
                    x += 36
                }
                ctx.stroke(grid, with: .color(Color(white: 0.88)), lineWidth: 1.2)
            case .dotted:
                var dots = Path()
                var y: CGFloat = 36
                while y < PageSize.height {
                    var x: CGFloat = 36
                    while x < PageSize.width {
                        dots.addEllipse(in: CGRect(x: x - 1.75, y: y - 1.75, width: 3.5, height: 3.5))
                        x += 36
                    }
                    y += 36
                }
                ctx.fill(dots, with: .color(Color(white: 0.74)))
            }
        }
        .background(Color.white)
    }
}

/// Paper + ink, scaled to fit. Give it a frame with the page's aspect ratio.
struct PageThumbnail: View {
    let page: NotePage

    var body: some View {
        ZStack {
            PaperView(template: page.template)
            Image(uiImage: page.drawing.image(
                from: CGRect(x: 0, y: 0, width: PageSize.width, height: PageSize.height),
                scale: 0.5))
                .resizable()
        }
    }
}
