import SwiftUI
import UIKit
import ImageIO
import UniformTypeIdentifiers

// Job file: one job per line.
//   full W H SCALE OUT            ForestPathIllustration() at W x H pt, opaque
//   layers W H SCALE OUTPREFIX    each layer alone (ForestPathLayers), transparent
//   split W H SCALE OUT           the scene as one ForestPathLayers view per layer, stacked in a ZStack
//   timing W H SCALE N            N renders, prints ms per render
//   cold W H SCALE X              parse time, first (rasterising) render, second render
@main
struct RenderHostApp: App {
    init() {
        if let job = ProcessInfo.processInfo.environment["RENDER_JOB"] {
            Jobs.run(job)
            exit(0)
        }
    }
    var body: some Scene { WindowGroup { ForestPathIllustration().ignoresSafeArea() } }
}

@MainActor
enum Jobs {
    static func run(_ path: String) {
        let text = (try? String(contentsOfFile: path, encoding: .utf8)) ?? ""
        for line in text.split(separator: "\n") {
            let f = line.split(separator: " ").map(String.init)
            guard f.count >= 5 else { continue }
            let w = CGFloat(Double(f[1])!), h = CGFloat(Double(f[2])!), s = CGFloat(Double(f[3])!)
            switch f[0] {
            case "full":
                write(render(ForestPathIllustration().frame(width: w, height: h), scale: s, opaque: true), f[4])
            case "layers":
                for id in ForestPathArt.LayerID.allCases {
                    write(render(ForestPathLayers([id]).frame(width: w, height: h), scale: s, opaque: false), f[4] + "_\(id).png")
                }
            case "split":
                let view = ZStack {
                    ForEach(Array(ForestPathArt.LayerID.allCases.enumerated()), id: \.offset) { _, id in
                        ForestPathLayers([id])
                    }
                }.frame(width: w, height: h)
                write(render(view, scale: s, opaque: true), f[4])
            case "subset":
                // subset W H SCALE OUT ids : one ForestPathLayers view with the listed layers, transparent
                let ids = f[5].split(separator: ",").compactMap { name in ForestPathArt.LayerID.allCases.first { "\($0)" == name } }
                write(render(ForestPathLayers(ids).frame(width: w, height: h), scale: s, opaque: false), f[4])
            case "parse":
                // cold parse: first access builds every layer's paths and mesh bitmaps
                let t0 = CFAbsoluteTimeGetCurrent()
                var count = 0
                for id in ForestPathArt.LayerID.allCases { count += ForestPathArt.shapes(of: id).count }
                print(String(format: "timing parse %.1f ms (%d shapes)", (CFAbsoluteTimeGetCurrent() - t0) * 1000, count))
            case "cold":
                // first render of a fresh process: parse, then rasterise + draw
                let t0 = CFAbsoluteTimeGetCurrent()
                for id in ForestPathArt.LayerID.allCases { _ = ForestPathArt.shapes(of: id) }
                let t1 = CFAbsoluteTimeGetCurrent()
                _ = ForestPathArt.image(of: ForestPathArt.LayerID.allCases, size: CGSize(width: w, height: h), scale: s)
                let tr = CFAbsoluteTimeGetCurrent()
                print(String(format: "timing raster %.1f ms", (tr - t1) * 1000))
                _ = render(ForestPathIllustration().frame(width: w, height: h), scale: s, opaque: true)
                let t2 = CFAbsoluteTimeGetCurrent()
                _ = render(ForestPathIllustration().frame(width: w, height: h), scale: s, opaque: true)
                let t3 = CFAbsoluteTimeGetCurrent()
                print(String(format: "timing cold parse %.1f ms, first render %.1f ms, second %.2f ms", (t1 - t0) * 1000, (t2 - t1) * 1000, (t3 - t2) * 1000))
            case "timing":
                let n = Int(f[4])!
                _ = render(ForestPathIllustration().frame(width: w, height: h), scale: s, opaque: true)
                let t0 = CFAbsoluteTimeGetCurrent()
                for _ in 0..<n { _ = render(ForestPathIllustration().frame(width: w, height: h), scale: s, opaque: true) }
                print(String(format: "timing %.2f ms/render", (CFAbsoluteTimeGetCurrent() - t0) * 1000 / Double(n)))
            default: break
            }
        }
        print("done")
    }

    static func render<V: View>(_ view: V, scale: CGFloat, opaque: Bool) -> CGImage {
        let r = ImageRenderer(content: view)
        r.scale = scale
        r.isOpaque = opaque
        return r.cgImage!
    }

    static func write(_ image: CGImage, _ path: String) {
        let url = URL(fileURLWithPath: path) as CFURL
        let dest = CGImageDestinationCreateWithURL(url, UTType.png.identifier as CFString, 1, nil)!
        CGImageDestinationAddImage(dest, image, nil)
        CGImageDestinationFinalize(dest)
        print("wrote \(path) \(image.width)x\(image.height)")
    }
}
