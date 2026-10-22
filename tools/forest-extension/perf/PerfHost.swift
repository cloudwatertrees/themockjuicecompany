import SwiftUI
import Darwin

// Simulator timing host: parse and raster times for the live art and the extension at one phone size, plus memory
// footprint. Output goes to stdout (simctl launch --console-pty).
@main
struct PerfHostApp: App {
    init() {
        Perf.run()
        exit(0)
    }
    var body: some Scene { WindowGroup { Color.clear } }
}

enum Perf {
    static func footprintMB() -> Double {
        var info = task_vm_info_data_t()
        var count = mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size / MemoryLayout<natural_t>.size)
        let kr = withUnsafeMutablePointer(to: &info) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) { task_info(mach_task_self_, task_flavor_t(TASK_VM_INFO), $0, &count) }
        }
        return kr == KERN_SUCCESS ? Double(info.phys_footprint) / 1_048_576 : -1
    }

    static func ms(_ t0: CFAbsoluteTime) -> String { String(format: "%.1f ms", (CFAbsoluteTimeGetCurrent() - t0) * 1000) }

    @MainActor static func run() {
        let size = CGSize(width: 402, height: (1678 * 874.0 / 1678 * 3).rounded(.up) / 3), scale: CGFloat = 3
        print(String(format: "perf start footprint %.1f MB", footprintMB()))
        var t = CFAbsoluteTimeGetCurrent()
        var n = 0
        for id in ForestPathArt.LayerID.allCases { n += ForestPathArt.shapes(of: id).count }
        print("perf live parse \(ms(t)) (\(n) shapes)")
        t = CFAbsoluteTimeGetCurrent()
        n = 0
        for id in ForestPathArt.LayerID.allCases { n += ForestPathExtensionArt.shapes(of: id).count }
        print("perf ext parse \(ms(t)) (\(n) shapes)")
        t = CFAbsoluteTimeGetCurrent()
        let live = ForestPathArt.image(of: ForestPathArt.LayerID.allCases, size: size, scale: scale)
        print("perf live raster 402x874@3 \(ms(t)) \(live.map { "\($0.0.width)x\($0.0.height)" } ?? "nil")")
        t = CFAbsoluteTimeGetCurrent()
        let ext = ForestPathExtensionArt.rasterize(size: size, scale: scale)
        print("perf ext raster 402x874@3 \(ms(t)) \(ext.map { "\($0.width)x\($0.height)" } ?? "nil")")
        print(String(format: "perf end footprint %.1f MB (both rasters held)", footprintMB()))
        print("perf done")
    }
}
