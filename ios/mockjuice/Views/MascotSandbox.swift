import SwiftUI

// Apple mascot system, traced 1:1 from "Apple System Trial" (Assets.xcassets).
// Every figure, face and part below is vector path data generated from the sheet
// (Lanczos 4x upscale -> palette segmentation -> potrace), drawn in sheet pixel
// coordinates so each figure lands exactly where it sits on the reference. The
// rig's face parts are the exception: constructed geometry (ellipses and few-node
// smooth Beziers, symmetric) with proportions measured from the sheet.

// MARK: - Palette

/// Inks measured from the sheet's pixels. The sheet's printed hex labels
/// (#E52332, #4A2E1F, #78C05F, #F8F5F1, #F7F6F2) don't match its own artwork,
/// so these are the values that reproduce it.
enum MascotInk {
    case bg, red, redShade, dark, stem, stemDark, leaf, leafVein, white, eyeShade, pink, shadow, wall, yellow, blue, blueDark, cream, bookGreen, outline, paper

    var color: Color {
        switch self {
        case .bg: Color(hex: "#F8F8F0")
        case .red: Color(hex: "#ED1826")
        case .redShade: Color(hex: "#D70F1D")
        case .dark: Color(hex: "#1C1011")
        case .stem: Color(hex: "#602114")
        case .stemDark: Color(hex: "#391C14")
        case .leaf: Color(hex: "#55AF56")
        case .leafVein: Color(hex: "#388739")
        case .white: Color(hex: "#FEFDFA")
        case .eyeShade: Color(hex: "#E4E0DC")
        case .pink: Color(hex: "#FD636C")
        case .shadow: Color(hex: "#E9E5DD")
        case .wall: Color(hex: "#EEEBE1")
        case .yellow: Color(hex: "#FDC238")
        case .blue: Color(hex: "#2F95EE")
        case .blueDark: Color(hex: "#137EE6")
        case .cream: Color(hex: "#FAEDD1")
        case .bookGreen: Color(hex: "#ADCE0B")
        case .outline: Color(hex: "#DCD8D0")
        case .paper: Color(hex: "#F4F0E7")
        }
    }
}

enum MascotPalette {
    static let appleRed = MascotInk.red.color
    static let stem = MascotInk.stem.color
    static let leaf = MascotInk.leaf.color
    static let highlight = MascotInk.white.color
    static let background = MascotInk.bg.color
    static let blush = MascotInk.pink.color
    static let details = MascotInk.dark.color
}

// MARK: - Path data

enum TracedPathParser {
    /// Parses absolute M / L / C / Z path data as emitted by the tracer.
    static func parse(_ data: String) -> Path {
        var path = Path()
        var nums: [CGFloat] = []
        var command: Character? = nil
        var token = ""

        func apply() {
            switch command {
            case "M"?:
                var k = 0
                while k + 1 < nums.count {
                    let p = CGPoint(x: nums[k], y: nums[k + 1])
                    if k == 0 { path.move(to: p) } else { path.addLine(to: p) }
                    k += 2
                }
            case "L"?:
                var k = 0
                while k + 1 < nums.count {
                    path.addLine(to: CGPoint(x: nums[k], y: nums[k + 1]))
                    k += 2
                }
            case "C"?:
                var k = 0
                while k + 5 < nums.count {
                    path.addCurve(to: CGPoint(x: nums[k + 4], y: nums[k + 5]),
                                  control1: CGPoint(x: nums[k], y: nums[k + 1]),
                                  control2: CGPoint(x: nums[k + 2], y: nums[k + 3]))
                    k += 6
                }
            default:
                break
            }
            nums.removeAll(keepingCapacity: true)
        }

        func flush() {
            if let v = Double(token) { nums.append(CGFloat(v)) }
            token = ""
        }

        for ch in data {
            switch ch {
            case "M", "L", "C":
                flush()
                apply()
                command = ch
            case "Z":
                flush()
                apply()
                path.closeSubpath()
                command = nil
            case "-":
                flush()
                token.append(ch)
            case " ":
                flush()
            default:
                token.append(ch)
            }
        }
        flush()
        apply()
        return path
    }
}

struct TracedLayer {
    enum Role { case body, face, other }

    let ink: MascotInk
    let role: Role
    let path: Path
    /// Soft edge (blush, ground shadow), in sheet pixels.
    let blur: CGFloat
    /// Shading sampled from the sheet; nil = flat ink.
    let gradient: (start: CGPoint, end: CGPoint, colors: [Color])?

    init(_ ink: MascotInk, _ role: Role, _ data: String, blur: CGFloat = 0,
         gradient g: (CGFloat, CGFloat, CGFloat, CGFloat, String, String)? = nil) {
        self.ink = ink
        self.role = role
        self.path = TracedPathParser.parse(data)
        self.blur = blur
        self.gradient = g.map { (CGPoint(x: $0.0, y: $0.1), CGPoint(x: $0.2, y: $0.3), [Color(hex: $0.4), Color(hex: $0.5)]) }
    }

    var shading: GraphicsContext.Shading {
        guard let g = gradient else { return .color(ink.color) }
        return .linearGradient(Gradient(colors: g.colors), startPoint: g.start, endPoint: g.end)
    }

    /// Blur is given in sheet pixels; the context's transform scales it with the figure.
    func draw(in ctx: inout GraphicsContext) {
        let style = FillStyle(eoFill: true)
        guard blur > 0 else {
            ctx.fill(path, with: shading, style: style)
            return
        }
        ctx.drawLayer { c in
            c.addFilter(.blur(radius: blur))
            c.fill(path, with: shading, style: style)
        }
    }
}

struct TracedFigure {
    /// Top-left of the figure's box on the reference sheet.
    let origin: CGPoint
    let size: CGSize
    var bodyCenter: CGPoint = .zero
    var bodyRadius: CGFloat = 1
    var faceBox: CGRect = .zero
    let layers: [TracedLayer]

    var frame: CGRect { CGRect(origin: origin, size: size) }

    /// Union of all layers of one role, for use as a single silhouette.
    func outline(_ ink: MascotInk? = nil, role: TracedLayer.Role? = nil) -> Path {
        var p = Path()
        for l in layers where (ink == nil || l.ink == ink) && (role == nil || l.role == role) {
            p.addPath(l.path)
        }
        return p
    }

    /// Union of specific layers (by draw index).
    func union(_ indices: [Int]) -> Path {
        var p = Path()
        for i in indices { p.addPath(layers[i].path) }
        return p
    }

    /// Draws the figure in its own coordinate space. When `face` is given, this
    /// figure's own face layers are replaced by the face layers of `face`,
    /// re-anchored onto this body and clipped to it.
    func draw(in ctx: inout GraphicsContext, face: TracedFigure? = nil) {
        for layer in layers {
            if face != nil, layer.role == .face { continue }
            layer.draw(in: &ctx)
            // Swapped faces sit directly on the body so props (books, wall) stay in front.
            if let face, layer.role == .body {
                drawFace(of: face, in: &ctx)
            }
        }
    }

    private func drawFace(of source: TracedFigure, in ctx: inout GraphicsContext) {
        let target = self
        ctx.drawLayer { c in
            c.clip(to: target.outline(role: .body), style: FillStyle(eoFill: true))
            let k = target.bodyRadius / source.bodyRadius
            c.translateBy(x: target.faceBox.midX, y: target.faceBox.midY)
            c.scaleBy(x: k, y: k)
            c.translateBy(x: -source.faceBox.midX, y: -source.faceBox.midY)
            for l in source.layers where l.role == .face {
                l.draw(in: &c)
            }
        }
    }
}

// MARK: - Composite

/// Renders a traced figure at its native aspect ratio, scaled to fit.
struct TracedFigureView: View {
    let figure: TracedFigure
    var face: TracedFigure? = nil

    var body: some View {
        Canvas { ctx, size in
            let s = min(size.width / figure.size.width, size.height / figure.size.height)
            ctx.translateBy(x: (size.width - figure.size.width * s) / 2,
                            y: (size.height - figure.size.height * s) / 2)
            ctx.scaleBy(x: s, y: s)
            figure.draw(in: &ctx, face: face)
        }
        .aspectRatio(figure.size, contentMode: .fit)
    }
}

struct AppleFace: View {
    enum Expression: String, CaseIterable, Identifiable {
        case neutral, happy, excited, curious, thinking, sad, wink
        var id: String { rawValue }
        var title: String { rawValue.capitalized }

        /// The expression-row head this face is traced from.
        var figure: TracedFigure {
            switch self {
            case .neutral: MascotArt.neutral
            case .happy: MascotArt.happy
            case .excited: MascotArt.excited
            case .curious: MascotArt.curious
            case .thinking: MascotArt.thinking
            case .sad: MascotArt.sad
            case .wink: MascotArt.wink
            }
        }
    }

    var expression: Expression = .neutral

    /// Eyes, brows, mouth and blush only, cropped to the face.
    var body: some View {
        let f = expression.figure
        Canvas { ctx, size in
            let box = f.faceBox
            let s = min(size.width / box.width, size.height / box.height)
            ctx.translateBy(x: (size.width - box.width * s) / 2, y: (size.height - box.height * s) / 2)
            ctx.scaleBy(x: s, y: s)
            ctx.translateBy(x: -box.minX, y: -box.minY)
            for l in f.layers where l.role == .face {
                l.draw(in: &ctx)
            }
        }
        .aspectRatio(f.faceBox.size, contentMode: .fit)
    }
}

// MARK: - Rig parts (step 1)

/// One rig layer: paths in local coordinates around a pivot, plus where
/// that pivot sits in character space (the Front figure's box, sheet pixels).
struct MascotPart: Identifiable {
    let id: String
    let anchor: CGPoint
    /// Moves with another part's pose (joint shading follows its limb).
    var follows: String? = nil
    let layers: [TracedLayer]

    var bounds: CGRect {
        layers.reduce(CGRect.null) { $0.union($1.path.boundingRect) }
    }

    /// Union of every layer, for clipping and lids.
    var silhouette: Path {
        var p = Path()
        for l in layers { p.addPath(l.path) }
        return p
    }

    func draw(in ctx: inout GraphicsContext) {
        for l in layers { l.draw(in: &ctx) }
    }
}

/// Eyelids. Not on the sheet: built from the eye white's own outline and filled
/// with body red. The upper lid comes down to a shut line low in the eye, edged
/// with a dark lid line that thickens from the open lid line's weight; the lower
/// lid rises late to meet it, so no white is left below a shut lid.
/// `closure` 0 = open, 1 = shut.
enum MascotLid {
    /// Lid line weight as the lid starts to close (the open lid line's) and when shut.
    static let openWeight: CGFloat = 1.4
    static let shutWeight: CGFloat = 2.6

    static func draw(over eye: MascotPart, closure: CGFloat, in ctx: inout GraphicsContext) {
        guard closure > 0 else { return }
        let white = eye.silhouette
        // A little past the eye's edge, so no ring of eye white shows around a shut lid.
        let shape = white.union(white.strokedPath(StrokeStyle(lineWidth: 2.4)))
        let b = white.boundingRect
        let c = min(max(closure, 0), 1)
        // The lid shuts low in the eye so a shut eye still reads as a closed lid. The upper
        // edge starts just clear of the eye; the lower lid only rises near the end.
        let shutY = b.minY + b.height * 0.78
        let upperY = b.minY - 1.2 + (shutY - b.minY + 1.2) * c
        let lowerY = b.maxY + 1.2 + (shutY - b.maxY - 1.2) * c * c * c
        let sag = b.height * 0.14 * (1 - c * 0.6)

        func edge(at y: CGFloat) -> Path {
            var p = Path()
            p.move(to: CGPoint(x: b.minX - 2, y: y - sag))
            p.addQuadCurve(to: CGPoint(x: b.maxX + 2, y: y - sag), control: CGPoint(x: b.midX, y: y + sag))
            return p
        }
        // Each lid is intersected with the eye on its own: a union of the two lids, a stroked
        // curve, or a clip all lose the curved edge on iOS.
        func lid(edgeY y: CGFloat, outerY: CGFloat) -> Path {
            var p = Path()
            p.move(to: CGPoint(x: b.minX - 2, y: outerY))
            p.addLine(to: CGPoint(x: b.maxX + 2, y: outerY))
            p.addLine(to: CGPoint(x: b.maxX + 2, y: y - sag))
            p.addQuadCurve(to: CGPoint(x: b.minX - 2, y: y - sag), control: CGPoint(x: b.midX, y: y + sag))
            p.closeSubpath()
            return p
        }
        let cover = lid(edgeY: upperY, outerY: b.minY - 4)
        let lower = lid(edgeY: lowerY, outerY: b.maxY + 4)
        ctx.fill(cover.intersection(shape), with: .color(MascotInk.red.color))
        ctx.fill(lower.intersection(shape), with: .color(MascotInk.red.color))

        // Round-capped line, cut half its weight inside the (elliptical) eye white, so the caps
        // end on the eye's edge and never overhang.
        let weight = openWeight + (shutWeight - openWeight) * c
        let inner = Path(ellipseIn: b.insetBy(dx: weight / 2, dy: weight / 2))
        ctx.stroke(edge(at: upperY).lineIntersection(inner), with: .color(MascotInk.dark.color),
                   style: StrokeStyle(lineWidth: weight, lineCap: .round))
    }
}

/// Draws parts at their rest positions in character space. `pose` adds a
/// transform per part id about its pivot; a part that `follows` another uses
/// that part's pose. Pupils are clipped to their eye; lids go on last, over the
/// lid lines, so a closing lid hides them.
enum MascotRenderer {
    static func draw(_ parts: [MascotPart], lid: CGFloat = 0, pose: [String: CGAffineTransform] = [:],
                     in ctx: inout GraphicsContext) {
        for part in parts {
            var c = ctx
            // Pupils run to the eye's edge: clip them to the eye white plus the rig's 0.75 px margin.
            if part.id.hasPrefix("pupil") {
                let eye = part.id == "pupilLeft" ? MascotParts.eyeLeft : MascotParts.eyeRight
                let white = eye.silhouette
                c.clip(to: white.union(white.strokedPath(StrokeStyle(lineWidth: 1.5)))
                    .applying(CGAffineTransform(translationX: eye.anchor.x, y: eye.anchor.y)))
            }
            let t = pose[part.id] ?? part.follows.flatMap({ pose[$0] })
            MascotRenderer.clipShade(part, pose: t ?? .identity, in: &c)
            c.translateBy(x: part.anchor.x, y: part.anchor.y)
            if let t { c.concatenate(t) }
            part.draw(in: &c)
            if part.id == "lashRight" {
                for eye in [MascotParts.eyeLeft, MascotParts.eyeRight] {
                    var e = ctx
                    e.translateBy(x: eye.anchor.x, y: eye.anchor.y)
                    MascotLid.draw(over: eye, closure: lid, in: &e)
                }
            }
        }
    }

    /// Joint shading (a part that `follows` a limb) only shows on that limb, outside the
    /// body, so it stays a soft crease at the body's edge however the limb is posed.
    static func clipShade(_ part: MascotPart, pose: CGAffineTransform, in ctx: inout GraphicsContext) {
        guard let id = part.follows, let limb = MascotParts.stack.first(where: { $0.id == id }) else { return }
        let body = MascotParts.body
        ctx.clip(to: limb.silhouette.applying(pose.concatenating(CGAffineTransform(translationX: limb.anchor.x, y: limb.anchor.y))))
        ctx.clip(to: body.silhouette.applying(CGAffineTransform(translationX: body.anchor.x, y: body.anchor.y)), options: .inverse)
    }
}

// MARK: - Assembled character (step 2)

/// The character built from parts, in the Front figure's box.
struct MascotCharacter: View {
    var parts: [MascotPart] = MascotParts.stack
    var lid: CGFloat = 0
    /// Draws the traced Front figure's outline on top, to check the fit.
    var showsFrontOutline = false
    /// Draws the whole stack faint underneath, so a partial build shows where its parts sit.
    var ghost = false

    var body: some View {
        let size = MascotRig.size
        Canvas { ctx, canvas in
            let s = min(canvas.width / size.width, canvas.height / size.height)
            ctx.translateBy(x: (canvas.width - size.width * s) / 2, y: (canvas.height - size.height * s) / 2)
            ctx.scaleBy(x: s, y: s)
            if ghost {
                var faint = ctx
                faint.opacity = 0.14
                faint.drawLayer { MascotRenderer.draw(MascotParts.stack, in: &$0) }
            }
            MascotRenderer.draw(parts, lid: lid, in: &ctx)
            if showsFrontOutline {
                ctx.stroke(MascotRig.frontOutline, with: .color(MascotInk.blue.color), lineWidth: 1.5 / s)
            }
        }
        .aspectRatio(size, contentMode: .fit)
    }
}

/// Step 2 review: the assembled character beside the traced Front figure, and
/// the traced outline drawn over the assembly.
struct MascotAssemblySheet: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            MascotSectionHeader(title: "Assembled  ·  Traced Front")
            HStack(spacing: 12) {
                MascotCharacter()
                    .aspectRatio(MascotRig.size, contentMode: .fit)
                    .frame(maxWidth: .infinity)
                TracedFigureView(figure: MascotArt.front)
                    .frame(maxWidth: .infinity)
            }
            MascotSectionHeader(title: "Fit check: the blue line is the sheet's Front outline")
            MascotCharacter(showsFrontOutline: true)
                .aspectRatio(MascotRig.size, contentMode: .fit)
                .frame(maxWidth: 300)
                .frame(maxWidth: .infinity)
        }
        .padding(16)
        .background(MascotPalette.background)
    }
}

struct MascotSectionHeader: View {
    let title: String

    var body: some View {
        Text(title.uppercased())
            .font(.system(size: 12, weight: .heavy, design: .rounded))
            .foregroundStyle(MascotPalette.details)
            .fixedSize(horizontal: false, vertical: true)
    }
}

/// Lays children out left to right, wrapping onto new rows when out of width.
struct MascotFlow: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let maxWidth = proposal.width ?? .infinity
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        var widest: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x > 0, x + size.width > maxWidth {
                y += rowHeight + spacing
                x = 0
                rowHeight = 0
            }
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            widest = max(widest, x - spacing)
        }
        return CGSize(width: min(widest, maxWidth), height: y + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX
        var y = bounds.minY
        var rowHeight: CGFloat = 0
        for view in subviews {
            let size = view.sizeThatFits(.unspecified)
            if x > bounds.minX, x + size.width > bounds.maxX {
                y += rowHeight + spacing
                x = bounds.minX
                rowHeight = 0
            }
            view.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}

/// A single part on its own, centred, with its pivot marked.
struct MascotPartTile: View {
    let part: MascotPart

    var body: some View {
        VStack(spacing: 4) {
            Canvas { ctx, canvas in
                let b = part.bounds.insetBy(dx: -4, dy: -4)
                let s = min(canvas.width / b.width, canvas.height / b.height)
                ctx.translateBy(x: (canvas.width - b.width * s) / 2, y: (canvas.height - b.height * s) / 2)
                ctx.scaleBy(x: s, y: s)
                ctx.translateBy(x: -b.minX, y: -b.minY)
                part.draw(in: &ctx)
                let r = 2.5 / s
                ctx.fill(Path(ellipseIn: CGRect(x: -r, y: -r, width: r * 2, height: r * 2)), with: .color(.blue))
            }
            .frame(width: 72, height: 60)
            Text(part.id)
                .font(.system(size: 10, weight: .medium, design: .rounded))
                .foregroundStyle(MascotPalette.details)
                .lineLimit(1)
                .minimumScaleFactor(0.5)
        }
        .frame(width: 76)
    }
}

/// Parts review sheet: the assembled character, its stacking order, the eyelid,
/// and every part with its pivot.
struct MascotPartsSheet: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            MascotSectionHeader(title: "Assembled from the parts below")
            MascotCharacter()
                .frame(maxWidth: 240)
                .frame(maxWidth: .infinity)

            MascotSectionHeader(title: "Stacking order (each adds one part)")
            MascotFlow {
                ForEach(MascotParts.stack.indices, id: \.self) { i in
                    VStack(spacing: 4) {
                        MascotCharacter(parts: Array(MascotParts.stack[...i]), ghost: true).frame(width: 72, height: 66)
                        Text("\(i + 1). \(MascotParts.stack[i].id)")
                            .font(.system(size: 10, weight: .medium, design: .rounded))
                            .foregroundStyle(MascotPalette.details)
                            .lineLimit(1)
                            .minimumScaleFactor(0.5)
                    }
                    .frame(width: 76)
                }
            }

            MascotSectionHeader(title: "Eyelid (drawn, not traced): open → shut")
            HStack(spacing: 8) {
                ForEach([0, 0.35, 0.7, 1.0], id: \.self) { c in
                    MascotCharacter(lid: c).frame(maxWidth: .infinity)
                }
            }

            MascotSectionHeader(title: "Parts (blue dot = pivot)")
            MascotFlow { ForEach(MascotParts.stack) { MascotPartTile(part: $0) } }
            MascotSectionHeader(title: "Expression variants (placed as on each sheet head)")
            MascotFlow { ForEach(MascotParts.variants) { MascotPartTile(part: $0) } }
            MascotSectionHeader(title: "Parts row (reference shapes)")
            MascotFlow { ForEach(MascotParts.partsRow) { MascotPartTile(part: $0) } }
        }
        .padding(16)
        .background(MascotPalette.background)
    }
}

// MARK: - Rig (step 3)

/// Every control the rig exposes. Angles are degrees; a positive arm angle
/// raises that arm and a positive leg angle swings that leg outward, on either
/// side. Lengths are sheet pixels.
struct MascotRigState: Equatable {
    var expression: AppleFace.Expression = .neutral
    /// Gaze, -1...1 on each axis, added to the expression's own gaze.
    var lookX: Double = 0
    var lookY: Double = 0
    /// 0 = open, 1 = shut.
    var blink: Double = 0
    var armLeft: Double = 0
    var armRight: Double = 0
    var legLeft: Double = 0
    var legRight: Double = 0
    /// Whole body, about the point between the feet.
    var tilt: Double = 0
    var lift: Double = 0
    /// Positive squashes, negative stretches (volume roughly kept).
    var squash: Double = 0
    var leafSway: Double = 0
    var stemSway: Double = 0
    /// Both brows, up or down in sheet pixels (positive lowers): they dip behind a blink.
    var browY: Double = 0
    /// Both eyes about their centres, lids and pupils included: positive squashes (shorter,
    /// wider), negative stretches. Gives a blink squash around the shut pose.
    var eyeSquash: Double = 0
}

/// Eye settings measured from each expression head on the sheet, relative to
/// the Neutral head (character-space pixels).
struct MascotEyePreset {
    var scaleLeft: CGFloat = 1
    var scaleRight: CGFloat = 1
    var eyeShiftLeft = CGVector.zero
    var eyeShiftRight = CGVector.zero
    var pupilShiftLeft = CGVector.zero
    var pupilShiftRight = CGVector.zero
    var closedLeft = false
    var closedRight = false
}

extension AppleFace.Expression {
    var eyes: MascotEyePreset { MascotRig.eyePresets[rawValue] ?? MascotEyePreset() }

    /// The mouth / brows / closed eyes for this expression (Neutral uses the base parts).
    func variant(_ base: String) -> MascotPart? {
        guard self != .neutral else { return nil }
        let name = rawValue.prefix(1).uppercased() + rawValue.dropFirst()
        switch base {
        case "mouthNeutral": return MascotParts.variantsByID["mouth" + name]
        case "browLeft", "browRight": return MascotParts.variantsByID[base + name]
        default: return nil
        }
    }
}

enum MascotRigRenderer {
    /// Pupil travel at look = ±1, in sheet pixels.
    static let maxLook: CGFloat = 4.5

    static func draw(_ s: MascotRigState, in ctx: inout GraphicsContext) {
        let ground = MascotParts.groundShadow.anchor
        let lift = CGFloat(s.lift)
        let squash = CGFloat(s.squash)

        // Ground shadow stays on the floor and shrinks / fades as the body rises.
        var floor = ctx
        let k = max(0.45, 1 - lift / 90)
        floor.translateBy(x: ground.x, y: ground.y)
        floor.scaleBy(x: k, y: k)
        floor.opacity = Double(k)
        MascotParts.groundShadow.draw(in: &floor)

        var body = ctx
        body.translateBy(x: ground.x, y: ground.y - lift)
        body.rotate(by: .degrees(s.tilt))
        body.scaleBy(x: 1 + squash * 0.5, y: 1 - squash)
        body.translateBy(x: -ground.x, y: -ground.y)

        let e = s.expression
        let eyes = e.eyes
        let look = CGVector(dx: CGFloat(s.lookX) * maxLook, dy: CGFloat(s.lookY) * maxLook)
        let left = EyeRig(eye: MascotParts.eyeLeft, scale: eyes.scaleLeft, shift: eyes.eyeShiftLeft,
                          pupil: eyes.pupilShiftLeft + look, closed: eyes.closedLeft, squash: CGFloat(s.eyeSquash))
        let right = EyeRig(eye: MascotParts.eyeRight, scale: eyes.scaleRight, shift: eyes.eyeShiftRight,
                           pupil: eyes.pupilShiftRight + look, closed: eyes.closedRight, squash: CGFloat(s.eyeSquash))
        let limbs: [String: CGAffineTransform] = [
            "armLeft": CGAffineTransform(rotationAngle: s.armLeft * .pi / 180),
            "armRight": CGAffineTransform(rotationAngle: -s.armRight * .pi / 180),
            "legLeft": CGAffineTransform(rotationAngle: s.legLeft * .pi / 180),
            "legRight": CGAffineTransform(rotationAngle: -s.legRight * .pi / 180),
            "leaf": CGAffineTransform(rotationAngle: s.leafSway * .pi / 180),
            "stem": CGAffineTransform(rotationAngle: s.stemSway * .pi / 180),
            "browLeft": CGAffineTransform(translationX: 0, y: s.browY),
            "browRight": CGAffineTransform(translationX: 0, y: s.browY),
        ]

        for part in MascotParts.stack {
            switch part.id {
            case "groundShadow":
                continue
            case "eyeLeft", "eyeRight":
                let rig = part.id == "eyeLeft" ? left : right
                if rig.closed {
                    let closed = part.id == "eyeLeft" ? MascotParts.eyeClosedLeft : MascotParts.eyeClosedRight
                    put(closed, in: body)
                } else {
                    put(part, rig.transform(for: part), in: body)
                }
            case "pupilLeft", "pupilRight":
                let rig = part.id == "pupilLeft" ? left : right
                if rig.closed { continue }
                put(part, rig.transform(for: part, pupil: true), clip: rig.clip, in: body)
            case "lashLeft", "lashRight":
                let rig = part.id == "lashLeft" ? left : right
                if !rig.closed { put(part, rig.transform(for: part), in: body) }
                // Lids go on last, over the lid lines, for every open eye (also beside a winked one).
                if part.id == "lashRight" {
                    for r in [left, right] where !r.closed && s.blink > 0 {
                        var c = body
                        c.translateBy(x: r.eye.anchor.x, y: r.eye.anchor.y)
                        c.concatenate(r.transform(for: r.eye))
                        MascotLid.draw(over: r.eye, closure: CGFloat(s.blink), in: &c)
                    }
                }
            default:
                let p = e.variant(part.id) ?? part
                let pose = limbs[part.id] ?? part.follows.flatMap { limbs[$0] } ?? .identity
                var c = body
                MascotRenderer.clipShade(p, pose: pose, in: &c)
                put(p, pose, in: c)
            }
        }
    }

    private static func put(_ p: MascotPart, _ t: CGAffineTransform = .identity, clip: Path? = nil,
                            opacity: Double = 1, in ctx: GraphicsContext) {
        var c = ctx
        if let clip { c.clip(to: clip) }
        c.opacity = opacity
        c.translateBy(x: p.anchor.x, y: p.anchor.y)
        c.concatenate(t)
        p.draw(in: &c)
    }

    /// One eye's scale and shift (about the eye's pivot), applied to the eye and
    /// to anything sitting on it (pupil, lid line). Pupils are clipped to the eye.
    private struct EyeRig {
        let eye: MascotPart
        let scale: CGFloat
        let shift: CGVector
        let pupil: CGVector
        let closed: Bool
        var squash: CGFloat = 0

        func transform(for p: MascotPart, pupil movesPupil: Bool = false) -> CGAffineTransform {
            let dx = eye.anchor.x - p.anchor.x
            let dy = eye.anchor.y - p.anchor.y
            let extra = movesPupil ? pupil : .zero
            return CGAffineTransform(translationX: dx + shift.dx + extra.dx, y: dy + shift.dy + extra.dy)
                .scaledBy(x: scale * (1 + squash * 0.5), y: scale * (1 - squash))
                .translatedBy(x: -dx, y: -dy)
        }

        /// The eye white plus a 0.75 px margin: on the sheet the pupils run right to
        /// the eye's edge, and an exact clip would leave an anti-aliased fringe there.
        var clip: Path {
            let white = eye.silhouette
            return white.union(white.strokedPath(StrokeStyle(lineWidth: 1.5)))
                .applying(transform(for: eye).concatenating(CGAffineTransform(translationX: eye.anchor.x, y: eye.anchor.y)))
        }
    }
}

private func + (a: CGVector, b: CGVector) -> CGVector { CGVector(dx: a.dx + b.dx, dy: a.dy + b.dy) }

/// The rigged character. The drawing box covers every pose the playground sliders
/// can reach (measured over all 512 control extremes: x -20...213, y -95...204, plus
/// a 4 pt margin). A Canvas clips to its frame on iOS, so a smaller box would cut
/// off combined poses.
struct MascotRigView: View {
    var state = MascotRigState()

    static let box = CGRect(x: -24, y: -99, width: 241, height: 307)

    var body: some View {
        let box = Self.box
        Canvas { ctx, canvas in
            let s = min(canvas.width / box.width, canvas.height / box.height)
            ctx.translateBy(x: (canvas.width - box.width * s) / 2, y: (canvas.height - box.height * s) / 2)
            ctx.scaleBy(x: s, y: s)
            ctx.translateBy(x: -box.minX, y: -box.minY)
            MascotRigRenderer.draw(state, in: &ctx)
        }
        .aspectRatio(box.size, contentMode: .fit)
    }
}

/// Step 3 review: the rig with a slider for every control.
struct MascotRigPlayground: View {
    @State private var s = MascotRigState()

    var body: some View {
        VStack(spacing: 0) {
            // Pinned, so the character stays in view while the sliders scroll. The
            // stage's headroom (needed for lifts and stretches) holds the quick actions.
            ZStack(alignment: .top) {
                MascotRigView(state: s)
                    .frame(maxWidth: .infinity)
                HStack {
                    Picker("Expression", selection: $s.expression) {
                        ForEach(AppleFace.Expression.allCases) { Text($0.title).tag($0) }
                    }
                    .pickerStyle(.menu)
                    .tint(MascotPalette.appleRed)
                    Spacer()
                    Button("Reset") { s = MascotRigState() }
                    Button("Jumping") { s = .sheetJumping }
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
                .tint(MascotPalette.appleRed)
                .padding(.horizontal, 12)
            }
            .frame(height: 300)
            .padding(.vertical, 8)
            Divider()
            ScrollView {
                controls.padding(16)
            }
        }
        .background(MascotPalette.background.ignoresSafeArea())
    }

    private var controls: some View {
        VStack(alignment: .leading, spacing: 12) {
            MascotSectionHeader(title: "Face")
            control("Look ←→", $s.lookX, -1...1)
            control("Look ↑↓", $s.lookY, -1...1)
            control("Blink", $s.blink, 0...1)
            control("Brows ↑↓", $s.browY, -4...4)
            control("Eye squash", $s.eyeSquash, -0.1...0.15)

            MascotSectionHeader(title: "Limbs")
            control("Left arm", $s.armLeft, -40...100)
            control("Right arm", $s.armRight, -40...100)
            control("Left leg", $s.legLeft, -30...40)
            control("Right leg", $s.legRight, -30...40)

            MascotSectionHeader(title: "Body")
            control("Tilt", $s.tilt, -15...15)
            control("Lift", $s.lift, 0...40)
            control("Squash / stretch", $s.squash, -0.25...0.25)
            control("Leaf sway", $s.leafSway, -30...30)
            control("Stem sway", $s.stemSway, -20...20)
        }
    }

    private func control(_ title: String, _ value: Binding<Double>, _ range: ClosedRange<Double>) -> some View {
        HStack(spacing: 10) {
            Text(title)
                .font(.system(size: 13, weight: .medium, design: .rounded))
                .foregroundStyle(MascotPalette.details)
                .frame(width: 112, alignment: .leading)
            Slider(value: value, in: range)
                .tint(MascotPalette.appleRed)
        }
    }
}

// The sheets are shown at their full height; the playground scrolls its own controls.
#Preview("Parts", traits: .sizeThatFitsLayout) {
    MascotPartsSheet().frame(width: 393)
}

#Preview("Assembled", traits: .sizeThatFitsLayout) {
    MascotAssemblySheet().frame(width: 393)
}

#Preview("Rig") {
    MascotRigPlayground()
}

// MARK: - Traced art (generated — do not hand-edit)

enum MascotArt {
    static let front = TracedFigure(
        origin: CGPoint(x: 428, y: 62), size: CGSize(width: 196, height: 208),
        bodyCenter: CGPoint(x: 96.8, y: 106.5), bodyRadius: 63.8,
        faceBox: CGRect(x: 40.8, y: 58, width: 112.2, height: 80),
        layers: [
            TracedLayer(.red, .body, "M116.9 34C113.1 34.5 106.8 36.1 102.8 37.8C102.2 38 101.9 38 101.5 37.8C101 37.5 100.9 37.6 100.1 38.4C99.6 38.9 99.2 39.5 99.2 39.6C99.2 40.4 98.7 41.2 97.8 41.6C96.7 42 92.4 42.2 91.7 41.9C90.9 41.3 82.5 38.5 79.8 37.9C75.7 36.8 67.8 36.8 67.9 37.8C67.9 38.1 67.5 38.3 66 38.6C60.1 39.9 52.6 43.8 47 48.2C43.6 50.9 39 55.7 36.5 59C34.6 61.6 34 62.5 32.6 64.6C31.5 66.4 28.4 72.4 27.9 73.7C27.7 74.2 27.2 75.4 26.9 76.4C26.5 77.3 26.1 78.7 25.9 79.4C23.3 89.1 23.1 90.2 23.1 99.8C23.2 106.7 23.2 108 23.7 111.2C24 113.2 24.4 115 24.5 115.3C25 116.1 24.8 116.7 23.7 117.4C19.9 120 14.4 126.2 11.8 131C8.5 137.1 6.5 144.2 6.5 150.2C6.5 154.6 8.2 157.8 11.1 159.3C14 160.8 18.4 159.9 22.5 156.9C24.8 155.3 28 151.8 29 150C29.3 149.5 29.8 148.7 30.1 148.1C31 146.7 31.2 145 30.5 144.4C30.2 144.1 29.9 144 29.5 144.1C29 144.3 29 144.2 29 142.7C29 141.4 29.2 140.8 29.9 139.2C30.9 137.1 31 137 31.4 137.8C31.8 138.7 32.4 138.9 33 138.4C33.6 137.8 34.5 138.1 34.3 138.8C34.2 139.1 34.3 139.2 34.6 139.1C34.8 139 35 139.1 35 139.2C35 140 40.7 146.9 44.9 151.2C48.7 155.1 53.4 158.8 57.6 161.1C58.1 161.3 59.2 161.9 60.1 162.5C61.1 163.1 62.5 163.8 63.2 164.1C64 164.5 64.6 164.9 64.7 165.2C64.8 165.7 65.7 166.2 66.5 166.2C66.8 166.2 67.6 166.6 68.3 166.9C70.2 167.8 72.7 168.8 73.4 168.8C73.7 168.8 75.7 169.1 77.7 169.5C79.8 169.9 82.3 170.3 83.3 170.4C84.3 170.5 85.5 170.7 86 170.9C86.9 171.3 88.1 171.3 88.4 171.1C88.4 171 91.9 170.9 96.1 170.8C100.2 170.8 104 170.7 104.5 170.6C105.1 170.5 105.6 170.6 105.8 170.8C106.3 171.3 107.7 171.3 108.4 170.9C108.7 170.7 109.3 170.5 109.7 170.5C110.4 170.5 115 169.7 117.9 169.1C122 168.2 124 167.7 126.1 166.8C127.3 166.4 128.5 166 128.8 166C130.3 166 130.9 165.7 130.8 165.1C130.7 164.7 130.9 164.4 131.8 163.9C132.3 163.5 133 163.2 133.2 163.1C134.6 162.6 139.5 159.5 143 156.9C148.8 152.7 158 142.9 160.1 138.8C160.3 138.4 160.7 138 160.9 138C161.1 138 161.2 137.8 161.1 137.7C161.1 137.5 161.4 137.1 161.8 136.9C162.7 136.3 162.8 136.1 163.2 134.6C163.6 133.7 165 131.5 165.2 131.5C165.3 131.5 165.6 132.1 165.7 132.7C165.9 133.4 166.4 134.7 166.9 135.7C167.8 137.3 167.8 137.4 167.7 139.2C167.5 141.6 167.1 142.1 165.9 141.4C164.6 140.7 164.1 141.1 164.2 142.5C164.2 143.1 164.5 143.8 164.6 144C165.4 144.9 167.5 148.1 167.4 148.3C167.2 148.6 170 151.3 171.8 152.6C178 157 183.2 157.6 186.8 154.3C188.3 152.9 188.9 151.7 189.4 148.7C189.8 146.2 189.8 145.9 189.4 143.1C189 140.4 188 136.6 187.5 135.9C187.4 135.7 187.2 135.3 187.1 135C187 134.6 186.4 133.5 185.8 132.4C182.2 126.1 177.3 120.3 172.6 116.6C170.8 115.2 170.8 115.1 171.4 112.3C171.8 110.6 172.2 107.2 172.8 102.1C173.3 96.8 172.6 85.7 171.4 80.1C170.2 75.2 168.5 68.9 167.5 66.9C167.4 66.6 166.9 65.4 166.4 64.2C165.6 62.4 164.5 60.3 163.1 57.8C158.5 49.5 150.5 41.7 143 38.2C135.9 34.8 132.2 33.9 124.4 33.8C121.2 33.8 117.9 33.9 116.9 34Z"),
            TracedLayer(.shadow, .other, "M83 186.8C82.7 187.2 82.5 187.8 82.5 187.9C82.5 188.2 82.3 188.6 82 188.9C81.7 189.3 81.5 189.8 81.5 190.1C81.5 190.4 81.4 190.8 81.2 191C80.7 191.4 80.4 192.5 80.7 192.8C81 193.1 82.5 191.8 82.5 191.2C82.5 191 82.7 190.7 82.9 190.5C83.2 190.2 83.2 190.3 83.2 191C83.2 191.4 83.1 191.8 82.9 191.9C82.7 192 82.5 192.3 82.4 192.8C82.3 193.2 82.1 193.5 81.9 193.5C81.7 193.5 81.5 193.7 81.5 193.8C81.5 194.2 79.2 196.5 78.8 196.5C78.6 196.5 78.4 196.7 78.4 196.8C78.3 197.1 77.9 197.3 77.4 197.3C76.9 197.4 76.5 197.7 76.5 197.8C76.4 197.9 75.6 198.2 74.8 198.3C73.9 198.4 73 198.7 72.8 198.8C72.3 199.2 66.9 199.2 66.5 198.8C66.3 198.7 67.1 198.5 69.7 198.4C72.2 198.3 73.3 198.2 73.9 197.9C74.3 197.7 75 197.5 75.3 197.5C75.7 197.5 76.3 197.2 76.7 196.9C77 196.5 77.4 196.2 77.6 196.2C77.7 196.2 77.7 196.1 77.5 195.9C77.1 195.4 77 195.4 75.7 196C74.4 196.6 70.5 197.1 69 196.9C63.8 196.3 60.3 195.1 58.6 193.2C57.7 192.3 56.5 189.7 56.5 188.8L56.5 187.9L56.2 188.6C56.1 189 56.1 189.7 56.2 190C56.2 190.4 56.2 190.6 56 190.4C55.9 190.2 55.8 189.7 55.7 189.1C55.6 188.5 55.6 188.8 55.6 189.9C55.5 192.3 54.8 192.4 54.8 190C54.8 188.8 54.4 187.9 53.9 188.2C53.8 188.3 52.9 188.5 51.9 188.6C50.9 188.7 48.9 188.9 47.4 189C38.3 189.9 29.5 191.5 27.1 192.7C23.5 194.6 27 196.3 38.2 198.1C46.3 199.5 60.1 200.9 67.2 201.1C69.8 201.2 73.7 201.4 76 201.6C81.4 202 112.7 201.9 116.5 201.5C122.4 200.9 124.1 200.8 129.6 200.8C132.8 200.8 136.3 200.7 137.5 200.5C138.7 200.4 141.3 200.1 143.4 199.9C155.6 198.7 158.1 198.2 165.9 196.1C170.1 195 169.9 193.1 165.6 191.9C161.4 190.7 158.8 190.3 149.1 189.4C146.9 189.2 144.1 188.8 142.9 188.6L140.6 188.2L140.1 188.9C139.8 189.3 139.5 190 139.5 190.4C139.5 190.8 139.3 191.4 139 191.6C138.7 191.9 138.5 192.2 138.5 192.3C138.5 192.8 135.9 195 134.8 195.5C134.5 195.6 134.2 195.8 134.2 196C134.2 196.1 133.9 196.3 133.5 196.4C133.1 196.4 132.7 196.7 132.7 196.8C132.6 197.1 132.1 197.3 131.6 197.4C131.1 197.4 130.5 197.7 130.2 197.9C130 198.1 129.2 198.3 128.3 198.4C127.5 198.5 126.6 198.7 126.2 198.9C125.3 199.3 122.9 199.3 122.1 198.9C121.7 198.7 120.8 198.5 120.2 198.4C119.4 198.2 118.9 198 118.7 197.7C118.6 197.4 118.2 197.2 118 197.2C117.7 197.2 117.5 197.1 117.5 196.9C117.5 196.4 117.7 196.4 118.6 197C119.1 197.3 120.1 197.5 121.1 197.6C122.6 197.7 122.7 197.7 121.8 197.5C120 197.1 120 197 121.7 197.1C123.4 197.2 123.6 196.9 121.9 196.7C119.9 196.4 116.3 194 115.2 192.3C114.2 190.4 113 189 112.6 189C112.4 189 112.2 189.2 112.4 189.4C112.7 190.6 112.8 191.5 112.6 191.5C112.2 191.5 111.8 191.1 111.6 190.4C111.5 190.1 111.3 189.8 111.1 189.8C110.9 189.8 110.7 189.4 110.6 189C110.4 188.1 110 188.1 103.4 188C94.7 187.9 86.6 187.6 86.1 187.2C85.9 187 85.7 187 85.6 187.2C85.5 187.3 85.1 187.6 84.8 187.7C84.5 187.9 84.2 188.2 84.2 188.5C84.2 189.2 84 189.8 83.7 189.6C83.4 189.4 83.5 188.6 83.9 187.7C84.4 186.7 84.2 186.2 83.7 187.1C83.5 187.5 83.3 187.7 83.2 187.6C83.2 187.4 83.4 187 83.5 186.7C84 185.8 83.6 185.9 83 186.8Z"),
            TracedLayer(.leaf, .other, "M58.5 10.7C52.9 11.5 47.4 12.9 46.9 13.6C46.6 14.1 47.1 15.7 48.7 19C52.8 27.5 60.2 34.4 67.6 36.8C67.9 36.9 68 37.1 67.9 37.4C67.8 37.8 68.1 37.9 72.3 37.9C77.5 37.9 79.3 38.3 85.4 40.4C87.2 41 89.2 41.7 89.9 41.9C90.6 42.2 91.2 42.5 91.3 42.6C91.4 42.8 91.6 42.7 91.9 42.4C92.6 41.8 91.9 36.5 91.1 36.1C90.7 35.9 89.9 35 89.3 34C88.2 32.2 85.2 29.2 82.4 26.8C80.7 25.4 81.2 25.4 83.1 26.9C84 27.5 85.4 28.5 86.3 29C87.5 29.7 88.4 30.5 89 31.4C90.1 32.9 90.6 33 91.9 32.3C92.7 31.8 94 28.4 93.6 27.6C93.5 27.3 93.4 27.2 93.3 27.4C93.2 27.6 93 27.8 92.7 27.8C92.2 27.8 92 27.5 91.7 26.3C90.6 22.8 88.4 19.1 86 16.9C83.1 14.2 77.7 11.8 72.2 10.8C68.9 10.2 62.5 10.2 58.5 10.7Z"),
            TracedLayer(.red, .other, "M63.5 170.2C63.3 170.7 63 170.9 63 170.9C62.9 170.8 62.6 171.6 62.2 172.6C60.2 179.1 59.1 182.2 57.9 184.4C56.1 187.8 55.8 189.7 56.7 191.8C58.2 195.1 62.4 197.1 69 197.7C70.8 197.8 74.6 197.3 75.9 196.7C76.5 196.5 77.1 196.2 77.3 196.2C78 196.2 81.2 193.1 81.4 192.2C81.5 191.8 81.7 191.4 81.9 191.2C82.1 191.1 82.2 190.7 82.2 190.4C82.2 190.1 82.5 189.5 82.8 189.2C83 188.8 83.2 188.2 83.2 187.9C83.2 187.6 83.4 186.9 83.6 186.4C84.1 185.1 84.8 183.2 85.1 181.8C85.3 181 85.7 179.6 86 178.6C86.4 177.1 86.4 176.8 86.1 176.3C85.6 175.5 85.1 175.4 84.3 175.9C83.7 176.4 83.6 176.4 83 176C82.7 175.7 81.5 175.4 80.4 175.2C79.3 175.1 78.3 174.9 78.2 174.8C78 174.7 77.4 174.5 76.8 174.4C75.2 174.2 73.8 173.7 71.2 172.4C70 171.8 68.9 171.2 68.8 171.2C68.3 171.2 65.8 170.1 65.6 169.8C65.3 169.2 64 169.5 63.5 170.2Z"),
            TracedLayer(.red, .other, "M130 169.2C128.7 169.6 127 170.4 124.8 171.7C123.3 172.6 121.9 173.3 121.5 173.4C121.1 173.5 120.7 173.7 120.6 173.8C120.5 173.9 120.3 174 120.1 174C119.9 174 119.3 174.2 118.8 174.4C118.3 174.6 117.7 174.9 117.4 175C117.1 175.2 116.6 175.3 116.2 175.5C115.8 175.7 115.4 176 115.2 176.5C115 177 114.8 177.2 114.1 177.3C113.7 177.4 112.9 177.7 112.5 178.1L111.7 178.6L111.1 177.8C110.4 176.9 109.6 176.8 108.9 177.4C108.6 177.8 108.6 178 108.9 179.2C109.1 180 109.4 180.8 109.5 181.1C109.6 181.4 110 182.5 110.4 183.6C110.8 184.7 111.2 186 111.5 186.5C111.7 187 112 187.8 112.1 188.3C112.2 188.9 112.6 189.8 113 190.3C113.4 190.9 114.2 191.9 114.6 192.6C115.5 194 117.2 195.4 119.1 196.4C120.9 197.3 126.4 197.4 129.2 196.5C130.3 196.2 131.7 195.8 132.5 195.6C133.2 195.3 133.8 195.1 133.8 194.9C133.8 194.7 134.3 194.2 135 193.6C135.7 193.1 136.7 192 137.2 191.3C138.1 190 138.1 189.8 138.1 188C138.1 186.2 137.8 185.2 136.6 182.6C136.2 181.8 134.5 176.6 133.2 172.2C132.4 169.8 132.2 169.3 131.7 169.2C131.1 169 130.5 169 130 169.2Z"),
            TracedLayer(.stem, .other, "M109.6 7C107.1 7.4 103.5 10.2 100.1 14.4C97 18.1 95.1 21.8 93 28.2C92.2 30.3 91.8 31.3 91.7 31C91.6 30.7 91.5 30.7 91.4 31C91.1 32.1 90.2 36.3 90.2 37C90.3 37.8 90.3 37.8 90.6 37.3C90.9 36.8 90.9 37 91.2 39.2C91.4 40.5 91.4 41.8 91.4 42.1C91.2 42.6 91.4 42.7 92.3 42.8C93.9 43 97.5 42.6 98.5 42.1C99.2 41.7 100 40.6 100 39.9C100 39.5 100.9 38.5 101.2 38.5C101.5 38.5 101.5 38.3 101.4 37.9C101.3 37.5 101.4 37 101.6 36.7C101.8 36.4 102 36 102 35.8C102 35.2 103.9 31.3 105.2 28.9C107.6 24.6 110.7 20.6 113.9 17.5C116.4 15 116.8 14.2 116.3 12C115.6 8.7 112.8 6.5 109.6 7Z"),
            TracedLayer(.redShade, .other, "M130 164.7C129.8 165.1 129.5 165.2 128.9 165.2C128.4 165.2 127 165.6 125.8 166.1C123.8 166.9 121.7 167.5 117.6 168.3C114.8 168.9 110.1 169.8 109.4 169.8C109 169.8 108.5 169.9 108.1 170.2C107.5 170.6 107.4 170.6 106.6 170.2C106.1 169.9 105.7 169.8 105.6 169.8C105.6 169.8 105.9 170.6 106.2 171.4C106.7 172.2 107 173.1 107 173.4C107 173.7 107.2 174.6 107.5 175.2C107.8 175.9 108 176.7 108 177C108 177.2 108.4 177.9 108.9 178.5L109.8 179.6L109.6 178.7C109.4 177.4 109.8 177.4 110.9 178.7L111.7 179.6L112.6 178.9C113.1 178.6 113.8 178.2 114.2 178.1C115.6 177.8 115.7 177.7 115.9 177C116 176.4 116.2 176.2 116.9 176.1C117.4 176 117.8 175.8 117.8 175.7C117.8 175.6 118 175.5 118.2 175.5C118.5 175.5 118.8 175.4 118.9 175.3C119 175.2 119.4 175 119.8 174.9C120.2 174.8 120.8 174.6 121.2 174.3C121.6 174.2 122 174 122.1 174C122.3 174 123.5 173.3 125 172.5C129.4 169.9 131 169.4 131.6 170.2C132.6 171.9 132.4 169.6 131.2 166.4C130.4 164.3 130.3 164.2 130 164.7Z"),
            TracedLayer(.redShade, .other, "M64.8 165C64.8 165.4 64.6 166.1 64.4 166.4C63.9 167.4 62.8 170.9 62.8 171.6C62.8 172.8 63.1 172.8 63.7 171.5C64.1 170.7 64.5 170.2 64.8 170.2C65 170.2 65.2 170.3 65.2 170.4C65.2 170.7 68 172 68.5 172C68.7 172 69.8 172.5 71 173.1C73.6 174.4 74.9 174.9 76.5 175.2C77.1 175.2 77.8 175.4 77.9 175.5C78.1 175.7 79 175.8 80 176C82.4 176.3 82.7 176.4 82.9 176.9C83.1 177.4 83.9 177.3 84.5 176.8C85.1 176.2 85.5 176.3 85.5 177.2C85.5 177.5 85.6 177.8 85.8 177.8C86.3 177.8 86.8 176.6 87.9 172.5C88 171.9 88.3 171.1 88.5 170.8C88.8 170.2 88.8 170.2 88 170.3C87.4 170.4 86.8 170.4 86.2 170.2C85.8 170 84.6 169.7 83.5 169.7C82.5 169.6 80 169.1 78 168.7C75.9 168.3 74 168 73.6 168C73 168 70.5 167.1 68.6 166.2C67.9 165.8 67 165.5 66.6 165.5C66.2 165.5 65.7 165.2 65.4 164.8L64.8 164.2L64.8 165Z"),
            TracedLayer(.redShade, .other, "M164.8 130.7C163.5 132.2 162.2 134.4 162.2 135.3C162.2 135.5 162 135.9 161.6 136.2C160.7 136.7 159.8 137.6 159.8 137.8C159.8 137.9 160.2 138 160.7 138C161.7 138 161.7 138 161.9 139.1C162.3 141.4 166.6 148.2 168 148.8C168.9 149.2 168.9 148.9 167.7 147.1C166.6 145.3 166.6 145.3 165.7 144.1C165.2 143.6 164.6 141.8 164.9 141.8C164.9 141.8 165.3 142 165.9 142.2C166.8 142.7 166.8 142.7 167.5 142.2C168.8 141.3 168.9 137.6 167.8 135.6C167.4 134.8 166.8 133.4 166.4 132.3C165.8 130.3 165.4 129.9 164.8 130.7Z"),
            TracedLayer(.leafVein, .other, "M73.4 21.4C73.2 21.8 75.1 23.1 78 24.8C83.6 28.1 89 33.6 89.9 37L90.2 38.1L90.6 37.3C91.3 36 92.1 32.1 91.8 31.3L91.6 30.6L91.3 31.3C90.9 32.2 90.4 32.2 89.8 31.2C89.1 30 88.4 29.4 86.1 27.9C85 27.2 83.3 26.1 82.4 25.5C78.1 22.6 73.9 20.7 73.4 21.4Z", gradient: (87.9, 29.9, 86.4, 32.3, "#3A8035", "#287B2B")),
            TracedLayer(.redShade, .other, "M30.3 136.8C28.8 139.2 28.2 140.8 28.2 142.8C28.2 144.8 28.5 145.3 29.4 145C30.2 144.7 30.3 145 29.9 146.5C29.7 147.2 29.7 147.8 29.8 147.8C30.7 147.8 32.5 144.3 33.4 140.8C33.8 139.5 33.9 139.3 34.6 139C35.6 138.7 35.7 138.5 35 137.9C34.2 137.1 33.1 137 32.8 137.6C32.4 138.1 32.1 137.9 31.9 137C31.6 135.9 30.9 135.9 30.3 136.8Z", gradient: (29.6, 140.7, 32.2, 141.4, "#D71325", "#D5050C")),
            TracedLayer(.white, .face, "M62.2 80.2C61.3 80.3 60.2 80.6 59.8 80.8C59.4 81.1 58.9 81.2 58.7 81.2C58.4 81.2 56.3 82.3 54.8 83.1C53.7 83.7 50.6 86.4 50.7 86.6C50.8 86.7 50.6 87 50.4 87.2C49.6 88.1 47.7 91.1 47 92.6C42.8 101.6 43.6 111.3 49.1 118.2C51.6 121.2 54.3 123.2 57.3 124.3C59.8 125.1 65.1 125.2 68 124.5C71.2 123.6 74.5 121.9 76.6 120C77.1 119.5 77.7 119 77.9 118.9C78.1 118.8 78.2 118.6 78.1 118.5C78.1 118.4 78.2 118.2 78.4 118C78.9 117.6 78.9 116.9 78.4 116.5C78.1 116.2 77.8 116.2 77.1 116.7C76.6 117 75.3 117.3 74.3 117.5C66.9 118.7 61 112.6 60.9 103.8C60.9 101.5 61.6 98.3 62.3 97C62.4 96.8 62.7 96.2 62.9 95.8C64.3 92.5 66.5 90.2 69.7 88.7C72 87.6 75.4 87.4 77.1 88.2C78.4 88.8 79 88.7 79 87.7C79 87.2 76 84 75.5 84C75.4 84 74.9 83.7 74.3 83.3C73.8 83 72.5 82.3 71.5 81.8C70.5 81.3 69.5 80.8 69.4 80.6C69 80.2 64.4 80 62.2 80.2Z"),
            TracedLayer(.white, .face, "M128 78.2C127.4 78.3 126.4 78.7 125.8 79.2C125.2 79.7 124.6 80 124.5 80C124.3 80 123.9 80.2 123.6 80.5C123.2 80.7 122.2 81.4 121.4 81.9C117.9 84.2 114.1 89.6 112.9 93.8C112.1 96.5 112 96.9 111.9 99.8C111.6 105.3 112.5 109.8 114.8 113.6C119.2 120.8 127.6 124.3 135.2 122.1C138.1 121.3 139.2 120.9 139.2 120.7C139.2 120.6 139.7 120.3 140.3 120C141.4 119.4 145.7 115.5 145.7 114.9C145.7 114.8 145.8 114.3 145.8 114C145.9 113.1 145.2 112.8 144.3 113.4C140.6 116.1 135 115.2 131.1 111.3C128.9 109.1 127 104.2 127 100.8C127 99.4 127.9 94.5 128.4 93.4C130 89.5 132 87.2 135.2 85.5C136.8 84.7 140.5 84.5 141.8 85.1C143 85.6 143.5 85.3 143.5 84.1C143.5 83.4 143.3 83.2 142.2 82.5C141.4 82 141.1 81.6 141.2 81.5C141.5 81.3 141.1 81.1 138.4 79.7C136.2 78.5 135 78.2 132.1 78.2C130.5 78.1 128.6 78.1 128 78.2Z"),
            TracedLayer(.dark, .face, "M78.2 87.3L78.2 87.9L77.3 87.4C75.7 86.6 71.7 86.9 69.4 88C66.2 89.5 63.6 92.2 62.1 95.5C61.9 96 61.7 96.5 61.5 96.8C61.4 97 61.1 98 60.7 99.1C59.6 102.9 60.1 107.7 61.9 111.6C62.8 113.4 65.6 116.4 67.4 117.3C70 118.7 75 118.8 77.2 117.5L78 117L78.1 117.7C78.1 118.3 78.4 118.1 80.3 115.6C83.2 112 84.5 109.4 85 105.8C85.6 102.1 84.9 97.8 83.1 93.6C82.6 92.4 79.7 88 78.9 87.2L78.2 86.7L78.2 87.3Z"),
            TracedLayer(.dark, .face, "M142.9 83.2C142.8 83.2 142.8 83.6 142.8 84C142.8 84.7 142.8 84.7 142 84.3C140.8 83.7 136.5 84 135 84.8C130.3 87.2 127.8 90.8 126.8 96.8C126.2 100.2 126.1 101.4 126.7 104C128 110.8 133.3 115.8 139.2 115.8C141.2 115.8 143.3 115.1 144.5 114.2L145.1 113.7L145.2 114.4L145.4 115L145.9 114.3C146.5 113.5 149 108.4 149 108C149 107.8 149.2 107.4 149.4 107C149.6 106.6 150 105 150.2 103.4C151.1 97.4 149.2 90.8 145.5 86.6C144.8 85.9 144 84.8 143.8 84.1C143.2 82.9 143.2 82.9 142.9 83.2Z"),
            TracedLayer(.dark, .face, "M107.8 117C104.2 118.6 102.4 119 98.6 119C95.2 119 93.7 118.7 88.8 117.2C86.1 116.4 84.1 117.4 82.7 120.2C81.7 122 82.4 127.8 83.9 130.3C85.3 132.8 89.4 136.5 89.9 135.7C90 135.6 90 134.8 89.9 134L89.7 132.5L90.8 131.4C91.6 130.7 92.5 130.1 93.7 129.7C96.1 128.8 96.4 128.7 99.4 128.7C101.6 128.7 102.2 128.8 103.1 129.2C105.8 130.6 106 133.6 103.5 135.4C103.2 135.6 103 136.1 103 136.3C103 137 103.7 137.8 104 137.3C104.1 137.2 104.4 137 104.6 136.9C105.5 136.6 108.8 133.7 110.1 132.1C112.5 129.2 114.5 123.9 114.6 120.6C114.6 116.2 112.3 114.9 107.8 117Z"),
            TracedLayer(.pink, .face, "M145.5 120.4C141.3 120.8 136.8 123.3 135.5 125.8C134.9 126.8 134.8 129.4 135.3 130.3C136.4 132.5 138.7 133.6 142.1 133.6C148.9 133.6 154.1 128.9 152.8 124C152.2 121.8 148.8 120.1 145.5 120.4Z", blur: 0.6),
            TracedLayer(.pink, .face, "M45.5 124.3C43.8 124.8 42.4 125.8 41.5 127.2C39.8 129.9 41.1 132.6 45.2 134.6L47.1 135.6L51 135.6C54.4 135.6 55 135.6 56.1 135.1C58.7 133.9 59.5 131.3 58 128.9C56.1 125.5 53.9 124.3 49.1 124.1C47.5 124 46.2 124.1 45.5 124.3Z", blur: 0.6, gradient: (48.5, 125.1, 51.1, 134.8, "#FA5960", "#FB4553")),
            TracedLayer(.pink, .face, "M97.4 128C94.4 128.2 92 129.2 90.3 130.9L88.9 132.2L89.1 133.9C89.2 134.8 89.3 135.7 89.4 135.8C89.6 135.9 90.8 136.4 92.2 137L94.9 138.1L98.5 137.9C100.5 137.8 102.4 137.7 102.8 137.6C103.1 137.6 103.5 137.6 103.7 137.6C104 137.5 104 137.3 103.9 136.8C103.8 136.3 103.8 136 104 136C104.1 136 104.6 135.4 105.1 134.8C106.3 133.1 106.4 131.6 105.3 130.1C103.9 128.2 101.7 127.7 97.4 128Z"),
            TracedLayer(.dark, .face, "M124.1 58.2C122.5 58.8 121 60.1 121 61.1C121 61.4 121.3 61.9 121.7 62.3C122.5 63.1 123.6 63.2 125.6 62.6C128.6 61.7 132.8 62.7 135.9 65.2C137.8 66.7 138.6 66.9 139.4 66.4C142.3 64.5 139 60.7 132.5 58.6C131 58.1 130.2 58 127.7 58C126 58 124.4 58.1 124.1 58.2Z"),
            TracedLayer(.dark, .face, "M62.6 62C59.6 62.4 55.8 64.5 53.6 66.9C52.6 68.1 52.4 68.9 52.9 69.7C54 71.4 54.9 71.4 56.7 69.8C60.1 66.6 61.8 66 66.8 65.9C70.4 65.8 70.6 65.8 71.1 64.7C71.7 63.8 71.1 62.6 69.9 62.1C69 61.7 64.9 61.7 62.6 62Z"),
            TracedLayer(.dark, .face, "M62.5 80C58.6 80.3 55.1 82 52 84.9C50.9 85.9 50.6 86.4 50.7 86.8C50.8 87.2 50.9 87.2 51.6 86.5C52.6 85.7 54.4 84.2 55.1 83.8C56.2 83.2 58.7 82 59.1 81.9C59.4 81.8 60.1 81.6 60.8 81.3C61.7 81 62.7 80.9 65.7 80.9C68.3 80.9 69.5 80.8 69.4 80.7C69.2 80.1 65.6 79.7 62.5 80Z"),
            TracedLayer(.dark, .face, "M128.5 78C125.7 78.5 125.7 79.3 128.4 78.9C130.8 78.6 134.6 78.9 136.1 79.5C137.7 80.2 139.8 81.2 140.3 81.7C140.7 82 140.8 82 141.1 81.7C141.4 81.4 141.3 81.2 140.3 80.4C137.5 78.3 136.5 77.9 132.9 77.8C131.1 77.8 129.1 77.9 128.5 78Z"),
            TracedLayer(.white, .face, "M76.1 91.2C73 92.2 73 96.5 76.2 97.5C77.3 97.9 78.5 97.4 79.4 96.4C80.6 94.7 80 92.4 77.9 91.4C77 91 76.9 90.9 76.1 91.2Z"),
            TracedLayer(.white, .face, "M141 88.4C140.1 88.8 139.2 90.2 139.2 91.2C139.2 92.8 141.2 94.8 142.7 94.8C144.1 94.8 145.8 92.4 145.4 90.9C145.2 90 144 88.7 143.1 88.3C142.1 87.9 141.8 87.9 141 88.4Z"),
        ])

    static let neutral = TracedFigure(
        origin: CGPoint(x: 24, y: 419), size: CGSize(width: 177, height: 169),
        bodyCenter: CGPoint(x: 74.2, y: 102), bodyRadius: 60.3,
        faceBox: CGRect(x: 29, y: 57.5, width: 124.8, height: 87.3),
        layers: [
            TracedLayer(.red, .body, "M115.2 31.9C110.3 32.3 100.6 35 97.6 36.8C96.9 37.2 96.6 37.2 96.6 37C96.2 36 94.5 37.6 93.3 40C92.7 41.2 92.1 42 91.7 42.2C89.9 43.1 84.4 42.1 77.8 39.6C76.4 39.1 68.4 37.3 65.4 36.8C61.5 36.2 54.1 36.2 51.4 36.8C46 38 45.8 38.1 45.9 38.5C46 38.8 45.6 39 44.4 39.5C42.5 40.2 36.7 43 35.3 43.9C30.9 46.8 28.4 48.8 25 52.2C19.5 57.8 14.1 65.8 12 71.3C11.7 72 11.2 73.2 11 73.9C10.5 75.1 9.4 78.3 8.7 80.6C7.8 83.3 7 88.3 6.6 93C5.9 101.4 7 109.6 9.9 118.5C16.6 138.5 33.1 154 53.4 159.2C64.2 162.1 71 162.9 82.9 162.8C95.7 162.8 105.2 161.8 116.1 159.2C118.4 158.6 124.9 156.4 127.2 155.3C127.6 155.2 128 155 128.1 155C128.3 155 134.7 151.8 135.8 151.2C138.1 149.8 143.5 146.1 144 145.5C144.1 145.4 145.1 144.6 146.2 143.6C153.7 137.4 160.5 128.9 163.9 121.5C165.5 118.1 166.7 115.2 167.5 112.6C170 104.4 170.9 98.6 170.9 90.2C170.9 84.1 170.7 81.8 169.6 76.1C169.4 75 169.1 73.6 169 72.9C168.9 72.3 168.6 71.2 168.4 70.6C166.6 65 165.8 62.8 165 61C164.4 59.9 164 58.9 164 58.8C164 58.3 159.8 51.7 158.1 49.6C150.5 40.1 142.8 35.2 131.5 32.7C128.3 32 127.8 31.9 122.2 31.9C119 31.8 115.9 31.8 115.2 31.9Z"),
            TracedLayer(.leaf, .other, "M42 10.8C36.2 11.5 30.1 13.1 22.9 15.7C20.8 16.5 20.5 16.7 20.5 17.3C20.5 17.9 23 21.2 26.1 24.6C27.2 25.8 28.5 27.2 28.9 27.7C31.6 30.8 40.2 36.1 44.4 37.4C45.4 37.7 45.9 37.9 45.8 38.1C45.6 38.7 46.2 38.8 47.8 38.4C53.6 37 59.5 36.7 65.1 37.6C68.2 38.1 76.1 39.8 77.5 40.4C78 40.5 79.9 41.2 81.7 41.8C85.6 43.1 85.8 43 85.8 40.6L85.8 39.1L84.5 38C83.8 37.4 82.1 35.8 80.8 34.6C77 31.2 74.8 29.6 69.4 26.5C67.3 25.3 67.4 25.3 70.7 26.2C74.3 27.2 78.3 29.5 81.2 32.1C81.9 32.7 82.6 33.2 82.7 33.2C82.8 33.2 83 33.5 83.1 33.8C83.6 34.8 84.2 34.9 84.8 34.3C85.2 33.7 85.5 32.8 85 33.1C84.9 33.2 84.6 32.7 84.4 32.1C81.8 24.5 78.4 20 72.3 16C68.4 13.4 64.5 11.9 59 11C56.5 10.5 45.4 10.5 42 10.8Z"),
            TracedLayer(.stem, .other, "M102.1 8.8C99.7 10 95.7 13.6 92.9 17.3C90.3 20.7 86.6 28.7 85.9 32.6C85.8 33 85.6 33.2 85.4 33.2C84.8 32.9 84.6 33.5 84.4 35.8C84.3 36.9 84.2 38.2 84.1 38.6C84 39.2 84 39.3 84.4 39.2C85.1 39.1 85.2 41.6 84.6 42.2C84.3 42.6 84.4 42.7 86.5 43C87.7 43.2 89.4 43.3 90.3 43.2C92.4 43.1 92.9 42.7 94.1 40.1C94.7 38.8 95.2 38.1 95.8 37.8C96.6 37.3 96.7 36.8 96.1 36.7C95.8 36.6 95.8 36.5 96.1 36C96.3 35.7 96.8 34.7 97.2 33.8C100.3 27.3 103.4 23 107.5 19.2C110 17 110.5 16.2 110.5 14.5C110.5 12 109.5 10.1 107.5 8.8C106.2 8 103.9 8 102.1 8.8Z"),
            TracedLayer(.leafVein, .other, "M61.4 23.4C61.5 23.5 62.3 23.9 63.1 24.2C64.5 24.8 70.3 27.8 70.9 28.3C71.1 28.4 72.1 29 73.2 29.7C75.8 31.3 77.5 32.7 80.7 35.5C82.1 36.9 83.4 38 83.5 38C83.6 38 83.8 38.3 83.9 38.6C84.2 39.9 84.9 39.1 85.1 37.1C85.4 34.9 85.4 33.4 85.2 33.4C85.1 33.4 84.8 33.1 84.6 32.8C84.2 32.1 84.2 32.1 84.4 32.7C84.4 33 84.4 33.4 84.3 33.7C84.1 34.3 83.8 33.7 83.6 32.1C83.5 31.2 83.3 30.4 83.2 30.3C83.1 30.2 83 30.4 83.1 30.9C83.2 31.3 83.1 31.8 82.9 32.1C82.6 32.5 82.6 32.5 82.1 32C80.6 30.1 74.9 26.7 71.9 25.8C65.5 23.8 60.5 22.7 61.4 23.4Z", gradient: (77.5, 35.3, 78.9, 28.2, "#388D36", "#387D38")),
            TracedLayer(.white, .face, "M54 81.1C50.7 81.7 47.4 83.3 44.1 85.9C41.6 88 40.7 88.9 40.9 89.2C40.9 89.3 40.8 89.6 40.6 89.8C40.4 89.9 40.1 90.3 39.9 90.7C39.7 91.1 39.1 92.3 38.4 93.4C37.8 94.5 37.1 95.8 37 96.4C36.8 96.9 36.6 97.5 36.5 97.6C36.4 97.8 36.1 98.9 35.7 100.1C34.3 105.4 35.2 113.4 37.7 117.9C39.9 121.8 44.2 125.8 48 127.2C50 128 53.6 128.8 55.4 128.8C58 128.8 62.9 127.6 65.7 126.3C67.7 125.4 72.6 121.7 72.4 121.2C72.3 121.2 72.4 120.9 72.6 120.8C73.1 120.3 73.1 119.9 72.6 119.5C72.2 119.2 72.1 119.2 71.4 119.6C68.7 121.2 63.2 120.7 60.1 118.6C56.8 116.4 55.4 114.4 54.4 110.4C53.2 105.9 53.7 101.2 56 96.7C59.2 90.3 64.7 87.2 70.3 88.6C71.5 88.9 71.9 88.9 72.2 88.7C72.7 88.3 72.6 87.9 71.5 86.8C69 84.4 64.3 81.9 61.4 81.4C60.9 81.3 60.5 81.1 60.5 81C60.5 80.7 56 80.8 54 81.1Z"),
            TracedLayer(.white, .face, "M126.5 77.6C126.4 77.7 125.9 77.8 125.3 77.8C124.7 77.8 124.3 77.9 124.3 78C124.4 78.1 123.7 78.6 122.8 79.1C117 82.1 114.1 85.1 111.1 90.6C109.8 93 109.3 94.7 108.7 97.8C107 107.8 111.1 117.7 118.8 121.8C122 123.6 123.2 123.9 127.2 123.9C131.5 123.8 132.6 123.6 136.2 121.8C138 120.9 139.1 120.2 140.8 118.5C143.1 116.3 143.7 115.3 142.9 114.5C142.6 114.2 142.3 114.3 140.6 115.1C138.8 116 138.5 116.1 136.2 116.1C130.5 116.2 126.3 112.5 124.5 106C123.2 101.6 123.7 96.9 125.9 92.5C128 88 131.2 85.4 135.2 84.6C137.1 84.2 139.5 84.4 140.9 85C142 85.5 142.7 84.3 142 83C141.2 81.4 136.2 78.8 132.8 78C130.6 77.5 126.8 77.3 126.5 77.6Z"),
            TracedLayer(.dark, .face, "M71.8 87.7C71.8 88.2 71.7 88.2 70.5 87.8C61.8 85.5 53.1 94.6 53 105.9C53 112.7 56.2 118 61.9 120.4C64.7 121.6 69.8 121.6 71.6 120.3C72.2 119.9 72.2 119.9 72.2 120.5C72.3 121.1 72.4 121 73.3 120C73.8 119.4 74.8 118.2 75.3 117.5C75.9 116.8 76.5 116 76.7 115.8C77.3 115.1 78.7 111.8 79.2 109.7C79.7 107.8 79.8 107 79.7 104.5C79.5 98 77.6 93.5 72.9 88.4C72 87.3 71.8 87.2 71.8 87.7Z"),
            TracedLayer(.dark, .face, "M125.6 77.4C124.6 77.8 124.4 78 124.5 78.3C124.5 78.7 124.7 78.8 125.2 78.6C129.7 77.6 135.6 79 139.9 82.1C141.2 83 141.5 83.4 141.5 84.1C141.5 84.4 141.4 84.4 141 84.3C140 83.7 137.2 83.5 135.4 83.8C130.2 84.6 125.5 89.4 123.8 95.5C123.1 98.3 123 99.5 123.1 101.9C123.4 108.8 126.8 114.2 132.2 116.3C133.3 116.8 134.1 116.9 136.2 116.9C138.8 116.8 139 116.8 140.7 115.9L142.5 115L142.5 115.7C142.5 116 142.6 116.2 142.6 116.2C142.9 116.2 143.8 115.4 143.8 115.1C143.8 114.9 143.9 114.7 144.1 114.5C144.7 114.1 147.2 108.7 147.9 106.5C150 100.1 148.8 93 144.7 86.9C144.1 86.1 143.4 85 143.2 84.5C142.3 82.2 137.3 78.5 133.7 77.5C131.3 76.8 127.5 76.8 125.6 77.4Z"),
            TracedLayer(.pink, .face, "M35.1 129.1C32.6 129.7 30.4 131.5 29.4 133.6C28.8 134.9 28.9 137.6 29.6 139.1C31.6 143.4 38.7 145.8 44.7 144.3C48.2 143.3 50.4 141.5 51.2 138.8C51.8 137.1 51.8 137 51.4 135.5C50.6 132.8 48.5 130.9 44.7 129.6C42.5 128.8 37.3 128.5 35.1 129.1Z", blur: 0.6),
            TracedLayer(.pink, .face, "M144.1 119.9C140.8 120.7 135.6 124.1 133.9 126.5C131.6 129.9 132.5 133.6 136.1 135.3C137.5 135.9 137.9 136 140.2 136C146.8 136 152.7 131.9 153.6 126.7C154 124.7 152.4 121.9 150.1 120.6C149.2 120 148.6 119.9 146.8 119.8C145.6 119.8 144.4 119.8 144.1 119.9Z", blur: 0.6, gradient: (136.4, 125.1, 150.1, 131, "#FD6F75", "#FD5D68")),
            TracedLayer(.dark, .face, "M103.8 114.8C103.2 115 102.2 115.6 101.6 116C97 119.2 90.3 119.5 85.7 116.8C83.6 115.6 81.9 115.5 80.8 116.6C80.1 117.3 80 117.5 80 118.9C80 123.4 84.8 127.4 90.7 128.1C98 128.8 103.9 125.7 106.4 119.7C107.3 117.5 107.2 115.6 106 114.8C105 114.2 105.1 114.2 103.8 114.8Z"),
            TracedLayer(.dark, .face, "M56.4 61.2C51.5 62.3 47.8 64.2 45.2 66.9C43.3 68.9 43.1 70 44.2 71.2C44.9 71.9 45.3 72.1 46.3 72C46.6 72 47.5 71.3 48.3 70.5C51.7 67.3 54.2 66.2 59.2 66C62.5 65.9 62.5 65.9 63.1 65.1C64.2 63.8 63.7 62.1 61.9 61.3C61.1 61 57.5 60.9 56.4 61.2Z"),
            TracedLayer(.dark, .face, "M123.6 57.9C120.5 58.5 119.5 61.4 122 62.5C122.5 62.7 123 62.7 123.8 62.5C127.4 61.7 131.3 62.6 135.5 65.3C137.6 66.6 138.4 66.8 139.3 65.9C140.5 64.8 140.3 63.8 138.5 61.9C135 58.4 128.8 56.8 123.6 57.9Z"),
            TracedLayer(.dark, .face, "M53.5 80.9C51.1 81.3 49 82.2 46.7 83.6C43.1 86.1 40.3 88.8 41 89.3C41.3 89.4 41.5 89.3 41.9 88.9C42.9 87.8 46.4 85 48 84.2C51.7 82.2 55.6 81.3 58.9 81.6C60.4 81.8 60.5 81.7 60.5 81.3C60.5 81 60.3 80.8 60 80.6C59 80.4 55.5 80.5 53.5 80.9Z"),
            TracedLayer(.white, .face, "M68.9 92.5C67.6 93.3 67 94.3 67 95.6C67 96.8 67.1 96.9 68.2 97.9C69.2 98.8 69.5 99 70.4 99C71.8 99 72.3 98.7 73.2 97.5C74.2 96.2 74.2 95 73.5 93.8C72.4 92.1 70.4 91.5 68.9 92.5Z"),
            TracedLayer(.white, .face, "M139.1 88.2C138.8 88.3 138.2 88.8 137.8 89.3C136.3 91 136.9 93.1 139.1 94.5C140.2 95.1 140.8 95 142 94.1C143.6 92.8 143.9 91.4 142.9 90C141.8 88.4 140.4 87.7 139.1 88.2Z"),
        ])

    static let happy = TracedFigure(
        origin: CGPoint(x: 218, y: 410), size: CGSize(width: 175, height: 178),
        bodyCenter: CGPoint(x: 95.8, y: 107.5), bodyRadius: 62.2,
        faceBox: CGRect(x: 30, y: 61.5, width: 125.8, height: 87.5),
        layers: [
            TracedLayer(.red, .body, "M109.8 34.2C109.4 34.2 108 34.4 106.5 34.7C103.4 35.1 99.9 36 97.4 36.9C96.4 37.3 95.2 37.7 94.7 37.9C94.2 38.1 93.2 38.6 92.5 39C91.4 39.7 91.1 39.8 90.7 39.5C90.5 39.4 90.2 39.2 90.1 39.2C89.8 39.2 88.2 40.8 88.2 41.2C88.2 41.9 87 44.2 86.3 44.7C84.9 45.7 83.3 46.1 81.4 45.9C80.5 45.8 79.6 45.7 79.4 45.5C79.3 45.4 78.9 45.2 78.7 45.2C78.4 45.2 76.6 44.8 74.7 44.3C65.2 41.7 61.9 41.1 53.6 40.6C50.9 40.4 49.6 40.7 49.9 41.4C50 41.6 49.7 41.8 49.1 41.9C48.6 41.9 46.6 42.5 44.6 43.2C31.6 47.4 19.7 58.1 12.8 71.6C9.9 77 8.1 82.9 6.6 90.9C5.9 94.4 5.9 104.9 6.6 109C8.9 123.6 14.6 135.8 23.8 146.2C29.5 152.4 34 156.2 40.5 160.2C47.4 164.3 58 168.1 65.7 169.2C66.8 169.4 67.7 169.6 67.8 169.6C68.5 170.1 78.5 170.8 84.2 170.8C98 170.8 108 169.3 118.5 165.8C123.2 164.2 123.8 163.9 126.1 162.9C127.1 162.4 128 162 128.1 162C128.2 162 131.6 160.1 133.2 159.1C133.7 158.8 138.2 155.8 139.8 154.7C143.6 152 150.2 145.7 153.6 141.2C158.1 135.5 161.2 130.2 163.5 124.6C163.7 123.9 164.2 122.8 164.5 122.1C164.9 120.9 165.5 119.1 166.5 115.6C169 106.7 169.4 91.2 167.4 81.9C164 66.2 159.3 57 150.2 48C145.7 43.4 141.8 40.8 134.7 37.7C132 36.5 127.6 35.3 123.6 34.6C121.2 34.2 111.3 33.9 109.8 34.2Z"),
            TracedLayer(.leaf, .other, "M44 12.4C37 13.1 28.4 15.1 27.8 16.2C27.2 17.3 30.6 24 34 28.6C37.6 33.5 45.1 39.3 49.4 40.6C49.7 40.7 49.9 40.9 49.9 41.1C49.8 41.3 50.5 41.4 52.6 41.4C59.4 41.5 64.5 42.3 74.4 45C76.4 45.6 78.2 46 78.5 46C78.8 46 79 46.1 79 46.2C79 46.8 79.8 46.5 80 45.9C80.4 44.8 80 41.9 79.4 41.7C78.6 41.3 78.2 40.4 78.8 40C79 39.9 79.3 39.3 79.4 38.5C79.5 37.8 79.7 37.2 79.9 37.2C80.5 37.2 80.8 36.6 80.9 34.9C81.1 33.4 81 33.2 80.7 33.4C80 33.7 79.4 32.7 79.1 31.2C78.2 26.7 74 20.2 70.4 17.8C66.7 15.3 61.1 13.3 55.8 12.6C53.3 12.3 46.6 12.2 44 12.4ZM67 28.7C67.8 29 68.8 29.5 69.4 29.9C69.9 30.2 71.1 30.8 72 31.3C74 32.2 75 33 76.2 34.3C76.8 35 77.2 35.2 77.6 35.2C78.1 35 78.1 35.4 77.6 36.1C77.4 36.4 77.2 37.2 77.2 38L77.2 39.4L76.8 38.7C76.6 38.4 75.5 37.2 74.4 36.2C73.2 35.2 71.1 33.2 69.5 31.8C68 30.3 66.3 28.9 65.9 28.5C64.9 27.8 65.4 27.8 67 28.7Z"),
            TracedLayer(.stem, .other, "M94.9 8.8C93 9.5 91.3 10.9 89.5 13.2C85.8 17.8 81.6 27 80.9 32.2C80.8 32.8 80.6 33.4 80.4 33.5C80.3 33.7 80.1 34 80.1 34.4C80.1 34.8 80.1 35.4 80 35.9C80 36.6 80 36.6 79.8 36L79.6 35.4L79.3 36C79.1 36.3 78.9 37.5 78.7 38.7C78.6 39.9 78.4 41.2 78.4 41.7C78.2 42.5 78.2 42.5 78.7 42.4C79.2 42.2 79.2 42.3 79.3 43.7C79.4 44.5 79.3 45.4 79.2 45.7C78.9 46.5 78.9 46.5 81.2 46.7C83.6 46.8 85.5 46.4 86.9 45.2C87.7 44.5 89 42.2 89 41.4C89 41 90 40.1 90.6 39.9C90.8 39.8 90.8 39.7 90.5 39.4C90.2 39.1 90.2 38.9 90.6 38.2C90.8 37.8 91.2 36.6 91.6 35.6C92.3 33.8 93.9 30.6 95.2 28.2C95.9 27 97 24.9 97.9 23.4C98 23.1 98.8 21.9 99.5 20.8C100.3 19.6 101.2 18.2 101.5 17.7C102.2 16.5 102.4 14.1 102 12.6C101.6 11.1 99.9 9.2 98.3 8.7C96.8 8.1 96.5 8.1 94.9 8.8Z"),
            TracedLayer(.leafVein, .other, "M57.4 24.2C57.1 24.7 57.4 24.9 59.9 26.1C64 28.2 65.7 29.2 67.8 31.2C71.1 34.2 75.3 38.1 75.5 38.2C75.6 38.3 76 38.9 76.5 39.5C76.9 40.2 77.4 40.8 77.6 40.8C77.8 40.9 78.1 41.4 78.2 41.9C78.3 42.5 78.4 42.7 78.6 42.5C79.1 42.1 79.5 40.4 79.6 37.8C79.8 35.4 79.8 35.4 79.3 35.9C79 36.2 78.8 37.1 78.7 38C78.6 38.8 78.4 39.5 78.2 39.5C77.9 39.5 78 36.8 78.4 36.4C78.7 36.1 78.7 35.7 78.6 34.1C78.4 32.3 78 31.2 78 32.6C78 32.9 77.9 33.5 77.7 33.9L77.5 34.6L76.6 33.6C75.4 32.3 74.4 31.7 72.1 30.5C70.2 29.5 69.4 29 68.8 28.6C68.5 28.4 67.7 28 66.8 27.7C65.4 27.1 62.4 25.7 59.7 24.3C58.9 23.9 57.6 23.9 57.4 24.2Z"),
            TracedLayer(.dark, .face, "M103.8 116.2C103.6 116.2 102.3 116.8 101 117.5C95.6 120.2 92.5 120.7 85.1 120.2C79.6 119.9 78.7 120 77.3 121.2C76 122.3 75.7 123.4 75.8 126.2C76.2 131.3 81.1 139.1 84.6 139.9C85.4 140.1 85.5 139.7 84.9 138.1C83.7 134.8 87.2 131 93.1 129.3C98.8 127.6 103.6 130.1 102.1 134C101.5 135.8 101.5 136.1 101.9 136.6C102.2 137.1 102.2 137.1 103.5 135.8C106.4 132.6 108.5 126.9 108.5 122C108.5 117.9 106.3 115.2 103.8 116.2Z"),
            TracedLayer(.pink, .face, "M39.9 129C34.3 130.5 30.2 135 30.2 139.6C30.2 144.8 35.6 148.8 42.5 148.8C49.3 148.8 54.7 144.4 55 138.6C55.1 134.8 53.3 132.2 48.8 130.1C46.4 128.9 46.4 128.9 43.5 128.8C41.9 128.8 40.3 128.9 39.9 129Z", blur: 0.6),
            TracedLayer(.pink, .face, "M142.2 111.8C139.6 112.4 136.6 114 135.2 115.4C129.6 121 130 127.4 136 130.2C137.2 130.8 137.8 130.8 140.3 130.9C143.6 131.1 146 130.6 148.2 129.3C157.4 124.2 158.2 114.3 149.6 111.7C147.7 111.1 144.5 111.1 142.2 111.8Z", blur: 0.6, gradient: (143.4, 113.1, 143.5, 129.1, "#FC6F77", "#FD616E")),
            TracedLayer(.dark, .face, "M56 99.3C48.7 99.9 42.4 105.2 39.6 113.2C38.8 115.5 38.6 118.3 39.1 119.6C39.8 121.3 41.8 121.6 43.2 120.2C43.8 119.6 45 116.5 45 115.6C45 115.4 45.5 114.2 46.1 112.9C48.4 108 53.1 105.1 58.2 105.3C63.4 105.6 66.9 107.5 70.4 112.2C71.9 114.1 72.4 114.4 74 114.2C77 113.7 76.6 110.1 73.1 106.2C68.5 101.3 62.2 98.7 56 99.3Z"),
            TracedLayer(.dark, .face, "M124.1 90C120.6 90.4 115.4 93.2 112.7 96.1C111.4 97.5 109.5 100 109.1 100.9C108.9 101.3 108.6 101.8 108.5 102C108 102.8 107 105.4 106.9 106.3C106.6 108.3 107.7 109.8 109.6 109.8C110.8 109.8 111.8 109.1 112.4 107.7C112.7 107.1 113.4 105.8 113.9 104.7C115 102.5 118.1 98.9 120 97.9C122.7 96.3 124.2 95.9 127.4 95.9C129.8 95.9 130.6 96 131.8 96.5C135 97.7 137.6 99.7 139.7 102.4C141.5 104.8 141.7 105 142.6 105C143.1 105 143.6 104.7 144.3 104C145.3 103 145.3 103 145.2 101.7C145.1 100 144.2 98.6 141.6 96.1C137.6 92.1 133.3 90.1 128.4 89.9C126.9 89.8 124.9 89.9 124.1 90Z"),
            TracedLayer(.pink, .face, "M92.5 128.6C86.2 130.6 83 134.5 84.2 138.5C84.6 139.9 84.7 140 85.3 140C85.7 140 86.3 140.2 86.6 140.3C88.5 141.6 94.5 141.4 97.5 140.1C98.3 139.7 100.2 138.3 101.2 137.3C101.4 137.2 101.7 137 102 137C102.6 137 102.8 136.8 102.5 136.2C102.3 135.9 102.4 135.6 102.6 135.1C103.9 132.6 103 130.1 100.4 128.7C98.8 127.9 95 127.8 92.5 128.6Z"),
            TracedLayer(.dark, .face, "M117.9 61.8C112.9 62.4 110.4 65 112.8 67C113.7 67.8 114.2 67.9 115.4 67.4C117.8 66.4 122.7 66.4 125.1 67.5C127.4 68.6 129.8 67.8 129.8 65.8C129.8 63.2 123.5 61.1 117.9 61.8Z"),
            TracedLayer(.dark, .face, "M51.9 71C47.7 72 43 75.1 42 77.5C41.5 78.6 41.9 79.7 43.1 80.3C44 80.8 44 80.8 44.9 80.3C45.5 80 46.1 79.5 46.4 79.2C47.5 78 51.1 76.2 53.5 75.6C54.8 75.3 56.2 75 56.6 75C57.5 75 58.8 73.8 58.8 72.9C58.8 72 58.1 71 57.4 70.8C56.4 70.4 53.8 70.5 51.9 71Z"),
        ])

    static let excited = TracedFigure(
        origin: CGPoint(x: 421, y: 410), size: CGSize(width: 181, height: 178),
        bodyCenter: CGPoint(x: 83.2, y: 109.5), bodyRadius: 64.2,
        faceBox: CGRect(x: 32.5, y: 58, width: 126.5, height: 96),
        layers: [
            TracedLayer(.red, .body, "M114 32.7C110.5 33 105.4 34 103.5 34.7C100.7 35.7 98.4 36.6 95.6 38C94 38.8 92.6 39.4 92.6 39.2C92.4 38.8 91.6 39 91.1 39.4C90.8 39.7 90.4 40.4 90.1 41.1C89.4 43.3 89 43.8 87.5 44.3C86.4 44.7 85.8 44.8 84.4 44.6C83.4 44.5 82 44.4 81.1 44.3C79.6 44.2 75.4 43.2 73.9 42.7C73.2 42.3 71.2 41.8 67.8 40.9C60.7 39 53.6 38.5 53.7 39.8C53.7 40.1 53.5 40.2 53.2 40.2C53 40.2 51.8 40.5 50.6 40.9C49.4 41.3 47.9 41.7 47.2 41.9C45.1 42.5 40.2 44.8 37.1 46.7C27.4 52.6 19.2 61.5 14.1 71.7C12 75.8 11.5 77.1 10 81.5C8.5 86.1 8.2 87.1 7.8 89.5C7.7 90.6 7.4 92.2 7.2 92.9C6.9 95 6.7 105.6 7 109.3C7.7 118 10.1 126.5 14.4 135C15.5 137 16.4 138.8 16.6 139C16.8 139.2 17 139.5 17 139.6C17 139.9 20.7 145.1 22.8 147.7C26.4 152.1 33 157.9 38.1 161.3C38.7 161.6 39.8 162.3 40.6 162.8C42.4 164 47.9 166.8 50.1 167.6C51.1 168 52.1 168.4 52.4 168.5C54.7 169.6 60 171 65.6 172C67.1 172.3 68.5 172.6 68.7 172.6C69 172.7 71.4 173 74 173.2C84.9 174.3 101.1 173.6 110.8 171.4C116.8 170.2 122.9 168.4 125.2 167.4C125.6 167.2 126.1 167 126.3 167C126.5 167 126.9 166.8 127.1 166.7C127.4 166.5 127.9 166.2 128.2 166.1C129.2 165.8 137.2 161.8 138.5 161C139.1 160.6 139.8 160.2 140 160.1C140.6 159.8 145.7 156.1 147.8 154.4C151.6 151.2 156.9 145.7 160.8 140.6C162.9 137.8 168 129.7 168 129.1C168 129 168.2 128.5 168.5 127.9C169.7 125.1 170 124.5 170 124.2C170 124 170.2 123.4 170.5 122.9C170.8 122.3 171 121.7 171 121.4C171 121.2 171.2 120.7 171.4 120.3C171.7 119.7 172.4 117 173.4 112.5C174.4 108 175.1 100 174.9 94.5C174.6 85.5 172.4 75.3 169.4 68.6C169.2 68.1 169 67.6 169 67.4C169 67.3 168.9 66.9 168.7 66.6C168.5 66.3 168.2 65.8 168.1 65.5C168 65.2 167.3 63.8 166.5 62.3C165.7 60.9 165 59.7 165 59.6C165 58.8 158.7 51 155.5 47.7C151.7 43.9 149.3 42 145 39.5C137.5 35.2 133.1 33.8 124.5 32.8C119.8 32.2 118.7 32.2 114 32.7Z"),
            TracedLayer(.leaf, .other, "M45.9 11C41.9 11.3 34 13.1 33.2 13.8L32.6 14.2L33.5 16.6C35.4 22.2 39.3 28.6 42.9 31.9C45 34 51.1 38 53.2 38.8C53.7 38.9 53.8 39.1 53.6 39.5C53.5 40 53.5 40.1 54.7 39.9C56.3 39.7 60.7 40.1 63.2 40.6C66.7 41.3 72.5 42.9 73.7 43.4C74.5 43.8 78.8 44.8 80.3 45.1C81.6 45.3 81.8 44.7 81.6 41.6C81.4 39 81.2 38.4 80.5 38.5C80.1 38.6 78.4 37.1 77.2 35.4C75.8 33.5 72.2 29.4 71.1 28.5C70 27.5 67.1 25.6 66.3 25.4C65.8 25.2 65 24.5 65.4 24.5C65.5 24.5 66.5 25.1 67.8 25.8C69.1 26.5 70.4 27.3 70.8 27.5C71.1 27.7 72.7 28.8 74.2 30C75.8 31.1 77.4 32.2 77.8 32.4C78.6 32.8 79 33.4 79 34.3C79 34.7 79.2 35.2 79.5 35.5L80 36.1L80.9 35.6C81.9 35.1 82 34.9 83.1 30.8C83.5 29.4 83.5 28.2 83 29C82.9 29.2 82.6 29.2 82.2 29.1C81.7 29 81.5 28.7 81.2 27.3C78.9 19 72 13.6 60.7 11.5C57.6 10.9 49.6 10.6 45.9 11Z"),
            TracedLayer(.stem, .other, "M96.9 8.8C94 9.9 90.2 14 87.4 18.9C84.9 23.2 83.4 26.8 81.6 33.2C81.3 34.4 81.1 34.7 81 34.3C80.9 34.1 80.8 33.9 80.8 34C80.6 34.6 80 39.3 80 39.9L80.1 40.6L80.4 39.9C80.7 39.2 80.7 39.2 80.8 41C80.9 43.4 80.9 44 80.6 44.7C80.5 45.2 80.6 45.2 81.4 45.2C82 45.2 83.2 45.3 84.2 45.4C86.5 45.6 88.6 45.1 89.4 44.2C90 43.5 90.9 41.7 91.1 40.7C91.2 40.3 91.6 39.9 91.9 39.8C92.5 39.5 92.7 39 92.2 39C91.9 39 92 38.3 92.5 37.3C92.8 36.8 93 36.2 93 36C93 35.8 93.2 35.3 93.4 34.8C96.5 28 98.7 24.1 101.2 21.4C101.7 20.9 102.7 19.8 103.5 19C105.9 16.5 106.2 15.1 105.2 12.7C103.5 8.9 100.3 7.4 96.9 8.8Z"),
            TracedLayer(.leafVein, .other, "M61.9 23C61.7 23.3 62.2 24 62.7 24C62.8 24 63.2 24.2 63.4 24.4C63.8 24.8 64.5 25.2 66 26C67.1 26.6 69.3 28 70.3 28.8C71.4 29.7 75 33.8 76.8 36.2C77.5 37.2 78.2 38 78.5 38.1C79 38.4 79.3 38.9 79.7 40L79.9 40.9L80.4 39.8C81 38.4 81.4 35.9 81.1 34.7L81 33.9L80.6 34.6C80.2 35.4 79.8 35.1 79.8 34C79.8 33.2 79 32.2 78 31.7C77.7 31.5 76 30.4 74.5 29.2C72.9 28.1 71.4 27 71 26.8C70.7 26.6 69.5 25.9 68.3 25.2C64.8 23.2 62.3 22.3 61.9 23Z"),
            TracedLayer(.white, .face, "M56.1 86.5C51 87.6 47.3 89.6 42.9 93.7C42.3 94.3 41.8 94.9 41.9 95C42 95.1 41.6 95.9 41.1 96.7C37 102.9 35.1 111.6 36.6 117.9C38.1 124.2 39.7 127.2 43.2 130.8C47.6 135.1 51.1 136.7 56.4 136.9C59.3 137.1 60.2 136.9 63.4 136.2C67.1 135.2 72 132.2 75 128.9C75.7 128.1 76.2 127.4 76.2 127.3C76.2 127.2 76.2 126.9 76.4 126.7C76.5 126.4 76.4 126.1 76.2 125.8C75.8 125.4 75.6 125.5 73.9 126.4C72 127.3 71.9 127.4 69.3 127.4C63 127.3 58.8 124 56.5 117.4C55.3 114 55.3 109.2 56.4 105.5C58.1 99.6 60.9 96.6 66.2 94.3C67.3 93.9 70.8 93.7 72.7 94C73.1 94.1 73.4 93.9 73.6 93.7C74 93.1 73.5 92.3 72.1 91.4C68.5 89 67.2 88.3 64.4 87.5C63.4 87.1 62.5 86.8 62.5 86.6C62.5 86.2 57.7 86.2 56.1 86.5Z"),
            TracedLayer(.white, .face, "M128.2 79.1C128.1 79.3 127.7 79.5 127.2 79.6C126.5 79.8 124.1 80.8 123.2 81.2C123.1 81.4 122.5 81.7 122 82C118 84.2 113.2 91.3 111.6 97.5C110.5 102 111 109.5 112.9 114.2C114.8 119 118.7 123.3 123 125.4C126.3 127 128.5 127.4 132.3 127.2C136.5 126.9 139.9 125.5 143.6 122.5C145.5 121 148.3 118 147.8 118C147.7 118 147.8 117.9 148 117.7C148.4 117.3 148.3 116.6 147.9 116.2C147.6 116 147.1 116.1 145.3 117L143.1 118.1L140 118.1C136.9 118.1 136.8 118.1 135.1 117.2C132 115.7 130 113.5 128.5 110.1C127.8 108.5 127 104.4 127 102.4C127 100.8 127.8 95.8 128.2 95.1C128.3 94.8 128.8 93.9 129.2 93.1C130.6 90.1 132.6 87.9 135.4 86.4C136.8 85.6 136.9 85.6 140.4 85.6C144 85.6 144.5 85.5 144.5 84.8C144.5 83.2 139 79.8 135.4 79.2C133.2 78.8 128.3 78.8 128.2 79.1Z"),
            TracedLayer(.dark, .face, "M73 92.8C73 93.4 73 93.4 72.2 93.2C71.1 92.8 67.1 93.1 65.9 93.6C62.9 94.9 62 95.5 60.1 97.4C53.1 104.4 53 118.1 59.9 124.5C62.8 127.2 65.2 128.1 69.3 128.1C72.1 128.1 72.2 128.1 74 127.2C75.7 126.3 75.7 126.3 75.8 126.8C75.9 127.3 76 127.3 76.4 126.5C76.7 126.1 77.5 124.9 78.2 123.9C80.7 120.7 81.9 117.6 82.2 114C82.3 112.7 82.4 111.2 82.3 110.6C81.6 103 80 99.4 75.2 94.4C73.2 92.3 73 92.2 73 92.8Z"),
            TracedLayer(.dark, .face, "M129.2 78.5C128.5 78.7 128.2 78.9 128.2 79.3C128.2 79.8 128.3 79.8 130 79.7C132.9 79.4 136.3 80 138.8 81.2C141.3 82.4 143.2 83.6 143.5 84.3C143.9 85 143.7 85.1 142 84.8C139.6 84.5 136.7 84.9 135 85.7C132.4 87.1 129.8 89.8 128.4 92.9C128 93.7 127.6 94.6 127.5 94.8C127.3 95.1 127 96.5 126.8 97.9C125.1 107 128.2 114.8 135 118C136.6 118.8 136.7 118.9 140 118.9L143.4 118.9L145.5 117.8L147.5 116.8L147.5 117.4C147.5 117.8 147.6 117.9 147.8 117.9C148.1 117.7 149.8 115.1 149.8 114.8C149.8 114.6 150.2 113.5 150.8 112.3C152.7 108.3 152.9 107.3 152.9 103.2C152.9 96.9 151 91.6 147.4 87.5C146.7 86.8 145.8 85.6 145.4 85C142.9 81 137.3 78.2 132.2 78.3C131.1 78.3 129.7 78.4 129.2 78.5Z"),
            TracedLayer(.dark, .face, "M109.5 121.2C109.2 121.3 108.2 121.8 107.4 122.1C102.5 124.3 100 124.9 95.2 124.8C92.9 124.8 91.4 124.7 90.4 124.4C89.6 124.2 88.1 124 87.1 124C85.5 124 85.2 124.1 84.2 124.8C83.6 125.3 82.9 126.2 82.4 127C81.7 128.3 81.7 128.5 81.8 131C82 133.8 82.6 136.4 83.6 138C85.6 141.4 86.7 142.7 87.9 142.8L88.6 142.9L88.6 141.1C88.7 136.9 92.3 134.6 98.6 134.8C101.5 134.9 101.7 134.9 102.8 135.6C104.8 137 105.5 138.9 104.6 140.5C104.2 141.2 104.1 142.8 104.5 142.8C105.5 142.8 108.6 140.1 110.3 137.8C111.3 136.4 112.7 133.3 113.4 131C114.1 128.6 114.4 124.1 113.8 123.1C113.1 121.7 110.9 120.8 109.5 121.2Z"),
            TracedLayer(.pink, .face, "M39 138.2C32.6 139.9 30.4 146.2 34.7 150.4C37.3 153.1 40.5 154.2 44.6 153.9C48.2 153.7 51.2 152.7 53.1 151C55.2 149.1 55.8 145.5 54.4 143.1C53.1 141 49.6 138.6 46.9 138C45.4 137.7 40.6 137.7 39 138.2Z", blur: 0.6),
            TracedLayer(.pink, .face, "M151.1 121.8C147.9 122.2 145.6 123.2 141.9 126C137.9 129.1 136.6 133.2 139 135.8C140.8 137.8 141.7 138.1 145.5 138.1C149.1 138.1 150.5 137.8 153.2 136.3C154.8 135.4 157.6 132.6 158.2 131.2C159 129.8 159.2 126.5 158.7 125.2C157.5 122.4 155.1 121.3 151.1 121.8Z", blur: 0.6),
            TracedLayer(.pink, .face, "M93.2 134.7C91.5 135.2 91 135.5 89.8 136.7C88.1 138.3 87.7 139.4 87.8 141.6C87.9 142.9 87.9 142.9 89.2 143.6C90 143.9 90.7 144.3 90.9 144.5C91 144.6 91.9 144.9 92.9 145.1C94.6 145.6 94.9 145.6 97.9 145.2C101.1 144.8 101.9 144.5 103 143.5C103.4 143.2 103.9 142.9 104.3 142.8C104.9 142.7 105 142.6 105 142C105 141.7 105.2 141.1 105.4 140.8C106.2 139.3 105.6 136.9 104.1 135.7C102.3 134.2 101.6 134 98.2 134C95.6 134 94.8 134.1 93.2 134.7Z"),
            TracedLayer(.dark, .face, "M124.8 58.1C120.3 59 118.2 61.4 120.2 63.3C121.1 64.1 121.7 64.1 123.5 63.6C125.5 63 129.7 63 131.6 63.6C133.6 64.2 134.4 64.6 136.2 65.9C138 67.2 139.1 67.4 140.1 66.3C142.2 64 139.2 60.8 132.9 58.7C131.4 58.2 126.2 57.9 124.8 58.1Z"),
            TracedLayer(.dark, .face, "M54.6 66.2C51 67 47.8 68.7 45.2 71.2C42.3 74.2 41.6 76.1 43 77.5C44 78.5 45 78.2 46.7 76.3C49.8 72.8 53.1 71.2 58 70.8C61.2 70.5 61.9 70.1 62 68.4C62 67.4 61.9 67.2 61.2 66.6C60.5 66 60.3 66 57.8 66C56.3 66 54.9 66.1 54.6 66.2Z"),
            TracedLayer(.dark, .face, "M54.2 86.5C49 88.2 46.9 89.5 43.9 92.5C41.9 94.5 41.7 94.8 42.1 95C42.5 95.3 42.7 95.2 43.2 94.5C44.4 92.9 47.7 90.5 50.6 89.1C53.8 87.6 57 86.9 60.3 87C62.2 87.1 62.5 87.1 62.5 86.7C62.5 85.8 56.9 85.7 54.2 86.5Z"),
            TracedLayer(.white, .face, "M70 98.1C68.7 99.1 68.3 101.4 69.3 103C69.9 103.8 71.5 104.8 72.4 104.8C73.1 104.8 74.6 103.8 75.2 103C76.2 101.6 76 100.3 74.7 98.9C73.6 97.8 73.5 97.8 72.1 97.8C71.2 97.8 70.4 97.9 70 98.1Z"),
            TracedLayer(.white, .face, "M142.1 89.3C140.8 89.9 140 91.1 140 92.6C140 94.6 141.5 96 143.6 96C144.6 96 144.8 95.9 145.8 95C147.3 93.5 147.4 92.3 146.1 90.8C145 89.4 143.3 88.8 142.1 89.3Z"),
        ])

    static let curious = TracedFigure(
        origin: CGPoint(x: 632, y: 410), size: CGSize(width: 176, height: 178),
        bodyCenter: CGPoint(x: 79, y: 109.2), bodyRadius: 62.5,
        faceBox: CGRect(x: 38.5, y: 57.8, width: 117.3, height: 96.2),
        layers: [
            TracedLayer(.red, .body, "M110 34.7C104.2 35.3 97.1 37.3 93.9 39C93.1 39.5 92.8 39.6 92.4 39.4C91.7 38.9 90.7 40 89.9 42.1C88.4 45.8 87.7 46.2 83.7 46.2C82.2 46.2 81 46.2 80.9 46C80.8 45.9 80.2 45.8 79.5 45.7C78.8 45.5 77.2 45.2 75.9 44.8C73.4 44 72.2 43.7 67.5 42.5C65.9 42.1 64.4 41.7 64.2 41.6C63.9 41.4 53.9 40.2 52.5 40.2C51.3 40.2 50.7 40.6 50.9 41.1C51 41.3 50.5 41.5 49.4 41.7C47.9 42 44.7 42.9 43.4 43.5C39.5 45.2 34.2 48.1 30.9 50.4C27.7 52.6 20.8 59.3 18.8 62.1C18.3 62.8 17.5 63.8 17 64.4C16.2 65.6 13 70.6 13 70.8C13 70.9 12.6 71.9 12 73C9.4 78.8 7.8 84.1 6.6 91.2C5.9 95 6 105.7 6.6 109.8C7.4 114.5 8.3 118.5 9.8 123C10.4 124.9 10.8 126 11.9 128.6C13 131.4 16.7 138.1 18.7 141.1C24.2 148.8 31.9 156.2 39.8 161.1C42.7 162.9 47.4 165.4 49.1 166.1C57.4 169.1 62.2 170.3 70 171.3C75.9 172.1 87.8 172.1 93.9 171.4C104.8 170.2 114.2 168.3 120 166.2C120.5 166.1 121.5 165.7 122.1 165.5C125.8 164.2 128 163.2 131.2 161.6C133.2 160.6 135.1 159.6 135.3 159.3C135.5 159.2 135.7 159 135.8 159C136 159 140.3 156.1 142.1 154.8C151.2 148 160.2 136.8 164.2 127.4C164.8 126.2 166.5 121.1 167.5 117.8C170.2 108.8 170.5 93.9 168.2 83.1C167.5 79.9 165.8 74.1 165 72C164.7 71.2 164.3 70.2 164.2 69.8C161.2 61.8 153.8 51.8 146.1 45.4C144 43.5 142.5 42.5 139.2 40.7C132.8 37.1 128.3 35.6 121.2 34.8C116.8 34.2 114.1 34.2 110 34.7Z"),
            TracedLayer(.leaf, .other, "M43.8 11.1C38.3 11.8 29.4 13.8 29 14.5C28.7 15 28.9 16 29.7 17.7C30 18.5 30.5 19.7 30.8 20.4C31.6 22.2 34 26.3 35.4 28.4C38.4 32.8 46.3 38.9 50.2 40C51.1 40.2 51.2 40.3 51 40.6C50.6 41.1 50.9 41.2 52.1 41.1C53.1 40.9 63.5 42.1 64 42.4C64.1 42.4 65.6 42.8 67.3 43.2C71.9 44.4 73.2 44.7 75.7 45.5C76.9 45.9 78.5 46.3 79.2 46.4C79.9 46.5 80.5 46.7 80.5 46.8C80.5 46.9 80.7 47 80.9 47C81.6 47 81.8 46 81.6 43.8C81.4 41.9 81.3 41.6 80.8 41.3C80 40.9 79.2 40.2 78.4 38.9C77 36.7 68.9 29 66.6 27.6C65.5 27 64.4 26.2 64 26.1C62.9 25.4 63.7 25.5 65.5 26.3C67.5 27.1 67.6 27.2 70.6 29.1C72.5 30.3 73.2 30.8 74.9 31.7C75.2 31.9 76.3 32.8 77.2 33.8C78.2 34.7 79.2 35.5 79.4 35.5C79.6 35.5 79.9 35.8 80.1 36.1C80.9 37.3 81.8 36.6 82.1 34.7C82.3 33.8 82.2 33.7 81.5 33.1C81.1 32.8 80.8 32.2 80.8 32C80.8 30.4 77.6 23.5 75.9 21.2C73 17.5 68.8 14.5 63.9 12.8C60.1 11.5 57.9 11.2 51 11.1C47.5 11.1 44.2 11.1 43.8 11.1Z"),
            TracedLayer(.stem, .other, "M97 8.7C95.6 9.1 93.6 10.6 92.4 12C91.5 13.1 89 16.7 89 16.8C89 16.9 88.6 17.6 88.1 18.4C85.9 22.1 84.1 26.8 82.7 32C82.5 32.9 82.2 33.4 82 33.4C81.6 33.4 81.4 34.3 80.5 39.4C80 42.4 80 43.7 80.4 42.5C80.6 42 80.7 42.2 80.8 43.8C80.9 45 80.9 46 80.8 46.2C80.6 46.5 80.5 46.8 80.5 46.8C80.5 46.9 81.9 47 83.6 47C88.1 47 89 46.4 90.6 42.3C91.2 40.9 91.5 40.4 92.1 40.1C92.7 39.8 92.7 39.7 92.5 39.3C92.2 39.1 92.4 38.6 93.1 36.9C93.6 35.7 94 34.7 94 34.6C94 34.4 97.2 28.1 97.9 26.9C98.2 26.3 98.7 25.5 98.9 25.1C99.1 24.7 100.3 22.9 101.5 21.1C104.1 17.1 104.6 15.9 104.4 14C104.2 12.2 103.7 11.2 102.6 10.1C100.9 8.4 99.2 7.9 97 8.7Z"),
            TracedLayer(.leafVein, .other, "M60 24C60 24.3 60.9 25.2 61.2 25.2C61.4 25.2 62.1 25.7 62.9 26.2C63.7 26.8 65.3 27.7 66.4 28.4C68.5 29.7 76.5 37.3 77.6 39C77.9 39.5 78.5 40.3 78.9 40.8C79.4 41.3 79.8 42 79.8 42.4C79.8 42.7 79.9 43 80 43C80.4 43 81 41.4 81.4 39C81.6 37.7 81.9 36 82 35.2C82.2 34 82.2 33.7 82 33.5C81.7 33.3 81.6 33.6 81.4 34.5C81.2 35.2 81 35.8 80.9 35.9C80.8 36 80.3 34.4 80.2 33.6C80.2 33.3 80.1 33.4 80 33.9C79.8 34.4 79.6 34.8 79.5 34.8C79.4 34.8 78.5 34 77.5 33C76.6 32 75.5 31.1 75.2 30.9C73.5 30 72.7 29.6 70.9 28.4C67.8 26.3 67.7 26.3 65.3 25.4C64.1 24.9 62.8 24.3 62.3 24.1C61.4 23.7 60 23.6 60 24Z"),
            TracedLayer(.white, .face, "M62.1 87.5C59 87.9 56.5 88.8 53.7 90.4C51.9 91.5 49.7 93.2 49.9 93.5C49.9 93.6 49.6 94 49.2 94.4C48.1 95.5 45.5 99.2 45 100.5C44.9 100.8 44.6 101.4 44.4 101.8C44.2 102.1 44 102.6 44 102.8C44 103 43.9 103.4 43.7 103.8C43.5 104.2 43.2 104.8 43.1 105.3C43 105.8 42.7 106.8 42.5 107.8C41.7 110.3 41.7 116.8 42.6 119.9C44.8 128.1 50.2 133.8 57.8 136.3C60.8 137.2 65.7 137.3 68.8 136.3C70.1 136 71.3 135.6 71.5 135.5C71.7 135.4 72.5 135 73.2 134.7C74.5 134 77.4 131.9 78.7 130.7C79.6 129.8 82.4 126.3 82.5 125.9C82.5 125.7 82.6 125.5 82.7 125.3C83.1 124.2 82 123.7 81.1 124.5C80 125.5 79.2 125.9 77.5 126.5C72.3 128.1 66.5 125.6 63.6 120.4C62.3 118 62 117 61.5 114.3C60.5 108.2 62.6 101.2 66.6 97.5C69.5 94.9 73.8 93.6 76.5 94.5C77.8 95 78.6 93.8 77.6 92.8C76.4 91.7 71.9 89.1 69.9 88.5C69.4 88.3 69 88.1 69.1 88C69.4 87.5 64.5 87.2 62.1 87.5Z"),
            TracedLayer(.white, .face, "M128.5 78.5C127.9 78.7 127.2 78.8 126.9 78.8C126.7 78.8 126.6 79 126.6 79.2C126.7 79.4 126.6 79.5 126.3 79.5C125 79.5 120.6 82.6 118.5 84.9C115.7 88.1 113.7 92.7 112.8 98.3C112 103 112.1 106 113.6 111.4C116 120.4 123.4 126.8 131.8 126.8C138.1 126.8 143.5 123.9 146.8 118.8C147.5 117.9 148 117 148 116.9C148 116.9 148.4 116.1 148.9 115.2C150.6 112.2 149.8 110.3 147.8 112.3C145.6 114.4 141.8 114.8 138.7 113.4C134.7 111.5 132.4 108.1 130.4 101.2C129.7 98.7 130.2 91.6 131.2 89.6C131.3 89.3 131.8 88.4 132.2 87.5C133.2 85.5 133.5 85.1 135.2 83.8C136.5 82.8 137.5 82.4 139.3 82.4C141.5 82.3 141.2 80.4 139.1 79.8C138.2 79.5 137.8 79.3 137.8 79.1C137.9 78.9 137.8 78.8 137.6 78.8C137.3 78.8 136.5 78.7 135.8 78.5C134.2 78.2 130.1 78.2 128.5 78.5Z"),
            TracedLayer(.dark, .face, "M77.2 93.4C77.3 94 77.3 94 76.6 93.8C76.3 93.6 75.3 93.5 74.4 93.5C71.3 93.5 68.7 94.6 66.1 97C62.9 100 61.4 103.4 60.6 108.8C60.3 111.5 60.3 111.9 60.7 114.4C61.3 117.7 61.9 119.2 63.8 122.2C64.6 123.4 67 125.5 68.4 126.3C72.5 128.5 78.3 128.1 81.3 125.3L82 124.7L82 125.3C82 125.9 82.1 126 82.4 125.8C82.6 125.6 82.8 125.2 82.9 124.9C83 124.6 83.6 123.4 84.3 122.2C86.5 118.3 86.9 116.8 86.9 111.9C86.9 108.2 86.8 107.3 86.3 105.6C85.2 101.8 83.4 98.8 80.4 95.4C77.9 92.8 76.8 92.1 77.2 93.4Z"),
            TracedLayer(.dark, .face, "M139.7 80.2C139.6 80.3 139.6 80.5 139.8 80.8C140.2 81.4 140.1 81.8 139.4 81.6C138.2 81.3 136.3 82 134.8 83.1C133.1 84.5 132.6 85.1 131.5 87.2C131.1 88.1 130.6 89.1 130.5 89.3C129.4 91.4 128.9 98.8 129.7 101.5C131.5 107.6 133.1 110.3 136.4 112.9C138.3 114.3 139.6 114.8 142.2 114.9C144.8 115.1 146.5 114.5 148 113.1C149.1 112.1 149.2 112.1 149.3 112.8C149.5 113.3 149.6 113.1 150 112C152.7 104.7 152.8 97.9 150.2 91.8C149.3 89.8 149 89.1 147 86.2C145 83.2 144.2 82.4 141.8 81C139.9 79.9 139.8 79.9 139.7 80.2Z"),
            TracedLayer(.dark, .face, "M101.5 119.2C98.7 119.6 96.7 120.5 94.9 122.2C92.9 124.1 92.3 126 92.8 128.9C93.2 131.7 94.6 132.7 97.8 132.7C100.7 132.7 101.7 133.9 100.6 136.3C100.1 137.5 100.3 138.2 101.8 139.2C104.2 141 107.4 139.5 107.8 136.4C108.4 132.2 108.2 132.6 109.7 131.9C111.2 131.2 111.8 130.4 112.4 128.7C113.6 125.1 111.8 120.8 108.6 119.7C107.2 119.2 103.5 118.9 101.5 119.2Z"),
            TracedLayer(.pink, .face, "M45.2 138.9C42.2 139.6 39.6 141.7 38.8 143.8C38 146.1 38.6 148.8 40.2 150.5C46.1 156.8 60.5 153.7 60.5 146.2C60.5 144.3 59.2 142 57.4 140.8C54.6 138.9 48.8 138 45.2 138.9Z", blur: 0.6),
            TracedLayer(.pink, .face, "M147.6 123.2C145.7 123.6 141.4 126.1 140.2 127.5C138.5 129.4 137.9 130.8 137.9 133.3L137.9 135.6L139.1 136.7C140.6 138 141.5 138.2 144.4 138.2C150.7 138.2 155.8 134.1 155.8 129C155.8 126.7 154.2 124.5 152.1 123.6C151.2 123.2 148.4 122.9 147.6 123.2Z", blur: 0.6),
            TracedLayer(.dark, .face, "M59.7 67C53.4 68.1 45.9 74.8 47.9 77.4C49.2 79.1 50.2 78.8 53.1 76.1C56.5 72.8 58.2 72.1 64.5 71.4C66.8 71.1 67.8 69.1 66.4 67.6C65.8 66.9 65.7 66.9 63.3 66.8C62 66.8 60.3 66.9 59.7 67Z"),
            TracedLayer(.dark, .face, "M123.1 58C119.2 58.7 116.8 61.2 118.2 63.1C119 64 119.8 64.1 121.6 63.4C122.9 63 123.6 62.9 126.5 62.9C129.8 62.9 129.9 62.9 132.1 63.8C134.3 64.8 134.4 64.8 135.2 64.4C136.8 63.6 136.6 61.6 134.7 60.2C132 58.2 127.3 57.3 123.1 58Z"),
            TracedLayer(.dark, .face, "M59.4 87.6C55.7 88.6 50.8 91.4 50 93C49.5 93.9 50.2 94 51.2 93C55.4 89.5 61.9 87.5 67 88.2C68.4 88.4 68.9 88.4 69 88.2C69.8 87 63 86.6 59.4 87.6Z"),
            TracedLayer(.dark, .face, "M129.2 78C127.4 78.3 126.6 78.8 126.6 79.4C126.6 79.9 126.6 79.9 127.6 79.6C129.6 78.8 134.5 78.9 137.2 79.6C137.6 79.8 137.7 79.6 137.8 79.3C138 78.4 136.4 77.9 133.1 77.8C131.6 77.8 129.9 77.9 129.2 78Z"),
            TracedLayer(.white, .face, "M75.7 98.6C74.9 99.2 74.2 100.5 74.2 101.3C74.2 102.8 76.2 104.8 77.8 104.8C79.4 104.7 81.1 103 81.1 101.3C81.1 98.9 77.5 97 75.7 98.6Z"),
            TracedLayer(.white, .face, "M142.1 85.9C141.3 86.2 140.5 87.3 140.5 88.2C140.5 90.2 143.1 92.3 144.5 91.4C146.3 90.3 146.7 88.1 145.2 86.6C144.2 85.6 143.2 85.4 142.1 85.9Z"),
        ])

    static let thinking = TracedFigure(
        origin: CGPoint(x: 840, y: 408), size: CGSize(width: 177, height: 180),
        bodyCenter: CGPoint(x: 80.5, y: 110.8), bodyRadius: 63.9,
        faceBox: CGRect(x: 40.5, y: 62.2, width: 115.5, height: 93.8),
        layers: [
            TracedLayer(.red, .body, "M112.6 36.2C109.7 36.4 105.2 37.1 103.1 37.7C100.4 38.4 99.8 38.6 96.3 40.3C94.2 41.3 93.7 41.5 93.3 41.2C92.5 40.7 91.7 41.5 90.9 43.5C90 45.8 89.6 46.2 88 46.4C86.6 46.6 83.1 46.3 82.9 45.9C82.8 45.8 82.4 45.8 82 45.9C81.5 46 80.8 45.9 80.3 45.7C79.3 45.3 77.2 44.6 74.2 43.8C73.2 43.4 71.7 43 70.9 42.7C68 41.9 63.7 41.4 58.6 41.4C54.5 41.4 53.9 41.4 53.9 41.8C53.9 42.1 53.4 42.2 51.7 42.6C42.4 44.4 34.6 48.1 28.1 53.6C20.8 59.9 14.6 68.2 11.9 75.4C11.7 75.9 11.3 77 11 77.8C9.9 80.6 8.6 85.4 7.7 90C6.9 94.3 6.8 107 7.6 111.1C8.5 116.1 9 118.2 10.5 123.2C12 128.4 14.3 133.2 18.9 140.9C20.9 144.3 26.7 151.4 29.8 154.4C33.4 157.8 39.4 162.3 42.6 164.1C43.1 164.3 43.8 164.8 44.4 165.1C45.4 165.7 49.1 167.6 51.1 168.5C52.5 169.1 54.5 169.8 56.8 170.5C57.8 170.8 59.1 171.2 59.6 171.4C60.2 171.6 61.7 172 63 172.3C71.9 174.7 74.3 175.1 83.1 175.1L90.4 175.1L92.8 174.3C94.6 173.7 96 173.4 98.9 173.1C105.8 172.4 110.7 171.6 114.5 170.5C115.4 170.2 116.2 170 116.4 170C116.8 170 121.9 168.3 124.2 167.4C132.5 164.3 140.9 159.2 147.6 153.1C149.1 151.7 150.5 150.5 150.8 150.3C152.7 148.9 159.9 139.5 162.1 135.6C162.3 135.2 162.8 134.5 163.1 134C163.7 133 165 130.3 165 130.1C165 130 165.2 129.5 165.5 128.9C166.4 126.9 168.2 121.4 168.8 119C168.9 118.4 169.2 117.3 169.4 116.6C169.6 115.9 169.8 114.8 169.9 114.1C170 113.4 170.2 111.8 170.5 110.4C171.1 106.8 171 96.9 170.4 92.1C169.9 88.4 168.8 82.2 168.2 80.1C167.4 77.7 166.1 74 165.5 72.6C165.4 72.3 165 71.3 164.5 70.4C163.7 68.4 163.1 67.2 161.2 64C160.6 62.8 158.7 60.1 157.4 58.5C149.1 47.8 139.1 40.9 127.1 37.6C123.2 36.5 116.4 35.8 112.6 36.2Z"),
            TracedLayer(.leaf, .other, "M49 13.8C44.1 14.1 35.8 15.9 34.9 16.8C34.4 17.2 34.4 17.3 34.9 18.7C35.5 20.7 38.5 26.8 39.9 28.9C43.1 33.6 48.4 38.5 52.3 40.3C53.6 40.9 54 41.2 53.9 41.5C53.8 41.9 54.2 41.9 58.7 42.1C65.2 42.2 68.5 42.8 73.6 44.4C74.2 44.5 75.7 45 76.9 45.4C78.1 45.8 79.5 46.2 80 46.4C80.5 46.6 81.2 46.8 81.7 46.7C82.1 46.7 82.5 46.7 82.7 46.8C83.1 47.1 83.1 45.7 82.8 45.3C82.6 45.2 82.5 44.6 82.5 44C82.4 43.1 82.2 42.8 81.9 42.7C81.6 42.5 81.1 42.1 80.9 41.7C80.5 41 80.5 41 80.9 41C82.2 40.9 82.8 40.2 83.2 38.4C83.3 37.4 83.7 35.9 83.9 35.1C84.5 33 84.6 31.8 84.3 31.7C84.1 31.5 84 31.6 84 31.7C84 31.8 83.7 31.9 83.4 31.9C83 31.9 82.8 31.7 82.8 31.5C82.8 31.3 82.5 30.3 82.2 29.3C80.7 25 77.3 20.8 73.4 18.2C67.5 14.5 59.6 13 49 13.8ZM71.3 30C75 32 75.3 32.2 77.2 33.5C78.2 34.3 79.2 35 79.4 35.2C79.8 35.4 79.9 35.8 79.9 37.9L79.9 40.4L79.2 39.3C78.8 38.7 78.2 37.7 77.7 37.2C75.4 34.9 70.8 30.5 69.7 29.7C68 28.4 68.5 28.5 71.3 30Z"),
            TracedLayer(.stem, .other, "M99.2 9.8C96 11.3 93.7 13.6 90.1 18.8C87.5 22.5 84.1 30.5 82.8 36.2C82.5 37.4 82.2 38.7 82.2 39.1C82.1 39.5 82.1 39.2 82 38.2C82 36.7 81.9 36.7 81.7 37.6C81.4 39.3 80.9 44 81.1 44.2C81.2 44.2 81.4 44 81.5 43.7C81.7 43.2 81.7 43.3 81.8 44.2C81.8 44.9 82 45.7 82.2 46.1C82.6 46.8 82.8 46.9 84.7 47.1C89.1 47.6 90.4 47 91.6 43.8C92.2 42.4 92.4 42 92.9 41.8C93.6 41.7 93.7 41.4 93.1 41.1C92.8 40.9 92.9 40.7 93.4 39.6C93.7 38.9 94.4 37.3 95 36.1C95.6 34.9 96.1 33.7 96.2 33.5C96.4 33.3 96.7 32.8 96.8 32.5C97 32.2 97.7 31 98.3 30C98.9 29 99.7 27.6 100.2 26.9C100.6 26.2 102 24.1 103.4 22.2C106.8 17.7 107 17.2 107 14.8C107 10.1 103.3 7.7 99.2 9.8Z"),
            TracedLayer(.leafVein, .other, "M61.5 25.2C61.5 25.3 61.9 25.7 62.4 26C64.5 27.3 65.2 27.7 65.7 28C66.9 28.5 69.9 30.7 71.2 32C76.6 37.1 78 38.6 78.6 39.9C79 40.6 79.4 41.2 79.5 41.2C79.9 41.2 80.8 42.9 80.8 43.7C80.8 45.4 81.8 43.6 82.1 41.5C82.1 40.9 82.1 39.5 82 38.5L81.9 36.6L81.5 38.4C81 41.3 80.4 40.7 80.7 37.5C80.9 35.2 80.8 35.2 77.8 33C76.9 32.4 76 31.8 75.9 31.6C75.7 31.4 75.4 31.2 75 31.2C74.8 31 74.4 30.8 74.2 30.7C74 30.5 72.2 29.5 70.1 28.5C68.1 27.5 66.2 26.5 66 26.4C65.1 25.7 61.5 24.8 61.5 25.2Z", gradient: (77.9, 33.3, 73.7, 35.7, "#3E903C", "#2C7E33")),
            TracedLayer(.white, .face, "M63.1 90C59.7 90.5 56.7 91.6 54.1 93.2C53.7 93.5 53.1 93.9 52.8 94C52.4 94.2 52.2 94.3 52.4 94.4C52.6 94.5 52 95.3 51 96.2C48.6 98.7 47.2 100.4 46 102.4C45.5 103.5 45 104.4 45 104.5C45 104.5 44.9 104.9 44.7 105.3C44.5 105.7 44 107.2 43.6 108.7C42.6 112.5 42.6 119 43.5 122C44.2 124.2 45.2 126.7 45.7 127.3C45.9 127.5 46 127.8 46 127.9C46 128.4 49.6 132.8 50.8 133.8C52.2 135 55.3 137 55.6 137C55.8 137 56.2 137.2 56.6 137.4C59.8 139 67.4 139.4 71.2 138.2C75.4 136.8 78.8 134.7 81.8 131.6C85.6 127.6 88.5 121.9 87.5 120.6C87 120 86.3 120.2 85.4 121.5C82 126.1 74 126.8 68.6 123C66.9 121.8 63.8 117.4 63.8 116.2C63.8 116.1 63.5 115.5 63.2 114.9C62.4 112.9 62.1 109.4 62.6 106.1C62.8 104.6 63.2 102.9 63.4 102.4C65 98.8 65.2 98.3 66.8 96.7C68.8 94.7 70.6 93.8 73.2 93.6C75.2 93.4 75.7 93.1 75.3 92.1C75 91.5 74.8 91.4 71.2 90.5C70.5 90.3 69.9 90 69.8 89.9C69.7 89.4 66.4 89.5 63.1 90Z"),
            TracedLayer(.white, .face, "M125.1 79.5C124.7 79.6 123.7 79.9 123 80.1C121.3 80.5 120.4 80.9 120.6 81.2C120.7 81.3 120.2 81.8 119.4 82.2C117.4 83.5 115.8 85 114.5 86.6C113.3 88.1 111 92.2 111 92.8C111 93 110.8 93.4 110.7 93.8C110.2 94.5 109.6 96.9 109.2 98.9C108.8 101 109.1 107.8 109.7 110C110.6 113.1 112 116.2 113.7 118.8C114.7 120.2 118.1 123.3 119.4 124C122.5 125.7 124.3 126.1 128.4 126.1C132.4 126.1 134 125.8 136.7 124.3C141.3 121.9 146.8 115.1 147.1 111.6C147.2 111.1 147.3 110.6 147.3 110.5C147.6 110.2 146.8 109.7 146.3 109.9C146 110 145.6 110.3 145.3 110.6C143.5 113 137.5 113.4 133.8 111.5C132 110.6 129.3 107.6 128.3 105.6C127.8 104.6 127.4 103.7 127.2 103.4C126.8 102.6 126 98 126 96.2C126 94.1 126.8 90 127.4 88.8C127.6 88.4 127.8 88 127.8 87.9C127.8 87.8 128.2 87.1 128.6 86.4C129.8 84.6 131.8 82.8 132.9 82.6C133.9 82.4 135.2 81.4 135.2 80.8C135.2 79.6 134.5 79.4 130.1 79.3C127.8 79.3 125.6 79.3 125.1 79.5Z"),
            TracedLayer(.dark, .face, "M74.2 91.5C74.2 91.7 74.4 92 74.5 92.2C74.7 92.6 74.6 92.7 72.9 92.8C70.3 93 68.5 93.9 66.2 96.2C64.4 98.1 64.2 98.4 62.7 102.1C62.1 103.3 61.5 107.2 61.5 109.2C61.5 111.3 62.1 114.4 62.6 115.4C62.8 115.8 63 116.3 63 116.5C63 117.3 64.9 120.3 66.5 122.1C69.4 125.2 72.9 126.5 77.7 126.2C81 126 84.2 124.3 85.9 122C86.7 120.9 87 120.8 87.2 121.5C87.4 122.2 87.8 121.9 87.8 121.1C87.8 120.8 88 119.7 88.2 118.7C89.4 114.8 89.4 108.5 88.4 106.5C88.2 106.1 88 105.6 88 105.5C88 105.3 87.5 104.1 86.9 102.9C85.6 100.3 82.5 96.4 80.6 94.9C79.1 93.6 74.2 91.1 74.2 91.5Z"),
            TracedLayer(.dark, .face, "M125.2 79C124.1 79.2 121.7 80.2 121 80.8C120.2 81.4 120.8 81.8 121.7 81.4C123.6 80.4 125.5 80.1 129.8 80.1C134.4 80.1 135.2 80.3 134.1 81.2C133.7 81.5 133.1 81.8 132.6 81.9C131 82.2 127.5 86 126.9 88C126.8 88.3 126.6 88.8 126.5 88.9C126.1 89.4 125.2 94.2 125.2 96.2C125.2 98.2 126 102.8 126.5 103.7C126.6 103.9 127.1 104.8 127.5 105.8C129.4 109.6 132.6 112.4 136.1 113.1C140 114 144 113.2 145.8 111.2C146.3 110.6 146.6 110.5 146.8 110.7C147.1 111 147.3 110.8 147.6 109.8C147.8 109.1 148.2 108.2 148.4 107.8C148.9 106.7 149.5 102.4 149.5 100.3C149.5 94 146.5 87.4 141.7 83.2C139.8 81.6 137.2 80 136.3 80C136.2 80 135.5 79.8 134.9 79.5C133.9 79 133.1 78.9 130 78.8C128 78.8 125.9 78.9 125.2 79Z"),
            TracedLayer(.pink, .face, "M49.4 141C46.1 141.5 42.6 143.5 41.3 145.7C40.3 147.4 40.3 150.1 41.3 151.8C43 154.7 45.4 155.8 50.4 155.9C55.1 156.1 58.5 155.1 61.1 152.8C62.7 151.5 63.7 149 63.4 147.4C62.6 143.2 55.7 140.1 49.4 141Z", blur: 0.6),
            TracedLayer(.pink, .face, "M147 121.2C143.5 121.8 139 124.6 136.8 127.4C136 128.6 135.2 130.9 135.2 132.6C135.2 136.6 139.2 138.5 145.5 137.4C151.7 136.3 155.9 132.2 155.9 127.1C155.9 122.6 152.3 120.2 147 121.2Z", blur: 0.6),
            TracedLayer(.dark, .face, "M65.6 70.2C62.5 73.5 61.5 74.4 59.6 75.7C57.7 77.1 55 78.4 52.1 79.4C50.9 79.8 49.2 81.2 49.2 81.9C49.2 83.1 51 84.8 52.1 84.8C52.4 84.8 53.5 84.4 54.6 84C55.7 83.5 57 83.1 57.4 82.9C60.6 81.7 65.9 78.1 68.2 75.6C70.4 73.2 71 71.5 69.9 70C69.4 69.2 69.2 69.1 68 69C66.8 69 66.7 69 65.6 70.2Z"),
            TracedLayer(.dark, .face, "M101.9 125.2C99.7 125.8 96.8 127.7 95.8 129.2C93.7 132.3 93.5 133.8 95 135.3C95.9 136.2 96.1 136.2 97.2 136.2C98.7 136.2 99.2 135.8 99.9 133.8C100.4 132.3 101.6 131.2 103.2 130.8C104.7 130.3 106 130.7 107.1 132.1C109.2 134.6 109.6 134.8 111.1 134.2C111.9 133.9 112.8 132.6 112.8 131.7C112.8 129.8 110.8 127.4 108.3 126C106.9 125.3 106.4 125.2 104.7 125.1C103.6 125 102.3 125.1 101.9 125.2Z"),
            TracedLayer(.dark, .face, "M116 62.9C114.4 63.9 114.3 65.4 115.7 66.6C116.6 67.6 116.5 67.6 120.9 67.5C124.6 67.4 129.1 67.8 131.3 68.4C132.9 68.8 133.1 68.8 133.9 68.4C134.9 67.9 135.8 66.6 135.6 65.9C135.1 64.3 133.4 63.4 130.1 63C128.9 62.8 127.4 62.6 126.7 62.5C126 62.3 123.5 62.2 121.2 62.2C117 62.2 116.8 62.3 116 62.9Z"),
            TracedLayer(.redShade, .other, "M93 144.5C93 144.7 93.2 144.9 93.6 145C93.9 145.1 94.9 146.1 95.9 147.1C97.3 148.6 97.8 149.2 98.2 150.5C98.9 152.4 99 155.8 98.4 157.5C98.2 158.1 97.9 159.2 97.8 160C97.2 162.3 94.8 167.2 93.2 168.9C91 171.4 91.8 172.8 94.8 171.6C95.3 171.4 95.8 171.1 95.8 170.8C95.8 170.7 95.9 170.2 96.1 169.7C96.5 168.8 96.6 168.5 97.8 165.1C98.2 164 98.6 162.9 98.7 162.6C100.1 159.7 100.7 155 100 152.2C99.5 150.1 98.2 147.5 97.1 146.5C95.9 145.4 94.4 144.4 94.2 144.7C94.1 144.8 94 144.7 94 144.6C94 144.4 93.8 144.2 93.5 144.2C93.2 144.2 93 144.4 93 144.5Z"),
            TracedLayer(.redShade, .other, "M84.6 143.5C83 143.9 81 145.6 80 147.3C79.5 148.2 79 149.3 78.9 149.8C78.8 150.2 78.5 150.8 78.3 151.1C78.1 151.3 77.8 151.8 77.7 152.1C77.5 152.4 77.1 152.8 76.7 152.9C75.5 153.5 73.3 155.9 72.5 157.6C72.1 158.5 71.6 159.3 71.5 159.4C71.4 159.4 71.2 159.7 71.2 159.9C71.2 160.1 71 160.6 70.8 160.9C70.5 161.3 70.1 162.2 69.9 162.9C69.6 163.7 69.3 164.6 69.1 164.9C68.7 165.8 68.6 167.3 69.1 167.2C69.2 167.1 69.5 166.8 69.7 166.5C70.7 164.4 71.5 162.6 71.9 161.5C72.3 160.1 72.8 159.1 73.4 158.3C73.9 157.8 74.5 157.1 75.5 155.6C75.9 155.2 76.7 154.2 77.3 153.5C78 152.7 78.9 151.3 79.4 150.4C80.6 148.2 83.2 145.5 85 144.9C85.6 144.7 86.9 144.4 87.8 144.4C88.7 144.3 89.7 144.2 90.1 144.1C90.5 144 90.8 144.1 90.8 144.2C90.8 144.3 91 144.4 91.4 144.4C92.2 144.5 92.2 144.1 91.5 143.7C90.8 143.3 85.8 143.2 84.6 143.5Z"),
            TracedLayer(.dark, .face, "M64.4 89.1C64.1 89.2 63 89.4 61.9 89.6C58.6 90.3 56.2 91.3 53.6 93.3C52.5 94.1 52.3 94.3 52.6 94.6C52.8 94.8 53 94.9 53.2 94.7C53.5 94.6 54 94.3 54.4 94C55.6 93.2 58 92.1 59.6 91.5C61.7 90.8 66.8 90.1 68.4 90.4C69.5 90.5 69.7 90.5 69.7 90C69.7 89.8 69.5 89.5 69.3 89.4C68.8 89.2 65 89 64.4 89.1Z"),
            TracedLayer(.white, .face, "M77.1 96.9C76.2 97.1 75 98.9 75 100C75 102.4 78.1 104.2 80.3 103.2C82.1 102.4 82.6 99.4 81.3 98C80.2 96.8 79.1 96.5 77.1 96.9Z"),
            TracedLayer(.white, .face, "M140.1 85C139.5 85.2 138.5 86.6 138.5 87.3C138.5 89 140.1 90.8 141.7 90.8C142.6 90.8 144 89.3 144 88.5C144 86.5 141.6 84.4 140.1 85Z"),
        ])

    static let sad = TracedFigure(
        origin: CGPoint(x: 1051, y: 410), size: CGSize(width: 178, height: 178),
        bodyCenter: CGPoint(x: 98.5, y: 107.5), bodyRadius: 64.1,
        faceBox: CGRect(x: 29.2, y: 62.8, width: 122.8, height: 87.4),
        layers: [
            TracedLayer(.red, .body, "M108.8 33.9C105.1 34.3 99.3 35.7 96.8 36.7C94.5 37.6 93.6 38 92.7 38.5C91.8 39 91.6 39 91.1 38.7C90.6 38.4 90.4 38.5 89.8 39.1C89.3 39.5 88.8 40.5 88.5 41.3C87.9 42.9 87.2 43.7 86.4 43.9C85.3 44.2 80.6 43.9 80.2 43.5C80.1 43.4 79.6 43.2 79.2 43.2C78.9 43.2 78.4 43.1 78.1 42.9C77.6 42.5 73.4 41.1 68.9 39.8C63.3 38.1 53.3 37.5 53.4 38.8C53.5 39.2 53 39.4 50.4 40C47 40.8 42.2 42.5 39.4 44C38.5 44.6 37.6 45 37.6 45C37.5 45 37.2 45.2 36.8 45.4C36.4 45.7 35.6 46.2 35 46.7C31.5 48.9 26.2 53.3 23.9 55.9C20.7 59.5 16 65.5 16 66.1C16 66.1 15.6 66.9 15.1 67.8C14.2 69.2 12.6 72.4 11.7 74.5C10.4 77.5 8 84.7 8 85.8C8 86 7.8 86.8 7.7 87.5C5.9 94.4 5.8 108.7 7.6 116.4C8.7 120.9 9.9 125 10.7 126.7C10.9 127.1 11 127.6 11 127.7C11 127.9 13.2 133 13.5 133.4C13.6 133.5 14.3 134.8 15 136.1C15.7 137.5 16.5 138.9 16.8 139.2C17 139.6 17.7 140.7 18.4 141.6C21 145.7 26.4 151.8 30.5 155.2C36.2 160.2 44 164.7 51.5 167.5C53.4 168.2 59.4 170 59.7 170C59.9 170 61 170.2 62.2 170.5C76.4 173.6 98.4 173.4 113 170.2C113.9 169.9 115.8 169.5 117.1 169.1C118.5 168.8 120.2 168.3 120.9 168.1C121.6 167.9 122.5 167.6 123 167.4C123.5 167.2 124.7 166.7 125.6 166.4C129.2 165 136 161.4 139.1 159.2C139.7 158.8 140.5 158.2 141 157.9C147.6 153.5 157.4 143.3 161.1 136.7C161.3 136.4 161.9 135.3 162.6 134.2C163.3 133.1 164.1 131.6 164.5 130.9C164.8 130.2 165.2 129.2 165.5 128.7C165.8 128.2 166 127.6 166 127.4C166 127.3 166.2 126.7 166.5 126.1C166.8 125.6 167 125 167 124.8C167 124.6 167.2 124.1 167.4 123.7C167.6 123.2 167.9 122.2 168.2 121.5C168.4 120.8 168.8 119.3 169.1 118.4C170.9 111.9 171.5 107.7 171.7 100C171.9 89.2 170.5 80.8 166.2 69C165.6 67.1 163.4 62.5 162 60.1C161.6 59.4 161.2 58.7 161.1 58.5C161 58.3 160.6 57.7 160.2 57.1C159.8 56.6 159.3 55.8 159.1 55.5C156.1 51.1 149.4 44.5 144.9 41.6C143.3 40.6 140.2 39 136.9 37.5C129.8 34.2 118.6 32.8 108.8 33.9Z"),
            TracedLayer(.leaf, .other, "M43.4 8.8C37.5 9.5 27.7 11.9 26.7 12.9C26.2 13.4 26.2 13.4 27.6 16.3C30.9 23 36 29.1 41.5 32.8C43.7 34.3 51.2 37.7 52.7 37.9C53.5 38 53.7 38.2 53.5 38.3C53 38.8 53.3 38.9 57 38.9C60.9 38.9 65.4 39.6 68.6 40.5C73.1 41.9 77.4 43.3 77.9 43.6C78.1 43.8 78.7 44 79 44C79.4 44 79.8 44.1 79.9 44.2C80.5 44.8 80.8 43.8 80.7 41.6C80.6 39.7 80.6 39.3 80.1 39.1C79 38.6 77.7 37.2 76.2 34.8C74.1 31.6 71.9 28.9 70.1 27.3C68.5 26 64.4 23.1 63 22.3C62.5 22.1 62.2 21.9 62.4 21.8C62.7 21.7 65.9 23.3 68.2 24.7C68.8 25.1 70.7 26.2 72.2 27.2C73.8 28 75.8 29.3 76.7 30C77.5 30.7 78.3 31.2 78.4 31.2C78.6 31.2 78.9 31.6 79.2 32C79.5 32.4 80 32.8 80.2 32.8C80.9 32.8 82.5 30.9 82.5 30.2C82.5 29.5 82.1 29 81.9 29.5C81.9 29.8 81.8 29.8 81.5 29.6C81.2 29.4 81 29.3 81 29.4C80.9 29.4 80.6 28.5 80.3 27.4C79 22.1 75.4 16.4 71.5 13.5C68.5 11.3 63.5 9.4 58.6 8.7C55.1 8.2 47.6 8.2 43.4 8.8Z"),
            TracedLayer(.stem, .other, "M95.5 9.8C92.6 11.1 88.7 15.3 86.2 19.9C84.6 22.9 83 26.3 83 26.7C83 26.9 82.8 27.5 82.5 28.1C82.2 28.7 82 29.5 81.9 29.9C81.8 30.3 81.4 30.9 81.1 31.2C80.8 31.5 80.5 32.2 80.4 32.7C80.3 33.2 80.1 33.9 80 34.4C79.6 35.8 79 39.7 79.2 40.1C79.3 40.5 79.4 40.5 79.7 40.1C80 39.7 80 39.9 80 42L79.9 44.3L80.6 44.5C81.1 44.7 82.5 44.8 83.9 44.8C87.1 44.8 87.8 44.5 88.7 42.6C90.1 39.6 90.1 39.6 91.2 39.1C91.2 39.1 91.2 38.8 91 38.6C90.8 38.2 90.8 37.9 91.2 37C91.5 36.4 92.1 35.1 92.5 34.1C92.9 33.1 93.6 31.6 94.1 30.8C94.6 29.9 95 29.2 95 29.1C95 29 95.2 28.7 95.5 28.3C95.7 27.9 96.2 27.1 96.7 26.5C97.9 24.5 100.3 21.4 101.5 20.1C103.7 17.9 103.9 17.5 104 15.8C104.2 11.5 99.4 8 95.5 9.8Z"),
            TracedLayer(.leafVein, .other, "M58.2 19.9C58.2 20.2 59 20.8 59.8 21.2C60.2 21.3 60.5 21.6 60.5 21.8C60.5 21.9 60.6 22 60.8 22C61 22 61.5 22.3 62 22.6C62.5 22.9 63.9 23.8 65.1 24.6C70 27.8 72 29.9 75.6 35.3C76.7 36.9 77.8 38.3 78.1 38.6C78.5 38.8 78.9 39.4 79.1 39.8C79.4 40.9 79.7 40.3 80.2 37.2C80.8 34.1 81.4 31.8 81.6 31.2C81.9 30.5 81.3 30.8 80.8 31.5C80.4 32.2 80.1 32.1 79.7 31.4C79.6 31 79.2 30.7 78.9 30.6C78.6 30.5 77.7 29.9 76.9 29.2C76 28.6 74.1 27.3 72.5 26.4C70.9 25.5 69.1 24.4 68.4 24C64 21.3 58.2 19 58.2 19.9Z"),
            TracedLayer(.white, .face, "M53 90.2C51.4 90.5 50.2 90.9 50.2 91.2C50.2 91.3 50 91.5 49.6 91.6C48.5 91.8 45.4 93.8 43.5 95.5C39.7 98.9 37.1 103 35.5 108.2C34.6 111 34.6 119.5 35.5 121.8C35.8 122.7 36 123.5 36 123.7C36 124.1 36.6 125.2 38 127.7C39.2 130.1 43.2 133.7 46.2 135.2C49.4 136.8 50.8 137.1 55.4 137.1C60.1 137.1 61.9 136.7 65.2 134.9C70.7 132.1 75.1 127.5 73.5 126.4C73.2 126.2 72.6 126.4 71.1 127.1C69.2 128 69 128.1 66.9 128.1C59.4 128.1 54.2 122.5 53.8 114C53.7 111.2 53.8 110.7 54.6 107.8C55.8 103.6 59 99.4 62.2 97.8C64.1 96.8 64.9 96.7 67.7 96.7C69.4 96.7 70 96.6 70.2 96.4C70.9 95.6 70.4 95 68.1 93.9C67.7 93.6 66.8 93.1 66.1 92.8C65.5 92.4 64.2 91.8 63.5 91.5C62.7 91.2 62.1 90.8 62.1 90.8C62.2 90.6 62 90.5 61.7 90.4C60.7 90.1 54.5 90 53 90.2Z"),
            TracedLayer(.white, .face, "M120.6 86.8C116.7 87.6 111.2 91.6 108 95.9C99.3 107.5 103.2 126 115.6 131.8C117.9 132.8 121.8 133.8 124 133.8C129.8 133.8 135.8 130.8 139.7 126C141.2 124 143 120.8 143.1 119.9C143.1 119.6 143.2 119.2 143.3 119C143.6 118.7 143.1 118 142.6 118C142.4 118 141.7 118.4 141.1 119C135.7 123.7 126.5 121.5 122.6 114.5C121 111.7 120.7 110 120.7 105.4C120.7 101.4 120.7 101 121.3 99.2C123.3 93.6 126.7 90.6 131.6 90C133.3 89.8 134 89.4 134 88.8C134 88.4 133.1 87.4 132.8 87.6C132.6 87.7 131.9 87.5 131.2 87.2C130.1 86.8 129.2 86.7 125.8 86.6C123.5 86.6 121.2 86.6 120.6 86.8Z"),
            TracedLayer(.dark, .face, "M132.6 87.7C132.4 87.8 132.5 87.9 132.8 88.3C133.5 88.9 133.4 89 131.3 89.2C126.4 89.8 122.6 93.2 120.6 98.9C119.9 100.8 119.9 101.1 119.9 105.4C119.9 109.6 120 110 120.6 111.8C121.5 114.5 122.4 115.9 124.4 117.9C127.5 120.9 129.5 122 133.1 122.2C136.7 122.4 139.1 121.7 141.3 119.8C142.6 118.6 142.8 118.5 142.8 119.3C142.8 120.3 143.3 119.1 144.1 116.5C146.6 108.1 145.9 102.6 141.7 95.4C140.1 92.7 137.6 90.5 133.1 87.7C133 87.6 132.8 87.6 132.6 87.7Z"),
            TracedLayer(.dark, .face, "M69.8 95.3L69.8 96.1L68.4 95.9C64.5 95.5 61.5 96.7 58.4 99.8C55.8 102.5 54.5 105 53.2 109.9C53.1 110.5 53 112.2 53.1 114C53.3 118.9 54.5 122 57.4 124.9C60.2 127.7 62.9 128.8 66.9 128.8C69.2 128.8 69.5 128.8 71.2 127.9C73.4 126.8 73.2 126.9 73.3 127.6C73.4 128.1 73.4 128.1 73.9 127.2C74.1 126.8 74.7 125.9 75.1 125.4C78 121.7 79.6 115.3 78.8 109.9C78.2 105.2 75.6 100 72.9 97.8C72.5 97.4 71.6 96.6 71 95.9C69.8 94.6 69.8 94.6 69.8 95.3Z"),
            TracedLayer(.pink, .face, "M141 129.4C137.2 130.4 132.5 133.7 131.4 136.1C129.3 140.4 132.4 144.5 137.9 144.9C144.5 145.4 151.3 140.8 151.9 135.2C152.2 133.2 150.8 131.2 148 129.8C146.5 129 143 128.8 141 129.4Z", blur: 0.6),
            TracedLayer(.pink, .face, "M34.3 136.6C30 137.7 28.1 141.4 30 145.2C31 147.1 31.8 147.7 35.4 149.2C38.4 150.6 44.4 150.6 46.9 149.3C50.1 147.7 51.3 144.9 50.1 142.1C48.5 138.1 40.1 135.2 34.3 136.6Z", blur: 0.6),
            TracedLayer(.dark, .face, "M85 125C82.7 125.4 79.1 127.7 77.8 129.6C76.1 132.2 75.9 133 76.8 134.4C78.2 136.8 80.3 136.6 81.5 133.9C82.3 132.1 82.9 131.5 84.8 130.7C86.4 129.9 88.6 129.8 89.8 130.4C90.2 130.6 91.2 131.4 92 132.2C93.8 133.8 94.9 133.9 96.2 132.8C98.4 131.1 96.2 127.3 92 125.6C90.2 124.9 87 124.6 85 125Z"),
            TracedLayer(.dark, .face, "M55.9 68C55.6 68.1 54.4 69.2 53.2 70.4C50.3 73.4 47.5 75.1 43.8 76.4C42.2 76.9 40.9 78 40.6 78.9C40.3 80.3 41.6 81.8 43.1 81.8C45 81.8 50 79.4 53.7 76.8C59.6 72.7 61.1 70.1 58.6 68C58.1 67.7 56.6 67.7 55.9 68Z"),
            TracedLayer(.dark, .face, "M114.4 63C112.8 63.9 112.6 65.5 113.8 66.8C116.1 69.4 126.3 74 130.1 74.1C131.5 74.1 131.6 74 132.3 73.3C132.7 72.8 133 72.2 133 71.8C133 70.9 131.5 69.6 130.2 69.2C123.6 67.4 122.1 66.8 118.1 64C116.2 62.7 115.4 62.5 114.4 63Z", gradient: (122.4, 64.2, 122.6, 72.8, "#141314", "#090708")),
            TracedLayer(.dark, .face, "M53.6 90C51.6 90.2 50.2 90.8 50.4 91.4C50.6 91.8 50.5 91.8 51.7 91.3C52.7 90.9 58.5 90.7 60.9 91.1C62 91.2 62.2 91.2 62.2 90.9C62.2 90.1 57.3 89.6 53.6 90Z"),
            TracedLayer(.white, .face, "M69.2 100.8C68.1 101.6 67.7 102.7 67.7 104.5C67.8 104.8 68.2 105.5 68.7 106C69.6 106.9 69.8 107 71 107C72.2 107 72.5 106.8 73.2 106.2C74 105.5 74.1 105.4 74.1 104C74.1 102.9 74 102.5 73.5 101.8C72.2 100.2 70.5 99.8 69.2 100.8Z"),
            TracedLayer(.white, .face, "M135.9 93.7C133.7 95 133.8 97.7 136 99.4C137.2 100.2 138.2 100.2 139.2 99.2C140.5 97.8 140.7 97 140 95.6C139.1 93.7 137.2 92.9 135.9 93.7Z"),
        ])

    static let wink = TracedFigure(
        origin: CGPoint(x: 1265, y: 408), size: CGSize(width: 188, height: 180),
        bodyCenter: CGPoint(x: 78.2, y: 110.5), bodyRadius: 64.6,
        faceBox: CGRect(x: 35.5, y: 64.8, width: 133.3, height: 91.2),
        layers: [
            TracedLayer(.red, .body, "M120 36.2C113.3 36.9 108.9 38.1 104.2 40.3C103 41 101.9 41.4 101.8 41.2C101.7 40.9 100.7 40.9 100.1 41.4C99.8 41.6 99.3 42.5 99 43.4C98.7 44.3 98.2 45.3 97.9 45.6C96.9 46.6 91.5 47.1 90.7 46.2C90.5 46.1 90.2 46 89.9 46C89.3 46 80.5 43.4 79.2 42.8C78.8 42.6 77.8 42.3 77.1 42.1C76.5 41.9 74.8 41.5 73.5 41.1C69.5 40 62.4 39 61.2 39.4C61 39.5 60.8 39.7 60.8 39.9C61 40.2 57.7 41 56.4 41C55.6 41 50.2 42.6 47.5 43.7C39.5 46.8 33.3 51 26.2 58C21.5 62.7 20.2 64.3 17.2 68.8C13.2 74.9 11.1 79.5 8.6 87.9C5.7 97.8 5.4 111.1 7.9 120.9C9 125 9.2 125.8 10 127.9C10.4 129 10.9 130.2 11 130.5C11.4 131.7 13.3 135.7 14.1 137.3C14.6 138.1 15 138.8 15 138.9C15 139 16.8 141.7 18.1 143.6C23.2 151.2 32.4 159.8 40.4 164.3C43.6 166.2 50.2 169.4 52.4 170.1C52.9 170.3 54.2 170.8 55.1 171.1C61.5 173.4 72.8 175.6 80.9 176C96.1 176.8 113.6 175.8 122.2 173.4C123.3 173.2 125 172.8 126 172.5C128.9 171.7 131.5 170.8 136 169.1C136.9 168.8 142.2 166.1 142.6 165.8C142.8 165.6 144.1 164.8 145.4 164.2C146.8 163.4 152.1 159.7 153.9 158.3C160.1 153.2 168.1 144.4 171.1 139.2C174.5 133.4 175.3 131.9 176.4 129.1C176.7 128.2 177.2 127 177.4 126.6C178.6 123.6 180.6 115.9 181 112.5C181.1 111.4 181.4 109.8 181.5 108.9C182 106.3 182 95.8 181.4 92C180.6 86.5 179.3 80.4 178.3 77.8C177.6 75.8 176.7 73.4 176.5 72.9C176.4 72.6 176 71.6 175.5 70.6C174.8 68.9 173.9 67.2 172.4 64.5C168.2 56.9 159.4 47.7 152.5 43.8C146 40 139.5 37.6 133.8 36.6C131.2 36.2 122.2 35.9 120 36.2Z"),
            TracedLayer(.leaf, .other, "M51.5 9C50.5 9.1 48.2 9.5 46.5 9.8C38.7 11.4 38.5 11.5 39 13.3C40.1 17.1 43.1 23.6 45.1 26.4C48.7 31.4 52.8 34.9 57.9 37.5C61.6 39.4 61.5 39.3 61.1 39.4C60.3 39.7 60.9 39.9 63 40.1C66 40.3 70.4 41.1 73.2 41.9C74.5 42.2 76.2 42.7 76.9 42.8C77.6 43 78.5 43.3 79 43.6C80.3 44.2 89.1 46.8 89.7 46.8C90.1 46.8 90.2 46.8 90.1 47C90 47.2 90.1 47.3 90.4 47.2C90.8 47.1 90.9 46.8 90.9 44C91 41 91.1 39.8 92.5 34.1C92.8 32.8 92.7 31.4 92.3 32.2C92.1 32.7 91.2 32.8 91 32.4C90.9 32.2 90.8 31.8 90.8 31.4C90.8 30.2 89.8 26.8 88.7 24.1C85.6 16.3 79.4 11.7 69.1 9.5C66.3 8.9 55.1 8.6 51.5 9Z"),
            TracedLayer(.stem, .other, "M108.2 8.8C105.5 9.5 100.5 14.9 97.2 20.6C94.8 25 93.5 27.9 92.5 31.6C92.1 33.1 91.6 34.8 91.4 35.4C90.7 37.4 90 42.6 90.1 44.9L90.1 47.1L91 47.3C93.3 47.8 97.1 47.2 98.3 46.3C98.7 46 99.2 45.2 99.6 43.9C100.2 42.2 100.4 41.9 101 41.8C101.8 41.7 102 41.1 101.5 40.9C101.2 40.9 101.4 40.4 101.9 39.2C102.3 38.3 103 36.9 103.4 36C103.8 35.1 104.3 34.1 104.5 33.8C104.7 33.4 105 32.8 105.2 32.5C105.4 32.2 105.8 31.4 106.1 30.9C106.5 30.3 107.2 29.2 107.7 28.3C108.2 27.4 108.8 26.5 108.9 26.3C109.5 25.3 110.2 24.2 112 21.8C114.8 17.9 115.1 17.2 115.2 15C115.4 12.6 115 11.5 113.6 10.2C112.1 8.6 110.4 8.2 108.2 8.8ZM90.5 35.5C90.2 36.7 89.5 40.4 89.5 41.2C89.5 42.3 90 41.3 90.2 39.8C90.2 39.2 90.5 37.8 90.7 36.8C91.1 34.8 91 34.2 90.5 35.5Z"),
            TracedLayer(.white, .face, "M63.2 87.7C60.4 88 57.2 88.5 56.6 88.9C56.2 89.1 55.8 89.2 55.6 89.2C55.3 89.2 53.4 90.1 52 90.9C50.1 92 45.2 96.2 45.9 96.2C46.1 96.2 45.6 97.2 44.8 98.3C43.3 100.6 41.5 104.2 40.7 106.6C40 108.8 39.2 114.4 39.4 115.9C39.9 120.3 40.1 121.6 40.7 123.4C42.8 130.3 49 136.6 55.6 138.5C57.4 139 58.2 139.1 61.4 139.1C65.6 139.1 67.4 138.7 71.2 137.1C75.1 135.4 80.6 130.8 80.5 129.3C80.4 128.4 79.7 128 79.1 128.6C78.8 128.8 78 129.2 77.1 129.6C73.3 131 67.5 129.5 64 126.2C59.7 122 58.2 114.2 60.4 107.5C62.4 101.6 65.2 98.4 70.5 96.2C72.3 95.5 76.6 95.5 77.7 96.1C79.2 97 79.8 95.5 78.5 94.2C77.6 93.4 74 91 72.8 90.4C70 89.1 68.7 88.7 66.7 88.3C65.5 88.1 64.6 87.8 64.7 87.7C64.7 87.6 64.6 87.5 64.5 87.5C64.3 87.5 63.7 87.6 63.2 87.7Z"),
            TracedLayer(.dark, .face, "M78.5 95.1C78.5 95.8 78.5 95.8 77.9 95.3C76.9 94.7 72 94.8 70.2 95.5C63.5 98.2 59.7 103.6 58.8 111.6C57.8 120.4 61.9 127.7 69.3 130.2C72.7 131.3 77.5 130.9 79.3 129.3C79.7 128.9 79.8 129 79.8 129.6C79.8 130.4 80.1 130.4 80.7 129.6C80.9 129.2 81.8 128.2 82.5 127.2C84.6 124.4 85.3 123 86.3 120C87.1 117.4 87.2 109.9 86.4 107.1C85.5 103.8 83.4 100 81.4 97.6C80.7 96.9 79.9 95.9 79.5 95.4C78.8 94.3 78.5 94.3 78.5 95.1Z"),
            TracedLayer(.dark, .face, "M117 121.9C116.7 122 115.6 122.5 114.6 123C113.5 123.5 112.5 124 112.4 124C112.3 124 111.8 124.2 111.2 124.4C110.6 124.7 108.8 125.1 107.2 125.4C104.3 125.8 104.2 125.8 99.5 125.3C92.7 124.4 91.4 124.7 89.7 127.3C88.9 128.6 88.9 128.7 88.9 131.3C88.9 134.2 89.3 135.7 90.8 138.5C92 140.8 93.9 143.2 95 143.7C96.1 144.1 96.3 143.8 96.1 142.4C95.8 140.5 97.9 137 100 136.1C102.1 135.2 102.7 134.9 104.3 134.6C107.9 133.8 110.7 134.3 112.3 136L113.3 137L113.2 139C113.2 140.4 113 141.1 112.7 141.4C112.2 141.9 112.1 143.4 112.5 143.6C112.7 143.7 112.8 143.7 112.8 143.5C112.8 143.4 113 143.2 113.3 143.2C114.2 143.2 117.8 139.4 119.2 136.8C123 130 123.2 123 119.8 122C118.9 121.8 117.7 121.7 117 121.9Z"),
            TracedLayer(.pink, .face, "M156.5 115.4C151.9 116.7 148.4 119.2 146.8 122.5C145.2 125.6 145.9 129.9 148.4 131.9C150.3 133.4 151.4 133.8 153.9 133.8C160.8 133.9 166.8 129.6 168.3 123.5C168.8 121.5 168.8 121.4 168.4 120C167.8 118.2 166 116.3 163.9 115.5C162.2 114.9 158.4 114.8 156.5 115.4Z", blur: 0.6),
            TracedLayer(.pink, .face, "M43.9 140C40 140.4 36.9 142.5 35.9 145.3C34.4 149.4 36.9 153.3 42.4 155.4C44.1 156.1 49.4 156.1 51.6 155.4C55.8 154.1 57.9 151.9 58.2 148.6C58.4 146.2 57.5 144.7 54.7 142.6C51.8 140.5 47.9 139.5 43.9 140Z", blur: 0.6),
            TracedLayer(.dark, .face, "M139.6 94.2C133.4 95.8 128.9 98.6 125 103.1C121.8 106.8 120 110 119.9 112C119.9 113.2 120 113.4 120.9 114.2C122 115.2 123 115.2 124.2 114.2C124.9 113.7 126.4 111.6 127.1 110.3C128.4 107.8 133.7 103 136.8 101.6C139.6 100.4 140.2 100.2 142.1 100C144.8 99.7 147.2 99.9 149.4 100.6C151.7 101.4 152.6 101.9 154.9 103.8C157.1 105.5 157.8 105.7 159.4 105C162.4 103.7 161 100.6 155.8 97.2C151.8 94.6 150.2 94.2 144.6 94.1C142.2 94.1 139.9 94.1 139.6 94.2Z"),
            TracedLayer(.pink, .face, "M103.9 133.8C102.6 134.2 101.6 134.5 99.8 135.3C99.4 135.5 98.5 136.3 97.6 137.1C95.9 138.9 95.2 140.4 95.3 142.4C95.4 143.8 95.4 143.8 96.9 144.8C97.7 145.4 99 146 99.7 146.3C102.8 147.4 108.6 146.4 111 144.3C111.2 144.2 111.7 143.9 112.1 143.9C112.6 143.8 112.8 143.5 112.9 143C113.1 142.3 113.1 142.1 113.6 141.2C113.9 140.8 114 139.9 114 138.8C114 136.4 113.4 135.3 111.3 134.3C109.7 133.5 106.3 133.3 103.9 133.8Z", gradient: (108.6, 134.5, 101.2, 145.8, "#FA5962", "#FB4857")),
            TracedLayer(.dark, .face, "M133.4 65C129 65.7 126.8 67.9 128.8 69.8C129.8 70.8 130.6 70.9 132.4 70.4C133.4 70.1 134.9 70 136.5 70C139.6 70 140.9 70.4 144.5 72.4C146.8 73.7 147.1 73.8 147.8 73.5C148.8 73.1 149.8 71.9 149.8 71.1C149.8 70.3 147.4 67.9 145.7 66.9C142.6 65.2 137.2 64.4 133.4 65Z"),
            TracedLayer(.dark, .face, "M61.8 66.6C61.4 66.7 60.3 66.9 59.4 67C55.2 67.6 51.5 69.7 48.6 72.8C46.1 75.6 46.3 78 49.1 78C50 78 50.2 77.8 52.2 75.9C55.6 72.7 57.8 71.8 63.9 71.4C66.5 71.2 66.9 71 67.3 69.8C68 67.4 65.7 66.1 61.8 66.6Z"),
            TracedLayer(.leafVein, .other, "M70 22.3C70 22.5 70.3 22.9 70.6 23C71.4 23.4 74.5 25.6 76.9 27.4C79.5 29.4 84.6 34.9 87 38.5C88.7 41 88.9 41 88.8 38.6C88.8 38.2 88.9 37.5 89.1 37.1C89.3 36.7 89.5 35.9 89.5 35.2C89.5 33.7 87.9 32 83.8 29.2C83.1 28.7 82.2 28.1 81.9 28C81.6 27.8 81 27.5 80.5 27.2C77.1 25.2 73.2 23 72.4 22.8C71.9 22.6 71.5 22.3 71.4 22.2C71.1 21.8 70 21.9 70 22.3Z", gradient: (87.7, 31.9, 78.6, 33.3, "#398838", "#2A782F")),
            TracedLayer(.dark, .face, "M59.1 87.8C53.8 88.9 49.1 91.6 46.6 95C45.6 96.4 46 96.9 47.2 95.7C48.1 94.7 51.2 92.2 52.3 91.6C53.6 90.9 55.5 90 55.8 90C56 90 56.5 89.8 56.9 89.6C57.7 89.2 61.9 88.5 63.6 88.5C64.5 88.5 64.7 88.4 64.7 88C64.6 87.2 62.4 87 59.1 87.8Z"),
            TracedLayer(.leafVein, .other, "M90.5 35.7C90.4 36.2 90.1 36.8 90 37.1C89.8 37.7 89.2 41 89.2 41.7C89.3 42.6 90 41.2 90.1 40C90.2 39.4 90.5 38 90.7 36.9C91.1 34.8 91 34.2 90.5 35.7Z"),
            TracedLayer(.white, .face, "M76 99.8C73.4 100.5 72.7 103.8 74.8 105.8C76.5 107.4 78.1 107.4 79.9 105.6C80.9 104.7 81 104.5 81 103.3C81 100.6 78.7 99 76 99.8Z"),
        ])

}

/// Rig parts in one character space (the Front figure's box on the sheet), at
/// their rest pose. Each part's paths are local to its pivot (`anchor`).
enum MascotParts {
    /// Ground shadow (bites from the feet filled)
    static let groundShadow = MascotPart(id: "groundShadow", anchor: CGPoint(x: 96.8, y: 193.9), layers: [
        TracedLayer(.shadow, .other, "M-27.4 -7C-52.1 -5.4 -67.7 -3.1 -70.6 -0.7C-71.6 0.1 -71.5 0.5 -70.2 1.3C-68.5 2.3 -66 3 -60 4.1C-44.7 6.8 -30.6 7.9 -6.8 8C27.2 8.3 54.2 6.5 66.4 3.1C70.4 2 72 1.3 72.2 0.4C72.4 -1.7 68.4 -2.8 54 -4.6L44.1 -5.9L15.6 -6.9C-0.1 -7.5 -13.4 -7.9 -13.9 -7.9C-14.5 -7.8 -20.6 -7.5 -27.4 -7Z"),
    ])

    /// Front-pose limb; pivot at the hip
    static let legLeft = MascotPart(id: "legLeft", anchor: CGPoint(x: 75.6, y: 160.3), layers: [
        TracedLayer(.red, .other, "M-2.4 -10.1C-5.1 -9.4 -8 -7 -9.2 -4.5C-9.6 -3.6 -10.3 -0.9 -11.2 3.5C-12 7.1 -12.9 10.8 -13.4 11.9C-13.8 12.9 -14.1 13.9 -14.1 14.1C-14.1 14.3 -14.3 15.1 -14.6 15.9C-14.9 16.7 -15.3 17.9 -15.5 18.7C-15.7 19.5 -16.5 21.4 -17.4 23.1C-19.7 27.9 -20 30 -18.5 32.4C-17.5 34 -14.4 35.9 -11.6 36.5C-11.1 36.6 -10.4 36.8 -10.1 37C-8.6 37.8 -2.9 37.5 0.6 36.4C3 35.7 5.2 33.5 6.5 30.6C7.1 29.4 7.7 27.7 7.9 26.9C8.1 26.2 8.3 25.5 8.4 25.3C8.5 25.2 9.1 23.5 9.6 21.5C10.2 19.5 11.1 16.6 11.6 15.1L12.5 12.3L11.4 5C10.2 -4 10 -4.5 7.4 -7.1C6 -8.5 5.2 -9.1 4 -9.5C2.4 -10.2 -0.8 -10.4 -2.4 -10.1Z"),
    ])

    /// Front-pose limb; pivot at the hip
    static let legRight = MascotPart(id: "legRight", anchor: CGPoint(x: 118.9, y: 159.1), layers: [
        TracedLayer(.red, .other, "M-2.9 -10.1C-4.9 -9.5 -6.3 -8.6 -7.7 -7.1C-9.8 -4.9 -10.1 -3.9 -11.4 4.7C-12.8 13.2 -12.8 13.1 -11.5 16.1C-11.3 16.6 -11.1 17.1 -11.1 17.3C-11.1 17.5 -11 18 -10.7 18.5C-10.5 18.9 -10.1 19.9 -9.9 20.7C-9.7 21.6 -9 23.4 -8.5 24.8C-8 26.1 -7.4 28 -7.1 28.8C-6.1 32 -2.7 35.9 0 37.2C2.7 38.5 7.2 38.4 12.2 37C14.7 36.3 15.9 35.3 18.2 32.4C19.2 31 19.2 31 19.2 28.9C19.2 27.1 19.1 26.5 18.3 24.7C17.5 22.7 15.8 17.6 14.7 14.1C14.5 13.4 14 11.9 13.6 10.8C13.2 9.8 12.3 6.2 11.6 2.8C10.9 -0.5 10.1 -3.8 9.7 -4.5C7.6 -9.1 1.9 -11.7 -2.9 -10.1Z"),
    ])

    /// Front-pose limb; pivot at the shoulder
    static let armLeft = MascotPart(id: "armLeft", anchor: CGPoint(x: 36.2, y: 126.4), layers: [
        TracedLayer(.red, .other, "M-7.9 -9.7L-14 -8.2L-16 -6.1C-21.5 -0.5 -22.4 0.8 -25.8 7.5C-28.4 12.7 -29.7 18 -29.7 23.4C-29.7 27.8 -28.7 30.3 -26.4 32C-23.5 34.2 -20.8 34.3 -16.5 32.2C-12.3 30.1 -7.9 25.6 -5.7 21.4C-4.5 18.8 -4 18.3 2.3 13C8.9 7.5 9.8 6.5 10.8 3.9C11.7 1.6 11.5 -2.5 10.4 -4.7C9.3 -6.9 6.5 -9.6 4.4 -10.4C1.5 -11.5 -0.8 -11.4 -7.9 -9.7Z"),
    ])

    /// Front-pose limb; pivot at the shoulder
    static let armRight = MascotPart(id: "armRight", anchor: CGPoint(x: 157.6, y: 123.4), layers: [
        TracedLayer(.red, .other, "M-3.7 -9.9C-10.5 -7.2 -12.7 1.5 -8 7C-7.5 7.6 -4.4 10.2 -1.1 12.7C3 15.9 5 17.7 5.2 18.2C6.9 22.4 11.6 27.7 15.8 30.2C18.9 32.1 21.3 32.9 23.8 32.9C25.9 33 26.1 32.9 27.5 32.2C30.2 30.7 31.7 28 32 24.2C32.2 22 31.9 18.1 31.3 16.4C31.1 15.7 30.8 14.7 30.6 14.1C29.4 9.7 22.4 -0.4 17.8 -4.5C13.9 -8 14.4 -7.7 8 -9.1C1.4 -10.6 -1.4 -10.8 -3.7 -9.9Z"),
    ])

    /// Pivot at the leaf base, next to the stem
    static let leaf = MascotPart(id: "leaf", anchor: CGPoint(x: 92.1, y: 38), layers: [
        TracedLayer(.leaf, .other, "M-28.2 -27.9C-31.9 -28 -36.4 -27.2 -42.2 -25.3C-45.9 -24.1 -46.3 -23.9 -45.6 -22.7C-44.8 -21.1 -44 -19.9 -42.2 -17.1C-41.5 -16.3 -40.8 -15.2 -40.5 -14.7C-39.7 -13.6 -38.8 -12.6 -37.9 -11.7C-37.1 -11.1 -36.8 -10.7 -34.8 -8C-33.6 -6.4 -32.4 -5 -31.8 -4.3C-31.6 -4.1 -31.3 -3.7 -31.2 -3.6C-31.2 -3.6 -31.1 -3.5 -31.1 -3.5C-31 -3.5 -30.9 -3.4 -30.8 -3.3C-30.8 -3.2 -30.7 -3.1 -30.6 -3.1C-30.5 -3.1 -30.5 -3 -30.5 -2.9C-30.3 -2.7 -29.4 -1.8 -29.3 -1.8C-29.1 -1.8 -28.7 -1.2 -28.8 -0.9C-28.8 -0.5 -28.4 -0.2 -26.1 0.3C-25.4 0.5 -24.7 0.8 -24.4 0.9C-23.8 1.1 -23.7 1.1 -21.8 1.1C-19.4 1.1 -16.8 1.3 -14.4 2C-13.6 2.1 -13.3 2.2 -11.5 2.8C-10.9 3 -10 3.3 -9.4 3.4C-8 3.9 -7.5 4.1 -6.3 4.6C-5.8 4.8 -5.2 5.1 -4.9 5.2C-4.7 5.3 -4.2 5.5 -3.9 5.7C-2.3 6.4 -1.7 6.7 -1 6.8L-0.4 6.8L-0.3 6.5C-0.2 6.2 0 4.9 0.1 1.8C0.3 -2.5 0.4 -2.6 0.1 -2.7C0 -2.7 0 -2.9 0.1 -5.2L0.3 -7.5L0 -7.6C-0.2 -7.7 -0.2 -7.8 -0.5 -8.9C-0.9 -10.5 -2.1 -14.1 -2.6 -14.9C-2.7 -15.1 -3 -15.6 -3.1 -15.9C-3.5 -16.8 -4.8 -18.5 -5.5 -19.3C-7 -21.1 -10.2 -23.8 -11.2 -24.3C-11.4 -24.4 -11.8 -24.6 -12.1 -24.8C-12.6 -25.2 -16.2 -26.6 -17 -26.8C-17.2 -26.9 -17.8 -27 -18.2 -27.1C-19.6 -27.4 -24.4 -27.9 -28.2 -27.9Z"),
        TracedLayer(.leafVein, .other, "M-16.6 -16.6C-16.6 -16.5 -16 -16.1 -15.4 -15.8C-14.5 -15.3 -10.4 -12.5 -10 -12.1C-9.9 -12 -9.2 -11.5 -8.4 -10.8C-6.6 -9.4 -5.4 -8.2 -3.2 -5.7C-2.3 -4.5 -1.4 -3.5 -1.3 -3.5C-1.3 -3.5 -1.1 -3.2 -1.1 -3C-0.9 -1.9 -0.4 -2.5 -0.1 -4.2C0.2 -6 0.2 -7.2 0.1 -7.2C0 -7.2 -0.2 -7.5 -0.3 -7.8C-0.6 -8.4 -0.6 -8.4 -0.5 -7.9C-0.5 -7.6 -0.5 -7.3 -0.6 -7C-0.7 -6.5 -0.9 -7.1 -1 -8.4C-1 -9.1 -1.1 -9.8 -1.2 -9.9C-1.3 -10 -1.4 -9.8 -1.3 -9.4C-1.3 -9.1 -1.3 -8.7 -1.5 -8.4C-1.7 -8.1 -1.7 -8.1 -2.1 -8.5C-3.1 -10.2 -7 -13.2 -9.2 -14.1C-13.7 -16.1 -17.3 -17.2 -16.6 -16.6Z", gradient: (-5.5, -6, -4.2, -11.8, "#388D36", "#387D38")),
    ])

    /// Pivot where it meets the body
    static let stem = MascotPart(id: "stem", anchor: CGPoint(x: 93.4, y: 45.7), layers: [
        TracedLayer(.stem, .other, "M16.2 -39.1C14.8 -38.8 13.3 -37.9 11.6 -36.6C10.3 -35.4 7.1 -32 6.4 -31C3.7 -27.4 2.6 -25.3 0.1 -19.6C-0.6 -18 -1.7 -14.8 -2.1 -13.2C-2.4 -11.7 -2.6 -11.4 -3 -11.4C-3.3 -11.3 -3.4 -11.2 -3.5 -10.9C-3.7 -10.4 -4.3 -6.3 -4.3 -5.6C-4.3 -5.4 -4.5 -5.1 -4.7 -4.8C-4.9 -4.5 -5.2 -4.1 -5.4 -3.8C-5.6 -3.5 -6.1 -2.8 -6.6 -2C-7.2 -1.3 -7.9 -0.4 -8.1 -0.1C-8.8 0.9 -9 1.2 -9.8 2.2C-10.5 3.2 -10.7 3.8 -10.3 3.9C-9.8 4.2 -9.7 4.4 -9.7 5.5C-9.7 6.2 -9.8 6.8 -9.9 7C-10.2 7.5 -10.2 7.8 -10.1 7.9C-9.8 8.1 -6.9 8.6 -6 8.7L-4.8 8.7L-4.5 8.1C-4.3 7.8 -3.8 7.4 -3.6 7.1C-3.4 6.9 -3.2 6.6 -3.2 6.6C-3.2 6.5 -3 6.1 -2.8 5.9C-2.6 5.6 -2 4.9 -1.6 4.4C-1.2 3.7 -0.7 2.9 -0.4 2.7C-0.2 2.4 0.1 2 0.1 1.9C0.1 1.9 0.4 1.5 0.8 1C1.4 0.3 1.4 0.3 2.1 0.2C3 0.1 3.9 -0.3 4.4 -1C4.8 -1.5 5.4 -2.8 5.6 -3.4C5.8 -4.3 6.5 -5.3 7.4 -5.9C8.1 -6.4 8.1 -6.6 7.7 -7L7.5 -7.4L7.8 -8.1C8 -8.4 8.6 -10 9.3 -11.3C10.8 -14.9 13.4 -19.5 14.7 -20.9C15 -21.2 15.5 -21.9 15.7 -22.2C16.2 -23 18.5 -25.7 20.5 -27.5C22.1 -29.4 22.4 -30.1 22.4 -31.9C22.5 -35.1 21.3 -37.5 19.1 -38.7C18.4 -39 16.9 -39.2 16.2 -39.1Z"),
    ])

    /// Limb-free body silhouette
    static let body = MascotPart(id: "body", anchor: CGPoint(x: 84.2, y: 107.5), layers: [
        TracedLayer(.red, .body, "M38.5 -72.2C36.2 -71.9 32.6 -71 30 -70.2C28.3 -69.7 26.9 -69.2 26.8 -69.1C26.7 -69.1 26.3 -69 26 -69C25.8 -69 23.8 -68.6 21.8 -68C17.3 -66.9 14.9 -66.4 12.1 -66C11 -65.8 9.5 -65.6 8.7 -65.4C6.9 -64.8 6.3 -64.8 4 -65.6C2.1 -66.3 -1.1 -67.2 -4 -68.1C-8.8 -69.2 -14.6 -69.5 -18.8 -68.8C-21.5 -68.3 -22.1 -68.1 -25.4 -66.3C-26.1 -65.9 -27.1 -65.3 -27.7 -65.1C-30.8 -63.5 -33.1 -62.2 -34.8 -60.9C-35.6 -60.4 -36.6 -59.6 -37.1 -59.2C-37.6 -58.9 -38.3 -58.3 -38.5 -58.1C-38.7 -57.8 -39.4 -57.3 -39.9 -56.8C-42.7 -54.5 -47 -49.2 -49.8 -45C-52.1 -41.5 -54.2 -37.5 -55.5 -34.2C-55.8 -33.4 -56.2 -32.6 -56.3 -32.4C-56.4 -32.2 -56.5 -31.7 -56.6 -31.2C-56.8 -30.9 -57 -30.3 -57.1 -30C-57.4 -29.2 -57.8 -27.8 -58.8 -24.6C-60.5 -19.1 -61.6 -10.6 -61.6 -3.9C-61.5 -2.4 -61.5 -0.7 -61.4 -0.1C-61.4 0.5 -61.3 1.8 -61.2 2.6C-61.1 4.7 -61.1 4.6 -60.4 8.8C-60.1 10.8 -59.6 13.1 -59.5 13.8C-59.2 14.5 -58.8 16.2 -58.5 17.5C-58 19.1 -57.5 20.6 -56.7 22.8C-52.9 32.1 -49.2 38.1 -42.5 45.4C-39.2 49 -33.7 53.1 -29.1 55.5C-21.7 59.4 -12.1 62.3 -3.2 63.3C1 63.8 9.9 63.9 15.4 63.8C21.4 63.6 29.5 62.5 33.2 61.6C33.5 61.5 34.5 61.3 35.4 61.2C36.2 61 37 60.8 37.2 60.7C37.4 60.6 38.4 60.3 39.4 59.9C40.5 59.6 41.6 59.1 42 59.1C42.3 58.9 42.7 58.8 42.8 58.8C42.9 58.8 43.3 58.6 43.6 58.5C44.6 58 45.9 57.4 46.8 57.1C47.6 56.8 54.3 53.3 54.8 52.8C55 52.8 55.2 52.5 55.3 52.5C55.4 52.6 60.2 49.1 60.7 48.6C60.9 48.5 61.4 48 61.9 47.6C62.4 47.2 62.9 46.6 63.2 46.4C64.9 45 69.8 39.9 71.2 38.2C72.8 36.2 73.4 35.5 75.4 32.7C77.4 29.8 80.5 24.2 81.5 21.5C81.7 21 82.1 20.2 82.3 19.8C83.2 17.9 84.6 13.6 85.6 9.6C86.9 4.6 87.4 2.2 87.9 -2.8C88.1 -5.1 88.5 -14.3 88.4 -16.3C88.3 -17.5 87.8 -23.1 87.6 -24.1C87.6 -24.7 87.4 -25.9 87.3 -27.1C86.9 -29.5 86.9 -29.7 86 -32.9C85.7 -34.2 85.3 -35.5 85.3 -35.9C85.2 -36.2 85 -36.8 84.9 -37.1C84.9 -37.5 84.6 -38.3 84.4 -38.9C84.2 -39.5 83.9 -40.4 83.8 -40.8C83.6 -41.2 83.3 -41.9 83.2 -42.4C82.5 -44.4 79.4 -50.3 77.6 -53.2C74 -58.6 68.8 -64 65 -66.3C63.5 -67.2 60.6 -68.6 59.2 -69.3C58.1 -69.7 53.1 -71.3 51.7 -71.7C50.2 -72 40 -72.4 38.5 -72.2Z"),
    ])

    /// Soft joint shading, shown on the limb just below the body edge; moves with legLeft
    static let legLeftShade = MascotPart(id: "legLeftShade", anchor: CGPoint(x: 75.6, y: 160.3), follows: "legLeft", layers: [
        TracedLayer(.redShade, .other, "M0.4 2.7C6.475 2.7 11.4 4.939 11.4 7.7C11.4 10.461 6.475 12.7 0.4 12.7C-5.675 12.7 -10.6 10.461 -10.6 7.7C-10.6 4.939 -5.675 2.7 0.4 2.7Z", blur: 2.2),
    ])

    /// Soft joint shading, shown on the limb just below the body edge; moves with legRight
    static let legRightShade = MascotPart(id: "legRightShade", anchor: CGPoint(x: 118.9, y: 159.1), follows: "legRight", layers: [
        TracedLayer(.redShade, .other, "M0.1 1.9C6.175 1.9 11.1 4.139 11.1 6.9C11.1 9.661 6.175 11.9 0.1 11.9C-5.975 11.9 -10.9 9.661 -10.9 6.9C-10.9 4.139 -5.975 1.9 0.1 1.9Z", blur: 2.2),
    ])

    /// Soft joint shading, shown on the limb just below the body edge; moves with armLeft
    static let armLeftShade = MascotPart(id: "armLeftShade", anchor: CGPoint(x: 36.2, y: 126.4), follows: "armLeft", layers: [
        TracedLayer(.redShade, .other, "M-5.2 4.6C-2.162 4.6 0.3 8.629 0.3 13.6C0.3 18.571 -2.162 22.6 -5.2 22.6C-8.238 22.6 -10.7 18.571 -10.7 13.6C-10.7 8.629 -8.238 4.6 -5.2 4.6Z", blur: 2.2),
    ])

    /// Soft joint shading, shown on the limb just below the body edge; moves with armRight
    static let armRightShade = MascotPart(id: "armRightShade", anchor: CGPoint(x: 157.6, y: 123.4), follows: "armRight", layers: [
        TracedLayer(.redShade, .other, "M7.9 4.6C10.938 4.6 13.4 8.629 13.4 13.6C13.4 18.571 10.938 22.6 7.9 22.6C4.862 22.6 2.4 18.571 2.4 13.6C2.4 8.629 4.862 4.6 7.9 4.6Z", blur: 2.2),
    ])

    /// Sclera
    static let eyeLeft = MascotPart(id: "eyeLeft", anchor: CGPoint(x: 68.5, y: 109.9), layers: [
        TracedLayer(.white, .face, "M-0.49 -24.357C10.124 -24.357 18.729 -13.43 18.729 0.048C18.729 13.526 10.124 24.452 -0.49 24.452C-11.105 24.452 -19.71 13.526 -19.71 0.048C-19.71 -13.43 -11.105 -24.357 -0.49 -24.357Z"),
    ])

    /// Sclera
    static let eyeRight = MascotPart(id: "eyeRight", anchor: CGPoint(x: 133.3, y: 107.5), layers: [
        TracedLayer(.white, .face, "M-0.02 -24.496C10.594 -24.496 19.199 -13.57 19.199 -0.092C19.199 13.387 10.594 24.313 -0.02 24.313C-10.635 24.313 -19.24 13.387 -19.24 -0.092C-19.24 -13.57 -10.635 -24.496 -0.02 -24.496Z"),
    ])

    /// Pupil + glint
    static let pupilLeft = MascotPart(id: "pupilLeft", anchor: CGPoint(x: 77.1, y: 108.8), layers: [
        TracedLayer(.dark, .face, "M-0.716 -17.271C6.304 -17.271 11.996 -9.326 11.996 0.475C11.996 10.275 6.304 18.22 -0.716 18.22C-7.736 18.22 -13.427 10.275 -13.427 0.475C-13.427 -9.326 -7.736 -17.271 -0.716 -17.271Z"),
        TracedLayer(.white, .face, "M2.608 -12.139C4.244 -12.139 5.57 -10.566 5.57 -8.624C5.57 -6.683 4.244 -5.109 2.608 -5.109C0.972 -5.109 -0.354 -6.683 -0.354 -8.624C-0.354 -10.566 0.972 -12.139 2.608 -12.139Z"),
    ])

    /// Pupil + glint
    static let pupilRight = MascotPart(id: "pupilRight", anchor: CGPoint(x: 140.6, y: 107.4), layers: [
        TracedLayer(.dark, .face, "M1.054 -18.41C8.074 -18.41 13.765 -10.465 13.765 -0.665C13.765 9.136 8.074 17.081 1.054 17.081C-5.967 17.081 -11.658 9.136 -11.658 -0.665C-11.658 -10.465 -5.967 -18.41 1.054 -18.41Z"),
        TracedLayer(.white, .face, "M4.378 -13.279C6.014 -13.279 7.34 -11.705 7.34 -9.764C7.34 -7.822 6.014 -6.249 4.378 -6.249C2.742 -6.249 1.416 -7.822 1.416 -9.764C1.416 -11.705 2.742 -13.279 4.378 -13.279Z"),
    ])

    static let blushLeft = MascotPart(id: "blushLeft", anchor: CGPoint(x: 52.3, y: 143.4), layers: [
        TracedLayer(.pink, .face, "M2.998 -7.851C8.173 -5.6 10.927 -0.462 9.149 3.625C7.37 7.712 1.734 9.199 -3.441 6.948C-8.616 4.696 -11.37 -0.442 -9.591 -4.529C-7.813 -8.615 -2.177 -10.103 2.998 -7.851Z", blur: 0.6),
    ])

    static let blushRight = MascotPart(id: "blushRight", anchor: CGPoint(x: 145.8, y: 136.5), layers: [
        TracedLayer(.pink, .face, "M-2.996 -7.351C2.179 -9.602 7.815 -8.115 9.593 -4.028C11.371 0.059 8.618 5.197 3.443 7.448C-1.732 9.7 -7.369 8.212 -9.147 4.126C-10.925 0.039 -8.171 -5.099 -2.996 -7.351Z", blur: 0.6),
    ])

    static let mouthNeutral = MascotPart(id: "mouthNeutral", anchor: CGPoint(x: 101.3, y: 128.4), layers: [
        TracedLayer(.dark, .face, "M-13.092 -3.565C-12.626 -0.696 -11.136 1.808 -9.01 3.61C-8.395 4.132 -5.412 6.637 -0.655 6.637C4.101 6.637 7.084 4.132 7.7 3.61C9.825 1.808 11.315 -0.696 11.781 -3.565C11.976 -4.767 11.405 -5.963 10.348 -6.567C9.292 -7.17 7.971 -7.055 7.035 -6.277C4.91 -4.511 2.222 -3.659 -0.655 -3.659C-3.533 -3.659 -6.221 -4.511 -8.346 -6.277C-9.282 -7.055 -10.602 -7.17 -11.659 -6.567C-12.716 -5.963 -13.287 -4.767 -13.092 -3.565Z"),
    ])

    static let browLeft = MascotPart(id: "browLeft", anchor: CGPoint(x: 66.7, y: 69.8), layers: [
        TracedLayer(.dark, .face, "M6.734 -5.761C1.296 -6.496 -1.968 -4.988 -3.076 -4.46C-5.524 -3.295 -7.334 -1.574 -8.616 -0.168C-9.564 0.871 -9.489 2.481 -8.451 3.428C-7.412 4.375 -5.802 4.3 -4.855 3.262C-3.925 2.242 -2.63 0.965 -0.888 0.136C0.311 -0.435 2.427 -1.207 6.053 -0.717C7.446 -0.529 8.727 -1.505 8.916 -2.898C9.104 -4.291 8.127 -5.573 6.734 -5.761Z"),
    ])

    static let browRight = MascotPart(id: "browRight", anchor: CGPoint(x: 136.2, y: 67), layers: [
        TracedLayer(.dark, .face, "M8.436 0.57C7.153 -0.837 5.343 -2.557 2.895 -3.723C1.788 -4.25 -1.477 -5.759 -6.915 -5.024C-8.308 -4.835 -9.285 -3.554 -9.097 -2.161C-8.908 -0.768 -7.626 0.209 -6.234 0.021C-2.608 -0.469 -0.492 0.302 0.707 0.873C2.449 1.702 3.744 2.979 4.674 3.999C5.621 5.038 7.231 5.112 8.27 4.165C9.308 3.218 9.383 1.608 8.436 0.57Z"),
    ])

    /// Lid line
    static let lashLeft = MascotPart(id: "lashLeft", anchor: CGPoint(x: 63.1, y: 88.9), layers: [
        TracedLayer(.dark, .face, "M-9.341 4.502C-6.722 0.873 -4.767 -1.844 -1.553 -3.19C1.858 -4.618 5.281 -3.825 8.601 -3.005C8.695 -2.982 8.752 -2.887 8.729 -2.793C8.706 -2.7 8.611 -2.642 8.517 -2.665C7.124 -3.009 3.406 -3.749 -1.012 -1.898C-2.72 -1.183 -6.084 0.586 -9.058 4.707C-9.114 4.785 -9.223 4.803 -9.302 4.746C-9.38 4.69 -9.398 4.58 -9.341 4.502Z"),
    ])

    /// Lid line
    static let lashRight = MascotPart(id: "lashRight", anchor: CGPoint(x: 139.1, y: 86.7), layers: [
        TracedLayer(.dark, .face, "M8.431 4.163C8.487 4.241 8.47 4.35 8.391 4.407C8.313 4.463 8.203 4.446 8.147 4.367C5.173 0.247 1.809 -1.523 0.102 -2.238C-4.317 -4.088 -8.035 -3.349 -9.428 -3.005C-9.522 -2.982 -9.616 -3.039 -9.64 -3.133C-9.663 -3.227 -9.605 -3.322 -9.512 -3.345C-6.192 -4.164 -2.769 -4.958 0.643 -3.529C3.857 -2.183 5.812 0.533 8.431 4.163Z"),
    ])

    static let mouthHappy = MascotPart(id: "mouthHappy", anchor: CGPoint(x: 100.9, y: 130), layers: [
        TracedLayer(.dark, .face, "M-1.072 -8.359C5.302 -8.926 8.881 -12.887 11.922 -11.156C15.968 -8.853 12.923 3.488 10.592 6.374C10.247 6.801 5.345 10.872 4.963 11.104C3.591 11.941 2.018 12.309 0.778 12.419C-0.461 12.53 -2.074 12.445 -3.573 11.865C-3.99 11.703 -9.534 8.562 -9.949 8.203C-12.753 5.775 -17.931 -5.834 -14.355 -8.816C-11.668 -11.057 -7.446 -7.791 -1.072 -8.359Z"),
        TracedLayer(.pink, .face, "M8.05 8.595C6.653 9.767 5.167 10.981 4.963 11.104C3.591 11.941 2.018 12.309 0.778 12.419C-0.461 12.53 -2.074 12.445 -3.573 11.865C-3.795 11.779 -5.473 10.847 -7.055 9.94C-7.823 9.117 -8.307 8.134 -8.403 7.05C-8.706 3.651 -5.085 0.551 -0.316 0.126C4.453 -0.298 8.564 2.113 8.867 5.513C8.963 6.596 8.661 7.65 8.05 8.595Z"),
    ])

    static let mouthExcited = MascotPart(id: "mouthExcited", anchor: CGPoint(x: 103.2, y: 133.1), layers: [
        TracedLayer(.dark, .face, "M-1.288 -8.88C8.259 -9.191 8.318 -12.831 11.647 -9.657C14.921 -6.536 12.441 4.783 5.881 9.073C4.968 9.67 0.995 11.294 -0.63 11.347C-2.255 11.4 -6.324 10.038 -7.274 9.501C-14.099 5.647 -17.31 -5.486 -14.246 -8.814C-11.131 -12.198 -10.835 -8.569 -1.288 -8.88Z"),
        TracedLayer(.pink, .face, "M5.564 9.257C4.272 9.95 0.849 11.299 -0.63 11.347C-2.108 11.395 -5.611 10.272 -6.946 9.665C-7.671 8.795 -8.107 7.755 -8.144 6.628C-8.249 3.402 -5.042 0.679 -0.981 0.547C3.079 0.415 6.456 2.923 6.561 6.15C6.598 7.277 6.231 8.342 5.564 9.257Z"),
    ])

    static let mouthCurious = MascotPart(id: "mouthCurious", anchor: CGPoint(x: 110.1, y: 131), layers: [
        TracedLayer(.dark, .face, "M-1.033 -11.098C-1.054 -11.096 2.977 -11.764 5.711 -9.914C8.825 -7.807 8.895 -1.343 7.201 0.162C6.068 1.169 4.467 0.77 3.423 2.054C1.863 3.972 4.022 6.235 2.813 8.045C2.34 8.752 1.504 9.086 0.698 9.154C-0.108 9.223 -0.989 9.037 -1.574 8.42C-3.073 6.841 -1.33 4.245 -3.193 2.62C-4.44 1.532 -5.95 2.197 -7.237 1.397C-9.162 0.2 -10.19 -6.182 -7.479 -8.786C-5.099 -11.074 -1.012 -11.1 -1.033 -11.098Z"),
    ])

    static let mouthThinking = MascotPart(id: "mouthThinking", anchor: CGPoint(x: 110, y: 129.4), layers: [
        TracedLayer(.dark, .face, "M-3.692 2.953C-3.033 -0.164 -1.043 -0.805 -0.3 -0.905C0.443 -1.006 2.531 -0.917 3.994 1.913C4.552 2.992 5.862 3.437 6.961 2.923C8.061 2.409 8.559 1.118 8.089 -0.001C6.034 -4.897 1.933 -6.202 -0.964 -5.81C-3.861 -5.418 -7.468 -3.07 -8.148 2.196C-8.303 3.4 -7.481 4.512 -6.284 4.715C-5.087 4.919 -3.943 4.141 -3.692 2.953Z"),
    ])

    static let mouthSad = MascotPart(id: "mouthSad", anchor: CGPoint(x: 94.9, y: 131), layers: [
        TracedLayer(.dark, .face, "M-5.923 2.839C-5.272 0.487 -3.412 -1.025 -1.173 -1.376C1.067 -1.726 3.299 -0.854 4.637 1.187C5.191 2.033 6.299 2.317 7.192 1.842C8.085 1.367 8.469 0.289 8.077 -0.643C6.242 -5.01 1.947 -6.812 -1.928 -6.206C-5.804 -5.6 -9.343 -2.572 -9.757 2.146C-9.846 3.154 -9.151 4.063 -8.156 4.243C-7.16 4.422 -6.192 3.814 -5.923 2.839Z"),
    ])

    static let mouthWink = MascotPart(id: "mouthWink", anchor: CGPoint(x: 106.7, y: 130.9), layers: [
        TracedLayer(.dark, .face, "M-1.703 -8.869C4.2 -9.061 6.977 -12.174 10.151 -10.717C16.387 -7.856 9.933 5.438 5.61 8.534C4.477 9.345 0.305 10.747 -1.065 10.791C-2.434 10.836 -6.689 9.708 -7.871 8.972C-12.386 6.163 -19.689 -6.685 -13.652 -9.945C-10.579 -11.604 -7.606 -8.677 -1.703 -8.869Z"),
        TracedLayer(.pink, .face, "M4.687 9.042C3.007 9.825 0.047 10.755 -1.065 10.791C-2.177 10.827 -5.19 10.091 -6.918 9.418C-8.125 8.369 -8.881 6.971 -8.931 5.416C-9.042 1.994 -5.692 -0.892 -1.448 -1.03C2.795 -1.168 6.326 1.495 6.437 4.918C6.487 6.472 5.824 7.916 4.687 9.042Z"),
    ])

    static let browLeftHappy = MascotPart(id: "browLeftHappy", anchor: CGPoint(x: 64.7, y: 73.9), layers: [
        TracedLayer(.dark, .face, "M4.03 -5.768C-0.307 -5.105 -4.879 -2.296 -7.122 -0.078C-8.121 0.91 -8.13 2.521 -7.142 3.521C-6.154 4.52 -4.542 4.529 -3.543 3.541C-1.998 2.014 1.671 -0.258 4.799 -0.736C6.189 -0.949 7.143 -2.247 6.93 -3.637C6.718 -5.026 5.419 -5.981 4.03 -5.768Z"),
    ])

    static let browRightHappy = MascotPart(id: "browRightHappy", anchor: CGPoint(x: 128.2, y: 64.6), layers: [
        TracedLayer(.dark, .face, "M-4.349 2.036C-0.193 0.848 3.063 2.046 3.956 2.616C5.141 3.372 6.714 3.024 7.47 1.839C8.226 0.654 7.878 -0.92 6.693 -1.676C6.594 -1.739 4.846 -2.958 1.5 -3.402C0.35 -3.555 -2.413 -3.811 -5.748 -2.858C-7.1 -2.472 -7.882 -1.063 -7.496 0.289C-7.109 1.64 -5.701 2.423 -4.349 2.036Z"),
    ])

    static let browLeftExcited = MascotPart(id: "browLeftExcited", anchor: CGPoint(x: 64.4, y: 70.2), layers: [
        TracedLayer(.dark, .face, "M6.063 -6.787C3.34 -7.005 0.25 -5.995 -2.398 -4.49C-4.857 -3.092 -7.287 -1.041 -8.319 1.141C-8.919 2.412 -8.376 3.929 -7.105 4.529C-5.834 5.13 -4.317 4.587 -3.717 3.316C-2.75 1.27 2.416 -1.973 5.657 -1.713C7.058 -1.601 8.285 -2.646 8.397 -4.048C8.509 -5.449 7.464 -6.675 6.063 -6.787Z"),
    ])

    static let browRightExcited = MascotPart(id: "browRightExcited", anchor: CGPoint(x: 133.6, y: 62.6), layers: [
        TracedLayer(.dark, .face, "M-5.891 0.427C-2.135 -0.971 2.268 0.859 3.879 3.002C4.724 4.125 6.32 4.351 7.443 3.506C8.566 2.661 8.792 1.066 7.947 -0.058C7.087 -1.202 5.007 -3.322 1.312 -4.473C-0.978 -5.187 -4.299 -5.597 -7.666 -4.344C-8.983 -3.854 -9.654 -2.389 -9.164 -1.072C-8.674 0.246 -7.209 0.917 -5.891 0.427Z"),
    ])

    static let browLeftCurious = MascotPart(id: "browLeftCurious", anchor: CGPoint(x: 70.5, y: 70.9), layers: [
        TracedLayer(.dark, .face, "M5.809 -6.959C1.272 -6.639 -1.638 -4.983 -2.697 -4.357C-4.834 -3.092 -6.655 -1.442 -8.135 0.468C-8.996 1.579 -8.794 3.177 -7.683 4.039C-6.572 4.9 -4.974 4.697 -4.112 3.587C-1.462 0.168 2.154 -1.598 6.168 -1.881C7.57 -1.98 8.626 -3.197 8.527 -4.599C8.428 -6.001 7.212 -7.058 5.809 -6.959Z"),
    ])

    static let browRightCurious = MascotPart(id: "browRightCurious", anchor: CGPoint(x: 133.7, y: 60.5), layers: [
        TracedLayer(.dark, .face, "M-4.312 1.985C-1.518 0.332 2.406 1.992 3.64 2.829C4.804 3.618 6.386 3.314 7.175 2.15C7.964 0.987 7.66 -0.596 6.496 -1.384C6.246 -1.554 4.177 -2.972 0.977 -3.572C-1.665 -4.067 -4.471 -3.835 -6.904 -2.395C-8.114 -1.68 -8.514 -0.119 -7.799 1.091C-7.083 2.301 -5.522 2.701 -4.312 1.985Z"),
    ])

    static let browLeftThinking = MascotPart(id: "browLeftThinking", anchor: CGPoint(x: 73.4, y: 73.2), layers: [
        TracedLayer(.dark, .face, "M3.845 -6.561C3.548 -5.89 2.62 -4.006 -0.966 -1.642C-3.113 -0.226 -5.552 0.949 -8.086 2.067C-9.372 2.634 -9.955 4.137 -9.388 5.423C-8.82 6.709 -7.318 7.291 -6.032 6.724C-1.367 4.666 0.788 3.299 1.836 2.607C4.011 1.174 7.034 -1.186 8.5 -4.502C9.069 -5.787 8.488 -7.29 7.202 -7.859C5.917 -8.427 4.414 -7.846 3.845 -6.561Z"),
    ])

    static let browRightThinking = MascotPart(id: "browRightThinking", anchor: CGPoint(x: 131.5, y: 63.4), layers: [
        TracedLayer(.dark, .face, "M-7.021 1.21C-4.608 1.559 -3.302 1.567 -0.053 1.79C2.714 1.98 4.013 2.284 4.986 2.652C6.3 3.15 7.769 2.488 8.267 1.173C8.764 -0.142 8.102 -1.611 6.787 -2.108C2.84 -3.602 -1.572 -3.144 -6.291 -3.828C-7.682 -4.03 -8.973 -3.065 -9.175 -1.674C-9.376 -0.283 -8.412 1.008 -7.021 1.21Z"),
    ])

    static let browLeftSad = MascotPart(id: "browLeftSad", anchor: CGPoint(x: 64.3, y: 73.1), layers: [
        TracedLayer(.dark, .face, "M3.034 -6.042C1.949 -4.922 0.617 -3.573 -1.085 -2.378C-1.576 -2.034 -3.566 -0.624 -7.577 0.926C-8.888 1.432 -9.54 2.906 -9.034 4.217C-8.527 5.528 -7.054 6.18 -5.742 5.674C-1.318 3.964 0.847 2.484 1.839 1.788C3.89 0.349 5.433 -1.203 6.689 -2.498C7.667 -3.507 7.642 -5.118 6.633 -6.097C5.624 -7.075 4.013 -7.051 3.034 -6.042Z"),
    ])

    static let browRightSad = MascotPart(id: "browRightSad", anchor: CGPoint(x: 128.3, y: 68.4), layers: [
        TracedLayer(.dark, .face, "M6.419 1.022C2.373 -0.435 0.352 -1.798 -0.147 -2.131C-1.876 -3.286 -3.239 -4.604 -4.35 -5.698C-5.352 -6.684 -6.963 -6.672 -7.949 -5.67C-8.935 -4.669 -8.923 -3.057 -7.921 -2.071C-6.636 -0.806 -5.058 0.71 -2.974 2.102C-1.967 2.775 0.233 4.204 4.695 5.811C6.018 6.287 7.476 5.601 7.952 4.279C8.428 2.956 7.742 1.498 6.419 1.022Z"),
    ])

    static let browLeftWink = MascotPart(id: "browLeftWink", anchor: CGPoint(x: 66.9, y: 68.5), layers: [
        TracedLayer(.dark, .face, "M5.63 -5.688C2.449 -5.747 -0.475 -4.776 -2.564 -3.759C-6.267 -1.954 -8.085 0.306 -8.675 1.127C-9.495 2.269 -9.235 3.859 -8.093 4.679C-6.952 5.5 -5.362 5.239 -4.541 4.098C-2.785 1.654 1.62 -0.672 5.536 -0.599C6.941 -0.573 8.102 -1.691 8.128 -3.096C8.154 -4.502 7.036 -5.662 5.63 -5.688Z"),
    ])

    static let browRightWink = MascotPart(id: "browRightWink", anchor: CGPoint(x: 136.1, y: 67.7), layers: [
        TracedLayer(.dark, .face, "M-5.36 0.931C0.822 -0.548 3.436 2.129 4.316 3.008C5.31 4.002 6.921 4.002 7.915 3.008C8.909 2.014 8.909 0.403 7.915 -0.591C5.485 -3.02 3.011 -3.872 1.473 -4.232C0.577 -4.442 -2.151 -5.07 -6.544 -4.019C-7.911 -3.692 -8.754 -2.319 -8.427 -0.952C-8.1 0.415 -6.727 1.258 -5.36 0.931Z"),
    ])

    /// Closed eye (from Happy)
    static let eyeClosedLeft = MascotPart(id: "eyeClosedLeft", anchor: CGPoint(x: 70.5, y: 110.1), layers: [
        TracedLayer(.dark, .face, "M15.866 0.109C13.181 -5.615 9.319 -8.162 8.206 -8.872C3.54 -11.854 -0.665 -11.604 -2.154 -11.444C-4.155 -11.229 -8.263 -10.386 -12.046 -6.26C-12.793 -5.446 -14.31 -3.658 -15.693 -0.735C-15.878 -0.345 -17.214 2.367 -18.095 6.671C-18.385 8.087 -17.472 9.471 -16.055 9.761C-14.639 10.051 -13.255 9.138 -12.965 7.721C-11.819 2.121 -9.809 -0.952 -8.187 -2.722C-5.444 -5.712 -2.617 -6.128 -1.594 -6.238C-0.739 -6.33 2.09 -6.567 5.387 -4.46C6.526 -3.733 9.169 -1.838 11.126 2.333C11.74 3.642 13.299 4.206 14.608 3.592C15.917 2.977 16.48 1.418 15.866 0.109Z"),
    ])

    /// Closed eye (from Happy)
    static let eyeClosedRight = MascotPart(id: "eyeClosedRight", anchor: CGPoint(x: 132.4, y: 101.2), layers: [
        TracedLayer(.dark, .face, "M16.749 0.809C15.354 -2.384 13.088 -5.236 10.199 -7.289C7.968 -8.874 4.624 -10.488 0.525 -10.506C-1.324 -10.515 -5.468 -10.253 -9.826 -6.707C-10.652 -6.035 -12.432 -4.478 -14.257 -1.79C-14.907 -0.832 -16.433 1.549 -17.838 5.213C-18.356 6.563 -17.681 8.077 -16.331 8.595C-14.981 9.113 -13.467 8.438 -12.949 7.088C-10.286 0.143 -7.03 -2.231 -6.521 -2.646C-3.36 -5.217 -0.487 -5.275 0.502 -5.27C1.265 -5.267 4.069 -5.221 7.166 -3.02C9.077 -1.662 10.833 0.349 11.95 2.905C12.529 4.23 14.072 4.835 15.397 4.256C16.722 3.678 17.327 2.134 16.749 0.809Z"),
    ])

    /// Unplaced (joints set in step 2-3)
    static let arm = MascotPart(id: "arm", anchor: CGPoint(x: 41.1, y: 46.6), layers: [
        TracedLayer(.red, .body, "M17.9 -37.6C16.7 -37.4 14.3 -36.7 11.8 -35.8C10.7 -35.3 6.2 -33.1 4.3 -32C-0.4 -29.2 -4.9 -25.6 -10.6 -19.9C-18.6 -11.8 -25.3 -2.7 -28.6 4.9C-31 10.3 -31.9 13.3 -32.5 17.5C-33.3 23.8 -32 28.6 -28.3 32.5C-23.9 37.3 -16.3 38.2 -9.9 34.7C-5.8 32.6 0.1 26.7 5.1 19.9C9.8 13.7 15.2 6.5 17.9 3.2C22.6 -2.7 27.9 -10 27.9 -10.5C27.9 -10.6 28.1 -11 28.4 -11.3C29.1 -12.4 30.8 -15.8 31.4 -17.5C33.3 -23.2 33.3 -28 31.1 -32.1C30.3 -33.8 29.8 -34.3 28.3 -35.5C25.5 -37.5 22.2 -38.2 17.9 -37.6Z"),
    ])

    /// Unplaced (joints set in step 2-3)
    static let leg = MascotPart(id: "leg", anchor: CGPoint(x: 32.5, y: 49.8), layers: [
        TracedLayer(.red, .body, "M2.1 -41C-4.5 -39.8 -9.8 -37.1 -16.6 -31.6C-21.4 -27.8 -24.5 -24.6 -24.5 -23.4C-24.5 -22.9 -21.7 -19.9 -19.9 -18.4C-14.9 -14.5 -11.8 -11.2 -11.2 -9.2C-10.6 -7.1 -12.2 -1 -15 5.5C-15.3 6 -15.5 6.6 -15.5 6.8C-15.5 6.9 -16.1 8.1 -16.7 9.5C-22.1 20.8 -22.3 21.2 -22.8 22.8C-24.3 27.5 -23.3 30.2 -19.1 33.2C-17.6 34.2 -11.6 37.2 -11 37.2C-10.8 37.2 -10.2 37.5 -9.5 37.8C-4.5 39.8 6.2 42 11.1 42C15.1 42 17.2 39.8 17.2 35.8C17.2 32 15.4 27.8 12.2 24.5C11.7 24 11.2 23.3 11.2 23.2C11.2 23 11.8 22 12.5 21.2C15.8 17.2 18.4 11.9 20.9 4.5C22.1 0.8 22.2 0.1 22.5 -1C22.6 -1.9 22.9 -3.1 23.1 -4.1C23.2 -5 23.6 -7.8 23.8 -10.1C24.6 -22.1 21.6 -32.1 15.5 -37.9C12.1 -41 7.7 -42 2.1 -41Z"),
    ])

    /// Unplaced (joints set in step 2-3)
    static let hand = MascotPart(id: "hand", anchor: CGPoint(x: 38.4, y: 36.6), layers: [
        TracedLayer(.red, .body, "M-6.9 -27C-11.9 -24.9 -15.4 -20.5 -19.8 -10.5C-21 -8 -23.4 -2.9 -25.3 0.9C-30.9 11.9 -31.3 14.2 -28.2 18.1C-25.1 22 -20.8 24.5 -13.1 26.8C-9.4 27.8 -0.2 27.9 3.8 26.9C11.1 25.1 16.2 22 21.5 16.4C28.6 8.6 31.3 -1.8 27.8 -7.3C24.5 -12.5 18.5 -13.8 9 -11.3C7.9 -11 6.7 -10.8 6.2 -10.8L5.5 -10.8L5.6 -12.1C5.7 -12.8 5.7 -15.2 5.7 -17.2C5.7 -20.8 5.7 -21.1 5.1 -22.2C3.8 -24.8 2.6 -26.1 0.6 -27C-1.2 -27.8 -4.9 -27.8 -6.9 -27Z"),
    ])

    /// Unplaced (joints set in step 2-3)
    static let foot = MascotPart(id: "foot", anchor: CGPoint(x: 39.1, y: 30.3), layers: [
        TracedLayer(.red, .body, "M5 -22.1C2.7 -21.8 -1.7 -20.6 -3.3 -19.8C-3.5 -19.8 -4.4 -19.3 -5.2 -18.9C-16.4 -13.7 -26.3 -4.2 -29.4 4.3C-30.1 6.2 -30.2 6.6 -30.2 9.8C-30.2 13.2 -30.2 13.4 -29.5 14.8C-27.1 20.1 -21.9 22.6 -13.3 22.6C-1.4 22.6 13.1 17.8 21.3 11.2C24.7 8.4 28.3 3.9 29 1.6C29.1 1.3 29.3 0.6 29.6 -0.1C30.2 -1.9 30.1 -6.9 29.4 -9C27.7 -13.9 24.1 -17.5 18.9 -19.8C14.3 -21.6 9.2 -22.5 5 -22.1Z"),
    ])

    /// Draw order for the character at rest.
    static let stack: [MascotPart] = [groundShadow, legLeft, legRight, armLeft, armRight, leaf, stem, body, legLeftShade, legRightShade, armLeftShade, armRightShade, eyeLeft, eyeRight, pupilLeft, pupilRight, blushLeft, blushRight, mouthNeutral, browLeft, browRight, lashLeft, lashRight]
    /// Swappable mouths, brows and closed eyes, placed where each sheet head puts them.
    static let variants: [MascotPart] = [mouthHappy, mouthExcited, mouthCurious, mouthThinking, mouthSad, mouthWink, browLeftHappy, browRightHappy, browLeftExcited, browRightExcited, browLeftCurious, browRightCurious, browLeftThinking, browRightThinking, browLeftSad, browRightSad, browLeftWink, browRightWink, eyeClosedLeft, eyeClosedRight]
    /// The loose arm, leg, hand and foot from the sheet's parts row (reference shapes).
    static let partsRow: [MascotPart] = [arm, leg, hand, foot]
    static let variantsByID: [String: MascotPart] = Dictionary(uniqueKeysWithValues: variants.map { ($0.id, $0) })
}

enum MascotRig {
    static let size = CGSize(width: 196, height: 208)

    /// Measured from the sheet heads: each open eye's white (centre, uniform scale) and
    /// pupil (centre) fitted to that head's edges with the constructed eye proportions.
    static let eyePresets: [String: MascotEyePreset] = [
        "neutral": MascotEyePreset(),
        "happy": MascotEyePreset(closedLeft: true, closedRight: true),
        "excited": MascotEyePreset(scaleLeft: 1.035, scaleRight: 0.971, eyeShiftLeft: CGVector(dx: 0.68, dy: 0.19), eyeShiftRight: CGVector(dx: -0.06, dy: -3.87), pupilShiftLeft: CGVector(dx: 1.56, dy: 0.06), pupilShiftRight: CGVector(dx: -0.28, dy: -0.69)),
        "curious": MascotEyePreset(scaleLeft: 1.034, scaleRight: 0.987, eyeShiftLeft: CGVector(dx: 7.15, dy: 1.73), eyeShiftRight: CGVector(dx: 3.99, dy: -3.85), pupilShiftLeft: CGVector(dx: 1.85, dy: -0.7), pupilShiftRight: CGVector(dx: 1.42, dy: -4.68)),
        "thinking": MascotEyePreset(scaleLeft: 1.034, scaleRight: 0.941, eyeShiftLeft: CGVector(dx: 8.38, dy: 1.79), eyeShiftRight: CGVector(dx: -0.2, dy: -5.52), pupilShiftLeft: CGVector(dx: 1.68, dy: -5.37), pupilShiftRight: CGVector(dx: 1.48, dy: -6.01)),
        "sad": MascotEyePreset(scaleLeft: 0.977, scaleRight: 0.963, eyeShiftLeft: CGVector(dx: -0.79, dy: 3.04), eyeShiftRight: CGVector(dx: -5.62, dy: 3.64), pupilShiftLeft: CGVector(dx: 2.12, dy: -0.33), pupilShiftRight: CGVector(dx: 0.7, dy: -4.31)),
        "wink": MascotEyePreset(scaleLeft: 1.023, eyeShiftLeft: CGVector(dx: 1.84, dy: -0.78), pupilShiftLeft: CGVector(dx: 1.58, dy: 0.53), closedRight: true),
    ]

    /// Outer outline of the traced Front figure (fit check only).
    static let frontOutline = TracedPathParser.parse("M109.5 7C106.2 7.6 101.2 12.2 97.3 18.1C96.4 19.3 94.4 23.9 93.8 25.9C93.1 28 92.4 28.1 91.8 26.2C91.2 24.6 89.7 21.2 89 20.3C88.7 19.9 88 19 87.4 18.3C86.4 16.9 83.9 15 82.3 14.3C81.8 14.1 81.1 13.8 80.8 13.5C79.6 12.8 76.1 11.6 73.1 11C66.6 9.7 58.6 10.1 50.2 12.3C47.6 12.9 46.8 13.4 46.8 14.1C46.8 15.3 48.3 18.8 50.5 22.2C54.5 28.8 59.6 33.3 66.1 36.3C67.5 36.9 67.8 37.1 67.7 37.5C67.6 38.1 66.2 38.7 65 38.8C64.7 38.8 63.7 39 62.9 39.4C62.1 39.8 60.9 40.2 60.4 40.4C57.6 41.3 53.6 43.6 48 47.4C45.7 49 38.5 56.1 37.3 57.8C37 58.4 36.3 59.2 35.9 59.7C34.5 61.5 32.1 65.2 30.6 68.1C30 69.3 29.1 71.1 28.6 72C26.8 75.5 24 85.4 23.2 91C22.7 95 23.1 108.6 23.8 112.1C24.7 116.9 24.7 116.5 23.3 117.5C20.6 119.4 15.2 125.3 13.4 128.4C8.5 136.6 6.5 142.9 6.5 149.8C6.5 154.2 7.5 156.7 9.8 158.4C11.4 159.7 12.6 160.1 14.6 160C19.7 160 26.5 154.8 30.2 148.3C32.1 144.9 32.7 143.5 33.1 142C33.9 139.1 34.5 138.6 35.4 140.1C37.1 143 45.6 152.3 49.9 155.9C51.6 157.3 54.4 159.3 55.9 160.1C56.4 160.4 57.7 161.2 58.6 161.8C59.6 162.3 61.2 163.3 62.3 163.8C63.4 164.3 64.3 164.9 64.4 165.1C64.5 165.5 64 167.3 62.8 170.8C62.3 171.9 61.8 173.6 61.5 174.5C61.2 175.4 60.9 176.6 60.7 177.1C60.5 177.7 60.2 178.6 60 179.2C59.8 179.9 59.1 181.7 58.2 183.4C55.9 188.2 55.6 190.4 57.1 192.8C57.8 193.8 60.5 195.8 61.5 196.1C61.9 196.2 62.5 196.3 62.9 196.4C66 197.5 66.7 197.6 69.9 197.6C77.8 197.6 81.7 194.6 83.5 187.1C83.7 186.4 83.9 185.8 84 185.6C84.1 185.5 84.7 183.7 85.2 181.6C85.9 179.6 86.8 176.5 87.3 174.9C87.8 173.3 88.2 171.8 88.2 171.6C88.2 171.4 88.7 171.2 89.6 171.2C91.8 170.9 105.4 170.8 105.7 170.9C106.1 171.2 106.6 172.2 106.9 173.6C107.2 175 107.7 176.2 108.2 177.5C108.4 178 108.8 179.1 109 179.9C109.2 180.7 109.9 182.5 110.4 183.9C110.9 185.2 111.5 187.1 111.8 187.9C112.8 191.1 116.2 195 118.9 196.3C121 197.2 123.8 197.4 127.4 196.9C130.1 196.5 134 195.4 134 195C134 194.9 134.5 194.4 135 193.8C135.6 193.3 136.5 192.2 137.1 191.5C138.1 190.1 138.1 190.1 138.1 188C138.1 186.2 138 185.6 137.2 183.8C136.4 181.8 134.9 177.6 133.5 173C133.2 172.1 132.6 170.1 132 168.5C131.5 166.9 131 165.4 131 165.1C131 164.6 132.8 163.2 134.5 162.5C136.6 161.7 143 157.1 147 153.7C151.8 149.5 157.6 143.2 159.2 140.4C159.6 139.7 160.2 138.9 160.5 138.6C161.1 138.1 161.8 138.3 161.8 138.9C161.8 139.6 163.4 143 164.6 144.9C167.8 149.8 171.7 153.2 177 155.4C178.9 156.2 179.4 156.3 181.4 156.3C184 156.4 185.6 155.7 187.3 153.9C189.7 151.4 190.4 144.7 188.9 139.8C188.7 139.1 188.4 138.1 188.2 137.5C186.9 132.8 179.9 122.8 174.9 118.5C173.7 117.5 172.4 116.3 172 115.9C171.1 115 171.1 115 172.2 108.5C173.6 99.7 172.9 84.5 170.7 76.9C170.5 75.9 170.1 74.5 169.9 73.8C169 70.7 168.2 68 167.5 66.4C166.7 64.7 166.6 64.4 166.1 63.4C165.9 63.1 165.7 62.7 165.7 62.5C165.4 61.8 162.5 56.4 161.7 55.1C158.7 50.3 152.8 44.3 147.8 41C144 38.4 142.1 37.5 138 36C135.3 35.1 134.2 34.8 131.9 34.2C131.3 34.1 128 33.9 124.4 33.8L117.9 33.7L114 34.5C111.9 34.9 109.7 35.4 109.1 35.6C108.6 35.8 107.5 36.1 106.6 36.4C105.8 36.6 104.7 37 104.1 37.3C102.7 37.9 101.4 37.9 101.6 37.3C103.5 31.3 107.5 24.5 112.3 19.3C116.3 15 116.3 15 116.4 13.6C116.6 11.8 116.2 10.5 114.8 9C113.8 7.9 113.3 7.5 112.2 7.2C111.5 6.9 110.7 6.8 110.6 6.8C110.5 6.8 110 6.9 109.5 7Z")
}

extension MascotRigState {
    /// Rig fitted to the sheet's Jumping pose (silhouette IoU 0.914 against the traced figure).
    static let sheetJumping = MascotRigState(expression: .happy, armLeft: 68.7, armRight: 86.7, legLeft: -9.8, legRight: 28.4, tilt: 5.2, lift: 24.6, squash: 0.09)
}

