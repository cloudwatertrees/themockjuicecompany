import SwiftUI

/// Pure-vector home scene. Drawn in a fixed 1536×3072 design space and
/// aspect-filled into whatever size it is given, matching the old
/// `scaledToFill()` raster behaviour.
struct HomeSceneIllustration: View {
    var body: some View {
        Canvas { context, size in
            let transform = HomeSceneArt.fillTransform(for: size)
            context.concatenate(transform)
            HomeSceneArt.draw(in: &context)
        }
    }
}

enum HomeSceneArt {
    static let size = CGSize(width: 1536, height: 3072)

    /// One flat-colour shape of the illustration.
    struct Layer {
        let color: Color
        let path: Path

        init(_ hex: String, _ subpaths: [[CGFloat]]) {
            color = Color(hex: hex)
            path = Path { p in
                for s in subpaths {
                    p.move(to: CGPoint(x: s[0], y: s[1]))
                    var i = 2
                    while i + 5 < s.count {
                        p.addCurve(
                            to: CGPoint(x: s[i + 4], y: s[i + 5]),
                            control1: CGPoint(x: s[i], y: s[i + 1]),
                            control2: CGPoint(x: s[i + 2], y: s[i + 3])
                        )
                        i += 6
                    }
                    p.closeSubpath()
                }
            }
        }
    }

    /// Maps the design space onto `viewSize` with aspect-fill, centred.
    static func fillTransform(for viewSize: CGSize) -> CGAffineTransform {
        let scale = max(viewSize.width / size.width, viewSize.height / size.height)
        return CGAffineTransform(
            translationX: (viewSize.width - size.width * scale) / 2,
            y: (viewSize.height - size.height * scale) / 2
        )
        .scaledBy(x: scale, y: scale)
    }

    /// Paints every layer back to front.
    static func draw(in context: inout GraphicsContext) {
        fill(skyAndClouds, in: &context)
        fill(distantHills, in: &context)
        fill(hills, in: &context)
        HomeSceneRoad.draw(in: &context)
        fill(houseAndFence, in: &context)
        fill(trees, in: &context)
        fill(roadSign, in: &context)
        fill(bushes, in: &context)
        fill(rock, in: &context)
        fill(grassTufts, in: &context)
        fill(flowers, in: &context)
    }

    static func fill(_ layers: [Layer], in context: inout GraphicsContext) {
        for layer in layers {
            context.fill(layer.path, with: .color(layer.color), style: FillStyle(eoFill: true))
        }
    }
}
