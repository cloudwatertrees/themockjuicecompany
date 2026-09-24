import SwiftUI

struct SceneryBackgroundView: View {
    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            GeometryReader { geo in
                let w = geo.size.width

                Canvas { context, size in
                    drawTrafficSigns(context: &context, size: size, width: w)
                }
                .ignoresSafeArea()
            }
        }
    }

    private func drawTrafficSigns(context: inout GraphicsContext, size: CGSize, width: CGFloat) {
        let signPositions: [(x: CGFloat, y: CGFloat, type: Int)] = [
            (0.15, 900, 2),
            (0.85, 1150, 0),
        ]

        for sign in signPositions {
            let cx = size.width * sign.x
            let cy = sign.y

            var pole = Path()
            pole.addRect(CGRect(x: cx - 2, y: cy, width: 4, height: 30))
            context.fill(pole, with: .color(MJTheme.signPost.opacity(0.6)))

            switch sign.type {
            case 0:
                var circle = Path()
                circle.addEllipse(in: CGRect(x: cx - 12, y: cy - 24, width: 24, height: 24))
                context.fill(circle, with: .color(MJTheme.signFaceWhite))
                context.stroke(circle, with: .color(MJTheme.trafficRed), lineWidth: 3)
            case 1:
                var triangle = Path()
                triangle.move(to: CGPoint(x: cx, y: cy - 28))
                triangle.addLine(to: CGPoint(x: cx - 14, y: cy))
                triangle.addLine(to: CGPoint(x: cx + 14, y: cy))
                triangle.closeSubpath()
                context.fill(triangle, with: .color(MJTheme.signFaceWhite))
                context.stroke(triangle, with: .color(MJTheme.trafficRed), lineWidth: 2)
            default:
                var rect = Path()
                rect.addRect(CGRect(x: cx - 12, y: cy - 22, width: 24, height: 22))
                context.fill(rect, with: .color(MJTheme.signFaceBlue))
                context.fill(Path(CGRect(x: cx - 8, y: cy - 18, width: 16, height: 14)), with: .color(MJTheme.signFaceWhite))
            }
        }
    }
}

/// Scrolls together with the road and nodes, unlike `SceneryBackgroundView`
/// which is pinned behind the ScrollView.
struct TreeSceneryView: View {
    let width: CGFloat
    let contentHeight: CGFloat

    private let treeFractions: [(x: CGFloat, yFraction: CGFloat, scale: CGFloat)] = [
        (0.14, 0.12, 1.0),
        (0.86, 0.36, 0.9),
        (0.14, 0.6, 1.05),
        (0.86, 0.84, 0.9),
    ]

    var body: some View {
        ForEach(Array(treeFractions.enumerated()), id: \.offset) { _, pos in
            Image("tree_sticker")
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: 70 * pos.scale, height: 70 * pos.scale)
                .position(x: width * pos.x, y: contentHeight * pos.yFraction)
        }
    }
}

struct RoadPathView: View {
    let nodePositions: [CGPoint]

    var body: some View {
        Canvas { context, size in
            guard nodePositions.count >= 2 else { return }

            var roadPath = Path()
            roadPath.move(to: nodePositions[0])

            for i in 1..<nodePositions.count {
                let prev = nodePositions[i - 1]
                let curr = nodePositions[i]
                let midY = (prev.y + curr.y) / 2
                roadPath.addCurve(
                    to: curr,
                    control1: CGPoint(x: prev.x, y: midY),
                    control2: CGPoint(x: curr.x, y: midY)
                )
            }

            context.stroke(
                roadPath,
                with: .color(MJTheme.roadAsphalt),
                style: StrokeStyle(lineWidth: 40, lineCap: .round, lineJoin: .round)
            )

            context.stroke(
                roadPath,
                with: .color(MJTheme.roadMarking),
                style: StrokeStyle(lineWidth: 3, lineCap: .round, dash: [12, 10])
            )
        }
    }
}
