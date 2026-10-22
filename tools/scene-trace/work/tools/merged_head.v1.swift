import SwiftUI

/// The home-screen forest as one continuous vertical scroll of two traced screens (each 937×1678 in design space):
/// the top screen, then its downward continuation joined on a pixel row. Each screen is aspect-filled into a frame of
/// the same size, so both share one scale and horizontal crop, rasterised off the main thread at the display's native
/// resolution and cached only while it is on screen.
struct ForestPathIllustration: View {
    @Environment(\.displayScale) private var displayScale
    @State private var position = ScrollPosition(edge: .top)

    var body: some View {
        GeometryReader { geo in
            let layout = ForestPathArt.Layout(viewSize: geo.size, displayScale: displayScale)
            ScrollView(.vertical) {
                LazyVStack(spacing: 0) {
                    ForEach(ForestPathArt.Screen.allCases, id: \.self) { screen in
                        ForestPathScreen(screen: screen)
                            .frame(width: geo.size.width, height: layout.screenHeight)
                    }
                }
                .clipped()
            }
            .scrollIndicators(.hidden)
            .scrollPosition($position)
            .background {
                // Bounce colours: the art's own colours beyond each end.
                VStack(spacing: 0) {
                    Color(rgb: ForestPathArt.topBounce)
                    Color(rgb: ForestPathArt.bottomBounce)
                }
            }
            .onAppear { position.scrollTo(y: layout.restingOffset) }
            .onChange(of: layout) { position.scrollTo(y: layout.restingOffset) }
        }
        .ignoresSafeArea()
    }
}

/// One screen of the scroll: its raster when ready, its ground colour until then.
private struct ForestPathScreen: View {
    let screen: ForestPathArt.Screen
    @Environment(\.displayScale) private var displayScale
    @State private var raster: ForestPathArt.ScreenRaster?

    var body: some View {
        GeometryReader { geo in
            let key = ForestPathArt.ScreenRaster.Key(screen: screen, size: geo.size, scale: displayScale)
            Canvas { context, _ in
                guard let raster, raster.key == key else { return }
                context.draw(Image(decorative: raster.image, scale: raster.key.scale), at: .zero, anchor: .topLeading)
            }
            .background(Color(rgb: screen.ground))
            .task(id: key) {
                raster = await ForestPathArt.ScreenRaster.make(key)
            }
            .onDisappear {
                raster = nil
                ForestPathArt.ScreenRaster.evict(screen)
            }
        }
    }
}

/// Draws a subset of one screen's layers in their original positions, aspect-filled into the size it is given. Split a
/// screen into several of these to animate or restyle one element on its own, e.g.
/// `ForestPathLayers([.water]).offset(x: 20)` between the layers below and above it.
struct ForestPathLayers: View {
    let ids: [ForestPathArt.LayerID]
    let screen: ForestPathArt.Screen

    init(_ ids: [ForestPathArt.LayerID], screen: ForestPathArt.Screen = .top) {
        self.ids = ids
        self.screen = screen
    }

    var body: some View {
        Canvas { context, size in
            let scale = context.environment.displayScale
            guard let (image, origin) = ForestPathArt.image(of: ids, in: screen, size: size, scale: scale) else { return }
            context.draw(Image(decorative: image, scale: scale), at: origin, anchor: .topLeading)
        }
    }
}

nonisolated enum ForestPathArt {
    /// Design space of one screen.
    static let size = CGSize(width: 937, height: 1678)

    /// The screens of the scroll, top to bottom. The bottom screen's y = 0 is the top screen's bottom edge.
    enum Screen: CaseIterable, Hashable, Sendable {
        case top, bottom

        /// Mean colour of the screen's first ~200 u: shown while its raster is being made.
        var ground: RGB {
            switch self {
            case .top: return ForestPathArt.topGround
            case .bottom: return ForestPathArt.seamGround
            }
        }
    }

    /// Named layers, back to front (colour classes of the traced art).
    enum LayerID: CaseIterable, Hashable, Sendable {
        case @CASES@
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
    struct RGB: Sendable {
        var r, g, b: Float
    }

    /// Ground colours shown before a screen's raster is ready, and the colours beyond the scroll content.
@COLOURS@

    /// Sizes for the scroll. Each screen is the design space scaled by the aspect-fill rule for the view,
    /// `s = max(width / 937, height / 1678)`, with the height rounded up to whole pixels so the join falls on a pixel
    /// row (a no-op on phones, where `s = height / 1678`). Every screen gets the same frame, so `fillTransform` gives
    /// them the same scale and horizontal crop.
    struct Layout: Equatable {
        let screenHeight: CGFloat
        /// Scroll offset that shows the top screen's centred crop (0 on phones).
        let restingOffset: CGFloat

        init(viewSize: CGSize, displayScale: CGFloat) {
            let scale = max(viewSize.width / size.width, viewSize.height / size.height)
            screenHeight = (size.height * scale * displayScale).rounded(.up) / displayScale
            restingOffset = max(((screenHeight - viewSize.height) / 2 * displayScale).rounded() / displayScale, 0)
        }
    }

    static func shapes(of id: LayerID, in screen: Screen = .top) -> [Shape] {
        switch screen {
        case .top: return parsedTop[id] ?? []
        case .bottom: return parsedBottom[id] ?? []
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

    /// A whole screen rasterised for a view of `size` points at `scale`, and the cache of on-screen ones.
    struct ScreenRaster: Sendable {
        struct Key: Hashable, Sendable {
            let screen: Screen
            let size: CGSize
            let scale: CGFloat
        }

        let key: Key
        let image: CGImage

        @MainActor private static var cached: [Screen: ScreenRaster] = [:]

        @MainActor static func make(_ key: Key) async -> ScreenRaster? {
            if let hit = cached[key.screen], hit.key == key {
                return hit
            }
            let made = await Task.detached(priority: .userInitiated) {
                ForestPathArt.rasterize(key.screen, size: key.size, scale: key.scale).map { ScreenRaster(key: key, image: $0) }
            }.value
            if let made {
                cached[key.screen] = made
            }
            return made
        }

        /// Drops a screen's raster once it leaves the screen.
        @MainActor static func evict(_ screen: Screen) {
            cached[screen] = nil
        }
    }

    /// All layers of `screen` rasterised for a view of `size` points at `scale`, with the aspect-fill transform. A pure
    /// function of its arguments, safe to call off the main thread.
    static func rasterize(_ screen: Screen, size: CGSize, scale: CGFloat) -> CGImage? {
        let all = LayerID.allCases.flatMap { shapes(of: $0, in: screen) }
        let width = Int((size.width * scale).rounded(.up)), height = Int((size.height * scale).rounded(.up))
        guard width > 0, height > 0 else { return nil }
        let transform = fillTransform(for: size).concatenating(CGAffineTransform(scaleX: scale, y: scale))
        return ShapeRaster(width: width, height: height, shapes: all, transform: transform).image()
    }

    /// The layers rasterised for a view of `size` at `scale`, cropped to their pixel bounds, and the crop's top-left
    /// corner in view space. Cached per screen and layer subset, for its latest size.
    @MainActor static func image(of ids: [LayerID], in screen: Screen, size: CGSize, scale: CGFloat) -> (CGImage, CGPoint)? {
        let key = SubsetKey(screen: screen, ids: ids)
        if let raster = subsets[key], raster.size == size, raster.scale == scale {
            return raster.image
        }
        let image = rasterize(ids, in: screen, size: size, scale: scale)
        subsets[key] = (size, scale, image)
        return image
    }

    private struct SubsetKey: Hashable {
        let screen: Screen
        let ids: [LayerID]
    }

    @MainActor private static var subsets: [SubsetKey: (size: CGSize, scale: CGFloat, image: (CGImage, CGPoint)?)] = [:]

    /// SwiftUI's own path rendering (Canvas fills, clips and Core Graphics drawing alike) reverses the
    /// antialiasing along parts of some outlines in large scenes on iOS 18, depending on draw order, which
    /// shows as sawtooth edges. So coverage comes from a Core Graphics bitmap context instead, and the
    /// fills are composited here.
    private static func rasterize(_ ids: [LayerID], in screen: Screen, size: CGSize, scale: CGFloat) -> (CGImage, CGPoint)? {
        let shapes = ids.flatMap { Self.shapes(of: $0, in: screen) }
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

    /// Shapes per layer, parsed once per screen on first use.
    private static let parsedTop = parse(TopScreen.data(of:))
    private static let parsedBottom = parse(BottomScreen.data(of:))

    private static func parse(_ data: (LayerID) -> String) -> [LayerID: [Shape]] {
        Dictionary(uniqueKeysWithValues: LayerID.allCases.map { id in
            var text = data(id)
            let shapes = text.withUTF8 { bytes in
                var reader = ShapeDataReader(bytes)
                var shapes: [Shape] = []
                while let shape = reader.nextShape() {
                    shapes.append(shape)
                }
                return shapes
            }
            return (id, shapes)
        })
    }
}

private extension Color {
    init(rgb: ForestPathArt.RGB) {
        self.init(.sRGB, red: Double(rgb.r) / 255, green: Double(rgb.g) / 255, blue: Double(rgb.b) / 255)
    }
}

