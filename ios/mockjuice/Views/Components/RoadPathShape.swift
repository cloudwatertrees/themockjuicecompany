import SwiftUI

struct SceneryBackgroundView: View {
    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            GeometryReader { geo in
                let w = geo.size.width

                Canvas { context, size in
                    drawTrees(context: &context, size: size, width: w)
                    drawTrafficSigns(context: &context, size: size, width: w)
                }
                .ignoresSafeArea()
            }
        }
    }

private func drawTrees(context: inout GraphicsContext, size: CGSize, width: CGFloat) {
        let treePositions: [(x: CGFloat, y: CGFloat, scale: CGFloat)] = [
            (0.08, 180, 1.0),
            (0.92, 250, 0.8),
            (0.05, 450, 1.2),
            (0.95, 520, 0.9),
            (0.1, 700, 1.1),
            (0.88, 780, 0.85),
            (0.03, 950, 1.0),
            (0.93, 1050, 0.95),
            (0.07, 1200, 1.15),
            (0.9, 1350, 0.9),
        ]

        for pos in treePositions {
            let cx = size.width * pos.x
            let cy = pos.y
            let s = pos.scale

            let darkGreen = MJTheme.treeFoliageDark
            let medGreen = MJTheme.treeFoliage

            var trunk = Path()
            trunk.addRect(CGRect(x: cx - 4 * s, y: cy + 15 * s, width: 8 * s, height: 20 * s))
            context.fill(trunk, with: .color(MJTheme.treeTrunk))

            let layers: [(offset: CGFloat, w: CGFloat, h: CGFloat, color: Color)] = [
                (0, 30, 25, darkGreen),
                (-12, 26, 22, medGreen),
                (-22, 20, 18, darkGreen.opacity(0.9)),
            ]

            for layer in layers {
                var treePath = Path()
                treePath.move(to: CGPoint(x: cx, y: cy + layer.offset - layer.h * s))
                treePath.addLine(to: CGPoint(x: cx - layer.w / 2 * s, y: cy + layer.offset))
                treePath.addLine(to: CGPoint(x: cx + layer.w / 2 * s, y: cy + layer.offset))
                treePath.closeSubpath()
                context.fill(treePath, with: .color(layer.color))
            }
        }
    }

    private func drawTrafficSigns(context: inout GraphicsContext, size: CGSize, width: CGFloat) {
        let signPositions: [(x: CGFloat, y: CGFloat, type: Int)] = [
            (0.18, 350, 0),
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
