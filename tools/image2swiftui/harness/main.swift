import SwiftUI
import AppKit
import UniformTypeIdentifiers

// usage: render <out.png> <width> <height> [scale]
// Renders ForestPathIllustration through SwiftUI's ImageRenderer and reports parse and draw time.
@MainActor func renderToFile() {
    let args = CommandLine.arguments
    let out = URL(fileURLWithPath: args[1])
    let w = Double(args[2])!, h = Double(args[3])!
    let scale = args.count > 4 ? Double(args[4])! : 1

    let t0 = Date()
    for id in ForestPathArt.LayerID.allCases { _ = ForestPathArt.shapes(of: id) }
    let parse = Date().timeIntervalSince(t0)

    let renderer = ImageRenderer(content: ForestPathIllustration().frame(width: w, height: h))
    renderer.scale = scale
    let t1 = Date()
    guard let image = renderer.cgImage else { fatalError("render failed") }
    let draw = Date().timeIntervalSince(t1)
    let srgb = CGColorSpace(name: CGColorSpace.sRGB)!
    let ctx = CGContext(data: nil, width: image.width, height: image.height, bitsPerComponent: 8,
                        bytesPerRow: 0, space: srgb, bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
    let dest = CGImageDestinationCreateWithURL(out as CFURL, UTType.png.identifier as CFString, 1, nil)!
    CGImageDestinationAddImage(dest, ctx.makeImage()!, nil)
    CGImageDestinationFinalize(dest)
    print(String(format: "wrote %dx%d  parse %.3fs  render %.3fs", image.width, image.height, parse, draw))
}

MainActor.assumeIsolated { renderToFile() }
