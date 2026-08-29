import SwiftUI

/// Shared line weight for the hand-drawn vector glyphs below, tuned to read
/// consistently inside the app's uniform 64x64pt icon slot — no white
/// sticker card, no shadow, just a clean stroke sitting on the cream screen.
private let mjIconLineWidth: CGFloat = 7

private extension StrokeStyle {
    static let mjIcon = StrokeStyle(lineWidth: mjIconLineWidth, lineCap: .round, lineJoin: .round)
}

// MARK: - "videos" — play button

/// A clean play button: a stroked ring with a centered play triangle.
struct PlayButtonGlyph: View {
    var body: some View {
        ZStack {
            Circle()
                .inset(by: mjIconLineWidth / 2)
                .stroke(MJTheme.deepForest, style: .mjIcon)
            PlayTriangleShape()
                .fill(MJTheme.deepForest)
                .frame(width: 20, height: 24)
                .offset(x: 3)
        }
        .frame(width: 64, height: 64)
    }
}

private struct PlayTriangleShape: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.minX, y: rect.minY))
        path.addLine(to: CGPoint(x: rect.maxX, y: rect.midY))
        path.addLine(to: CGPoint(x: rect.minX, y: rect.maxY))
        path.closeSubpath()
        return path
    }
}

// MARK: - "alertness" — lightning bolt

/// A bold lightning bolt, filled solid in the app's existing icon green.
struct LightningBoltGlyph: View {
    var body: some View {
        LightningBoltShape()
            .fill(MJTheme.deepForest)
            .frame(width: 64, height: 64)
    }
}

private struct LightningBoltShape: Shape {
    /// Small radius applied to every vertex so the bolt reads as bold and
    /// graphic without being needle-sharp — but still crisp, not a soft blob.
    private let cornerRadius: CGFloat = 5

    func path(in rect: CGRect) -> Path {
        let w = rect.width
        let h = rect.height
        let points: [CGPoint] = [
            CGPoint(x: 0.60 * w, y: 0.0),
            CGPoint(x: 0.25 * w, y: 0.55 * h),
            CGPoint(x: 0.45 * w, y: 0.55 * h),
            CGPoint(x: 0.35 * w, y: 1.0 * h),
            CGPoint(x: 0.78 * w, y: 0.38 * h),
            CGPoint(x: 0.52 * w, y: 0.38 * h)
        ]
        return roundedPolygon(points, radius: cornerRadius)
    }

    /// Builds a closed polygon path where every vertex is softened by a small
    /// arc, keeping the silhouette bold and legible instead of pin-sharp.
    private func roundedPolygon(_ points: [CGPoint], radius: CGFloat) -> Path {
        var path = Path()
        let count = points.count
        guard count >= 3 else { return path }

        func point(_ i: Int) -> CGPoint { points[(i + count) % count] }

        for i in 0..<count {
            let prev = point(i - 1)
            let curr = point(i)
            let next = point(i + 1)

            let toPrev = CGVector(dx: prev.x - curr.x, dy: prev.y - curr.y)
            let toNext = CGVector(dx: next.x - curr.x, dy: next.y - curr.y)
            let lenPrev = max(sqrt(toPrev.dx * toPrev.dx + toPrev.dy * toPrev.dy), 0.001)
            let lenNext = max(sqrt(toNext.dx * toNext.dx + toNext.dy * toNext.dy), 0.001)
            let r = min(radius, lenPrev * 0.4, lenNext * 0.4)

            let startPoint = CGPoint(x: curr.x + toPrev.dx / lenPrev * r, y: curr.y + toPrev.dy / lenPrev * r)
            let endPoint = CGPoint(x: curr.x + toNext.dx / lenNext * r, y: curr.y + toNext.dy / lenNext * r)

            if i == 0 {
                path.move(to: startPoint)
            } else {
                path.addLine(to: startPoint)
            }
            path.addQuadCurve(to: endPoint, control: curr)
        }
        path.closeSubpath()
        return path
    }
}

// MARK: - "rules of the road" — directional arrow

/// A single clean diagonal road arrow: shaft plus a chevron head.
struct RoadArrowGlyph: View {
    var body: some View {
        RoadArrowShape()
            .stroke(MJTheme.deepForest, style: .mjIcon)
            .frame(width: 64, height: 64)
    }
}

private struct RoadArrowShape: Shape {
    func path(in rect: CGRect) -> Path {
        let w = rect.width
        let h = rect.height
        var path = Path()
        path.move(to: CGPoint(x: 0.20 * w, y: 0.84 * h))
        path.addLine(to: CGPoint(x: 0.72 * w, y: 0.24 * h))
        path.move(to: CGPoint(x: 0.42 * w, y: 0.24 * h))
        path.addLine(to: CGPoint(x: 0.72 * w, y: 0.24 * h))
        path.addLine(to: CGPoint(x: 0.72 * w, y: 0.54 * h))
        return path
    }
}

// MARK: - "all categories" — window pane grid

/// A single square outline divided into 4 equal panes by a crossing line.
struct WindowPaneGlyph: View {
    var body: some View {
        WindowPaneShape()
            .stroke(MJTheme.deepForest, style: .mjIcon)
            .frame(width: 64, height: 64)
    }
}

private struct WindowPaneShape: Shape {
    func path(in rect: CGRect) -> Path {
        let inset = rect.insetBy(dx: mjIconLineWidth / 2, dy: mjIconLineWidth / 2)
        var path = Path()
        path.addRect(inset)
        path.move(to: CGPoint(x: inset.midX, y: inset.minY))
        path.addLine(to: CGPoint(x: inset.midX, y: inset.maxY))
        path.move(to: CGPoint(x: inset.minX, y: inset.midY))
        path.addLine(to: CGPoint(x: inset.maxX, y: inset.midY))
        return path
    }
}

// MARK: - Shared resolver

/// Resolves an icon asset name (from `TheorySubcategory.lineArtIconAsset` or
/// the synthetic "all categories"/"videos" rows) to its glyph or image, at
/// any size. Used by both the theory list and the quiz screen's topic badge
/// so every screen agrees on what each category looks like.
struct TheoryIconGlyph: View {
    let iconAsset: String
    var size: CGFloat = 64

    var body: some View {
        Group {
            switch iconAsset {
            case "four_circles_grid":
                Image("theory_grid_icon")
                    .resizable()
                    .renderingMode(.original)
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 64, height: 64)
            case "film_reel_sticker":
                PlayButtonGlyph()
            case "eye_alert_circle":
                LightningBoltGlyph()
            case "arrow_curve_forward":
                RoadArrowGlyph()
            case "speech_bubbles_dialog":
                SpeechBubblesGlyph()
            default:
                Image(iconAsset)
                    .resizable()
                    .renderingMode(.original)
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 64, height: 64)
            }
        }
        .frame(width: 64, height: 64)
        .scaleEffect(size / 64)
        .frame(width: size, height: size)
    }
}

// MARK: - "attitude" — speech bubbles, no card

/// Two overlapping speech bubbles, stroke-only, no white card or shadow.
struct SpeechBubblesGlyph: View {
    var body: some View {
        ZStack {
            SpeechBubbleShape(tailOnLeft: true)
                .stroke(MJTheme.deepForest, style: .mjIcon)
                .frame(width: 40, height: 32)
                .offset(x: -10, y: -5)
            SpeechBubbleShape(tailOnLeft: false)
                .stroke(MJTheme.deepForest, style: .mjIcon)
                .frame(width: 40, height: 32)
                .offset(x: 10, y: 7)
        }
        .frame(width: 64, height: 64)
    }
}

private struct SpeechBubbleShape: Shape {
    let tailOnLeft: Bool

    func path(in rect: CGRect) -> Path {
        let bodyRect = CGRect(x: rect.minX, y: rect.minY, width: rect.width, height: rect.height * 0.78)
        var path = Path(roundedRect: bodyRect, cornerRadius: bodyRect.height * 0.45)
        let tailX = tailOnLeft ? bodyRect.minX + bodyRect.width * 0.24 : bodyRect.maxX - bodyRect.width * 0.24
        var tail = Path()
        tail.move(to: CGPoint(x: tailX - 6, y: bodyRect.maxY - 2))
        tail.addLine(to: CGPoint(x: tailX, y: rect.maxY))
        tail.addLine(to: CGPoint(x: tailX + 8, y: bodyRect.maxY - 2))
        path.addPath(tail)
        return path
    }
}
