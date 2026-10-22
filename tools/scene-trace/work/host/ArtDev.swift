import SwiftUI

/// Vector forest path scene, traced from the 937×1678 reference artwork, aspect-filled
/// into whatever size it is given and rasterised at the display's native resolution.
struct ForestPathIllustration: View {
    var body: some View {
        ForestPathLayers(ForestPathArt.LayerID.allCases)
    }
}

/// Draws a subset of the scene's layers in their original positions. Split the
/// scene into several of these to animate or restyle one element on its own, e.g.
/// `ForestPathLayers([.water]).offset(x: 20)` between the layers below and above it.
struct ForestPathLayers: View {
    let ids: [ForestPathArt.LayerID]

    init(_ ids: [ForestPathArt.LayerID]) {
        self.ids = ids
    }

    var body: some View {
        Canvas { context, size in
            let scale = context.environment.displayScale
            guard let (image, origin) = ForestPathArt.image(of: ids, size: size, scale: scale) else { return }
            context.draw(Image(decorative: image, scale: scale), at: origin, anchor: .topLeading)
        }
    }
}

enum ForestPathArt {
    static let size = CGSize(width: 937, height: 1678)

    /// Named layers, back to front.
    enum LayerID: CaseIterable {
        case meadow, pathEdges, path, water, rocks, wood, foliage, conifers, accents, flowers
    }

    /// One filled shape (even-odd) in design space.
    struct Shape {
        let fill: Fill
        let path: Path
    }

    /// Shape colours.
    enum Fill {
        case color(RGB)
        /// Two-stop gradient from `start` to `end`, padded beyond them.
        case linearGradient(RGB, RGB, start: CGPoint, end: CGPoint)
        /// `width` × `height` vertex colours, row by row from the top left, evenly spanning `rect`
        /// (the path's bounding rect grown by one unit) and interpolated bilinearly.
        case mesh(width: Int, height: Int, colors: [RGB], rect: CGRect)
    }

    /// An sRGB colour with components in 0...255.
    struct RGB {
        var r, g, b: Float
    }

    static func shapes(of id: LayerID) -> [Shape] {
        parsed[id] ?? []
    }

    /// The layers rasterised for a view of `size` at `scale`, cropped to their pixel bounds, and the
    /// crop's top-left corner in view space. Cached per layer subset, for its latest size.
    static func image(of ids: [LayerID], size: CGSize, scale: CGFloat) -> (CGImage, CGPoint)? {
        if let raster = rasters[ids], raster.size == size, raster.scale == scale {
            return raster.image
        }
        let image = rasterize(ids, size: size, scale: scale)
        rasters[ids] = (size, scale, image)
        return image
    }

    private static var rasters: [[LayerID]: (size: CGSize, scale: CGFloat, image: (CGImage, CGPoint)?)] = [:]

    /// SwiftUI's own path rendering (Canvas fills, clips and Core Graphics drawing alike) reverses the
    /// antialiasing along parts of some outlines in large scenes on iOS 18, depending on draw order, which
    /// shows as sawtooth edges. So coverage comes from a Core Graphics bitmap context instead, and the
    /// fills are composited here.
    private static func rasterize(_ ids: [LayerID], size: CGSize, scale: CGFloat) -> (CGImage, CGPoint)? {
        let shapes = ids.flatMap { Self.shapes(of: $0) }
        let toPixels = fillTransform(for: size).concatenating(CGAffineTransform(scaleX: scale, y: scale))
        let viewPixels = CGRect(x: 0, y: 0, width: (size.width * scale).rounded(.up), height: (size.height * scale).rounded(.up))
        let bounds = shapes.reduce(CGRect.null) { $0.union($1.path.boundingRect) }
            .applying(toPixels).insetBy(dx: -1, dy: -1).integral.intersection(viewPixels)
        guard !bounds.isEmpty else { return nil }
        let toRaster = toPixels.concatenating(CGAffineTransform(translationX: -bounds.minX, y: -bounds.minY))
        let raster = ShapeRaster(width: Int(bounds.width), height: Int(bounds.height), shapes: shapes, transform: toRaster)
        guard let image = raster.image() else { return nil }
        return (image, CGPoint(x: bounds.minX / scale, y: bounds.minY / scale))
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

    /// Shapes per layer, parsed once on first use.
    private static let parsed: [LayerID: [Shape]] = Dictionary(uniqueKeysWithValues: LayerID.allCases.map { id in
        var data = data(of: id)
        let shapes = data.withUTF8 { bytes in
            var reader = ShapeDataReader(bytes)
            var shapes: [Shape] = []
            while let shape = reader.nextShape() {
                shapes.append(shape)
            }
            return shapes
        }
        return (id, shapes)
    })

    /// Raw data for a layer, one shape per line, back to front. Each line is
    /// `RRGGBB <path>` for a flat fill, `RRGGBB RRGGBB x0 y0 x1 y1 <path>` for a
    /// linear gradient from (x0, y0) to (x1, y1), or `*W H RRGGBB … <path>` for a
    /// W × H bilinear mesh gradient (colours row by row from the top left) spanning
    /// the path's bounding rect grown by one unit. `<path>` is SVG path data (M, L, C,
    /// Z and relative l, c) in design-space units.
    static func data(of id: LayerID) -> String {
        switch id {
        case .meadow: return meadow
        case .pathEdges: return pathEdges
        case .path: return path
        case .water: return water
        case .rocks: return rocks
        case .wood: return wood
        case .foliage: return foliage
        case .conifers: return conifers
        case .accents: return accents
        case .flowers: return flowers
        }
    }
}

/// Single-pass reader for `ForestPathArt` layer data.
struct ShapeDataReader {
    private let bytes: UnsafeBufferPointer<UInt8>
    private var index = 0

    init(_ bytes: UnsafeBufferPointer<UInt8>) {
        self.bytes = bytes
    }

    mutating func nextShape() -> ForestPathArt.Shape? {
        while index < bytes.count, bytes[index] == .space || bytes[index] == .newline {
            index += 1
        }
        guard index < bytes.count else { return nil }
        if bytes[index] == UInt8(ascii: "*") {
            index += 1
            let width = Int(number()), height = Int(number())
            var colors: [ForestPathArt.RGB] = []
            colors.reserveCapacity(width * height)
            for _ in 0..<width * height {
                skipSpaces()
                colors.append(color())
            }
            let path = path(acrossLines: false)
            let rect = path.boundingRect.insetBy(dx: -1, dy: -1)
            return ForestPathArt.Shape(fill: .mesh(width: width, height: height, colors: colors, rect: rect), path: path)
        }
        let from = color()
        skipSpaces()
        let fill: ForestPathArt.Fill
        if index < bytes.count, bytes[index] == UInt8(ascii: "M") {
            fill = .color(from)
        } else {
            let to = color()
            let start = point(), end = point()
            fill = .linearGradient(from, to, start: start, end: end)
        }
        return ForestPathArt.Shape(fill: fill, path: path(acrossLines: false))
    }

    /// Reads path commands up to the end of the line, or of the data if `acrossLines`.
    mutating func path(acrossLines: Bool) -> Path {
        var path = Path()
        var current = CGPoint.zero
        var subpathStart = CGPoint.zero
        while true {
            skipSpaces()
            if acrossLines {
                while index < bytes.count, bytes[index] == .newline || bytes[index] == .space {
                    index += 1
                }
            }
            guard index < bytes.count, bytes[index] != .newline else { return path }
            let command = bytes[index]
            index += 1
            switch command {
            case UInt8(ascii: "M"):
                current = point()
                subpathStart = current
                path.move(to: current)
            case UInt8(ascii: "L"), UInt8(ascii: "l"):
                current = point(from: command == UInt8(ascii: "l") ? current : .zero)
                path.addLine(to: current)
            case UInt8(ascii: "C"), UInt8(ascii: "c"):
                let origin = command == UInt8(ascii: "c") ? current : .zero
                let control1 = point(from: origin)
                let control2 = point(from: origin)
                current = point(from: origin)
                path.addCurve(to: current, control1: control1, control2: control2)
            case UInt8(ascii: "Z"):
                path.closeSubpath()
                current = subpathStart
            default:
                return path
            }
        }
    }

    private mutating func color() -> ForestPathArt.RGB {
        let value = rgb()
        return ForestPathArt.RGB(r: Float((value >> 16) & 0xFF), g: Float((value >> 8) & 0xFF), b: Float(value & 0xFF))
    }

    private mutating func rgb() -> Int {
        var value = 0
        for _ in 0..<6 where index < bytes.count {
            let byte = bytes[index]
            value = value << 4 | Int(byte >= UInt8(ascii: "A") ? byte - UInt8(ascii: "A") + 10 : byte - UInt8(ascii: "0"))
            index += 1
        }
        return value
    }

    private mutating func point(from origin: CGPoint = .zero) -> CGPoint {
        let x = number()
        return CGPoint(x: origin.x + x, y: origin.y + number())
    }

    private mutating func number() -> CGFloat {
        skipSpaces()
        var negative = false
        if index < bytes.count, bytes[index] == UInt8(ascii: "-") {
            negative = true
            index += 1
        }
        var value = 0.0
        while index < bytes.count, bytes[index] &- UInt8(ascii: "0") < 10 {
            value = value * 10 + Double(bytes[index] &- UInt8(ascii: "0"))
            index += 1
        }
        if index < bytes.count, bytes[index] == UInt8(ascii: ".") {
            index += 1
            var scale = 0.1
            while index < bytes.count, bytes[index] &- UInt8(ascii: "0") < 10 {
                value += Double(bytes[index] &- UInt8(ascii: "0")) * scale
                scale *= 0.1
                index += 1
            }
        }
        return CGFloat(negative ? -value : value)
    }

    private mutating func skipSpaces() {
        while index < bytes.count, bytes[index] == .space || bytes[index] == UInt8(ascii: ",") {
            index += 1
        }
    }
}

/// Source-over compositing of `ForestPathArt` shapes into premultiplied sRGB pixels, with exact-area
/// antialiased coverage from Core Graphics. Bands of rows are rendered in parallel.
nonisolated struct ShapeRaster {
    let width: Int
    let height: Int
    /// Fills, paths in pixel space, and their pixel bounds.
    private let shapes: [(fill: ForestPathArt.Fill, path: CGPath, box: CGRect)]
    /// Pixel centre (x + 0.5, y + 0.5) -> design space, per axis: `pixel * scale + offset`.
    private let scale: SIMD2<Float>
    private let offset: SIMD2<Float>

    /// `transform` maps design space into pixel space (a scale and translation).
    init(width: Int, height: Int, shapes: [ForestPathArt.Shape], transform: CGAffineTransform) {
        self.width = width
        self.height = height
        self.shapes = shapes.map { shape in
            let path = shape.path.applying(transform)
            return (shape.fill, path.cgPath, path.boundingRect.insetBy(dx: -1, dy: -1))
        }
        let toDesign = transform.inverted()
        scale = SIMD2(Float(toDesign.a), Float(toDesign.d))
        offset = SIMD2(Float(toDesign.tx), Float(toDesign.ty)) + scale / 2
    }

    func image() -> CGImage? {
        var pixels = [UInt8](repeating: 0, count: width * height * 4)
        let bands = 16, bandHeight = (height + bands - 1) / bands
        pixels.withUnsafeMutableBufferPointer { pixels in
            // Each band writes only its own rows.
            nonisolated(unsafe) let pixels = pixels.baseAddress!
            DispatchQueue.concurrentPerform(iterations: bands) { band in
                render(rows: band * bandHeight..<min((band + 1) * bandHeight, height), into: pixels)
            }
        }
        guard let provider = CGDataProvider(data: Data(pixels) as CFData) else { return nil }
        return CGImage(
            width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: width * 4,
            space: CGColorSpace(name: CGColorSpace.sRGB)!,
            bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.premultipliedLast.rawValue),
            provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent
        )
    }

    private func render(rows: Range<Int>, into pixels: UnsafeMutablePointer<UInt8>) {
        // One coverage byte per pixel of the band, row `rows.lowerBound` first.
        guard !rows.isEmpty, let coverage = CGContext(
            data: nil, width: width, height: rows.count, bitsPerComponent: 8, bytesPerRow: width,
            space: CGColorSpaceCreateDeviceGray(), bitmapInfo: CGImageAlphaInfo.none.rawValue
        ), let mask = coverage.data?.assumingMemoryBound(to: UInt8.self) else { return }
        coverage.translateBy(x: 0, y: CGFloat(rows.upperBound))
        coverage.scaleBy(x: 1, y: -1)
        coverage.setFillColor(gray: 1, alpha: 1)
        let row = UnsafeMutablePointer<Float>.allocate(capacity: width * 3)
        defer { row.deallocate() }
        for shape in shapes {
            let x0 = max(Int(shape.box.minX.rounded(.down)), 0), x1 = min(Int(shape.box.maxX.rounded(.up)), width)
            let y0 = max(Int(shape.box.minY.rounded(.down)), rows.lowerBound)
            let y1 = min(Int(shape.box.maxY.rounded(.up)), rows.upperBound)
            guard x0 < x1, y0 < y1 else { continue }
            for y in y0..<y1 {
                (mask + (y - rows.lowerBound) * width + x0).update(repeating: 0, count: x1 - x0)
            }
            coverage.addPath(shape.path)
            coverage.fillPath(using: .evenOdd)
            let shader = RowShader(shape.fill)
            defer { shader.deallocate() }
            for y in y0..<y1 {
                // Covered span of this row.
                let covered = mask + (y - rows.lowerBound) * width
                var first = x0, end = x1
                while first < end, covered[first] == 0 { first += 1 }
                while end > first, covered[end - 1] == 0 { end -= 1 }
                guard first < end else { continue }
                shader.colors(row, count: end - first, y: Float(y) * scale.y + offset.y, x: Float(first) * scale.x + offset.x, dx: scale.x)
                let out = pixels + y * width * 4
                var x = first
                while x < end {
                    let alpha = covered[x]
                    if alpha > 0 {
                        let pixel = out + x * 4, color = row + (x - first) * 3
                        if alpha == 255 {
                            pixel[0] = UInt8(color[0] + 0.5)
                            pixel[1] = UInt8(color[1] + 0.5)
                            pixel[2] = UInt8(color[2] + 0.5)
                            pixel[3] = 255
                        } else {
                            let a = Float(alpha) * (1 / 255), b = 1 - a
                            pixel[0] = UInt8(color[0] * a + Float(pixel[0]) * b + 0.5)
                            pixel[1] = UInt8(color[1] * a + Float(pixel[1]) * b + 0.5)
                            pixel[2] = UInt8(color[2] * a + Float(pixel[2]) * b + 0.5)
                            pixel[3] = UInt8(255 * a + Float(pixel[3]) * b + 0.5)
                        }
                    }
                    x += 1
                }
            }
        }
    }
}

/// Colours of one fill along pixel rows. (Plain loops and scalar arithmetic: generic SIMD, ranges and
/// `min`/`max` stay unspecialised in unoptimised builds and make them many times slower.)
nonisolated private struct RowShader {
    private let fill: ForestPathArt.Fill
    /// Mesh fills: the vertex colours interpolated down to the current row, three floats per vertex.
    private let verticalBlend: UnsafeMutablePointer<Float>?

    init(_ fill: ForestPathArt.Fill) {
        self.fill = fill
        if case .mesh(let width, _, _, _) = fill {
            verticalBlend = .allocate(capacity: width * 3)
        } else {
            verticalBlend = nil
        }
    }

    func deallocate() {
        verticalBlend?.deallocate()
    }

    /// Writes `count` colours (three floats each) for the pixel centres at design-space `x`, `x + dx`, …
    /// on row `y`.
    func colors(_ row: UnsafeMutablePointer<Float>, count: Int, y: Float, x: Float, dx: Float) {
        switch fill {
        case .color(let color):
            var i = 0
            while i < count {
                row[i * 3] = color.r
                row[i * 3 + 1] = color.g
                row[i * 3 + 2] = color.b
                i += 1
            }
        case .linearGradient(let from, let to, let start, let end):
            let axisX = Float(end.x - start.x), axisY = Float(end.y - start.y)
            let length = axisX * axisX + axisY * axisY
            let stepX = length > 0 ? axisX / length : 0, stepY = length > 0 ? axisY / length : 0
            let base = (x - Float(start.x)) * stepX + (y - Float(start.y)) * stepY
            var i = 0
            while i < count {
                let t = Self.clamp(base + Float(i) * dx * stepX, 1)
                row[i * 3] = from.r + (to.r - from.r) * t
                row[i * 3 + 1] = from.g + (to.g - from.g) * t
                row[i * 3 + 2] = from.b + (to.b - from.b) * t
                i += 1
            }
        case .mesh(let width, let height, let colors, let rect):
            guard let blend = verticalBlend else { return }
            let v = Self.clamp((y - Float(rect.minY)) / Float(rect.height), 1) * Float(height - 1)
            let j = Int(v) < height - 2 ? Int(v) : height - 2, fv = v - Float(j)
            let last = Float(width - 1)
            let u0 = (x - Float(rect.minX)) / Float(rect.width) * last, du = dx / Float(rect.width) * last
            let firstU = Int(Self.clamp(u0, last)), lastU = Int(Self.clamp(u0 + Float(count - 1) * du, last))
            colors.withUnsafeBufferPointer { colors in
                var k = firstU < width - 2 ? firstU : width - 2
                let kEnd = lastU < width - 2 ? lastU + 2 : width
                while k < kEnd {
                    let top = colors[j * width + k], bottom = colors[(j + 1) * width + k]
                    blend[k * 3] = top.r + (bottom.r - top.r) * fv
                    blend[k * 3 + 1] = top.g + (bottom.g - top.g) * fv
                    blend[k * 3 + 2] = top.b + (bottom.b - top.b) * fv
                    k += 1
                }
            }
            var i = 0
            while i < count {
                let u = Self.clamp(u0 + Float(i) * du, last)
                let k = Int(u) < width - 2 ? Int(u) : width - 2, f = u - Float(k)
                let left = blend + k * 3
                row[i * 3] = left[0] + (left[3] - left[0]) * f
                row[i * 3 + 1] = left[1] + (left[4] - left[1]) * f
                row[i * 3 + 2] = left[2] + (left[5] - left[2]) * f
                i += 1
            }
        }
    }

    /// `value` limited to 0...`upper`.
    private static func clamp(_ value: Float, _ upper: Float) -> Float {
        value < 0 ? 0 : value > upper ? upper : value
    }
}

private extension UInt8 {
    static let space = UInt8(ascii: " ")
    static let newline = UInt8(ascii: "\n")
}

extension ForestPathArt {
    static let meadow: String = devLoad("meadow")
    static let pathEdges: String = devLoad("pathEdges")
    static let path: String = devLoad("path")
    static let water: String = devLoad("water")
    static let rocks: String = devLoad("rocks")
    static let wood: String = devLoad("wood")
    static let foliage: String = devLoad("foliage")
    static let conifers: String = devLoad("conifers")
    static let accents: String = devLoad("accents")
    static let flowers: String = devLoad("flowers")
}
func devLoad(_ name: String) -> String {
    let dir = ProcessInfo.processInfo.environment["ART_DATA_DIR"]!
    return try! String(contentsOfFile: dir + "/" + name + ".txt", encoding: .utf8)
}
