import SwiftUI

/// The winding road, defined by a mathematical centreline in the `HomeSceneArt`
/// design space (1536×3072). The centreline runs from the far tip at the horizon
/// to beyond the bottom edge; the pale verge, the asphalt and the lane dashes are
/// all generated from it using width profiles along its arc length.
///
/// Use `point(at:)` or `point(atDistance:)` to place things on the road (e.g.
/// journey nodes), then map to view space with `HomeSceneArt.fillTransform(for:)`.
enum HomeSceneRoad {
    struct Dash {
        /// Arc-length span along the centreline.
        let start: CGFloat
        let end: CGFloat
        /// Lateral offset from the centreline at the dash midpoint (positive =
        /// towards the left verge), changing by `slope` per point of arc length.
        let offset: CGFloat
        let slope: CGFloat
        let halfWidth: CGFloat
    }

    /// Cubic Bézier chain: p0, c1, c2, p1, c1, c2, p2, …
    static let centreline: [CGPoint] = [
        CGPoint(x: 766.5, y: 1218.96),
        CGPoint(x: 788.41, y: 1229.57),
        CGPoint(x: 808.39, y: 1239.49),
        CGPoint(x: 827.93, y: 1254.29),
        CGPoint(x: 837.5, y: 1261.55),
        CGPoint(x: 846.4, y: 1269.66),
        CGPoint(x: 853.87, y: 1279.11),
        CGPoint(x: 864.64, y: 1292.72),
        CGPoint(x: 876.13, y: 1313.07),
        CGPoint(x: 874.02, y: 1331.03),
        CGPoint(x: 871.65, y: 1351.25),
        CGPoint(x: 849.53, y: 1373.22),
        CGPoint(x: 835.04, y: 1386.46),
        CGPoint(x: 811.91, y: 1407.59),
        CGPoint(x: 786.93, y: 1426.62),
        CGPoint(x: 763.07, y: 1446.91),
        CGPoint(x: 745.31, y: 1462.01),
        CGPoint(x: 727.86, y: 1477.66),
        CGPoint(x: 713.3, y: 1495.96),
        CGPoint(x: 700.46, y: 1512.12),
        CGPoint(x: 689.32, y: 1529.94),
        CGPoint(x: 683.43, y: 1549.85),
        CGPoint(x: 682.02, y: 1554.61),
        CGPoint(x: 680.7, y: 1559.54),
        CGPoint(x: 680.67, y: 1564.54),
        CGPoint(x: 680.64, y: 1570.59),
        CGPoint(x: 682.3, y: 1576.42),
        CGPoint(x: 684.38, y: 1582.05),
        CGPoint(x: 689.56, y: 1596.11),
        CGPoint(x: 698.21, y: 1608.79),
        CGPoint(x: 707.44, y: 1620.48),
        CGPoint(x: 725.39, y: 1643.22),
        CGPoint(x: 747.6, y: 1662.52),
        CGPoint(x: 770.57, y: 1680.02),
        CGPoint(x: 779.85, y: 1687.09),
        CGPoint(x: 789.37, y: 1693.84),
        CGPoint(x: 798.82, y: 1700.69),
        CGPoint(x: 817.71, y: 1714.39),
        CGPoint(x: 836.79, y: 1727.93),
        CGPoint(x: 852.86, y: 1744.98),
        CGPoint(x: 879.46, y: 1773.19),
        CGPoint(x: 902.97, y: 1812.85),
        CGPoint(x: 899.14, y: 1853),
        CGPoint(x: 895.99, y: 1886.11),
        CGPoint(x: 874.34, y: 1914.87),
        CGPoint(x: 851, y: 1937.13),
        CGPoint(x: 828, y: 1959.05),
        CGPoint(x: 801.62, y: 1976.7),
        CGPoint(x: 776.13, y: 1995.47),
        CGPoint(x: 753.85, y: 2011.87),
        CGPoint(x: 732.36, y: 2029.49),
        CGPoint(x: 714.09, y: 2050.36),
        CGPoint(x: 698.06, y: 2068.68),
        CGPoint(x: 682.59, y: 2091.83),
        CGPoint(x: 675.97, y: 2115.43),
        CGPoint(x: 674.52, y: 2120.57),
        CGPoint(x: 673.4, y: 2125.8),
        CGPoint(x: 673.36, y: 2131.17),
        CGPoint(x: 673.24, y: 2148.42),
        CGPoint(x: 683, y: 2168.81),
        CGPoint(x: 691.58, y: 2183.49),
        CGPoint(x: 712.61, y: 2219.43),
        CGPoint(x: 743.46, y: 2250.28),
        CGPoint(x: 774.43, y: 2277.72),
        CGPoint(x: 795.88, y: 2296.73),
        CGPoint(x: 817.81, y: 2315.24),
        CGPoint(x: 838.52, y: 2335.06),
        CGPoint(x: 877.06, y: 2371.96),
        CGPoint(x: 912.01, y: 2414.63),
        CGPoint(x: 932.81, y: 2464.19),
        CGPoint(x: 940.79, y: 2483.2),
        CGPoint(x: 947.09, y: 2503.15),
        CGPoint(x: 949.57, y: 2523.68),
        CGPoint(x: 950.65, y: 2532.62),
        CGPoint(x: 950.97, y: 2541.63),
        CGPoint(x: 950.28, y: 2550.62),
        CGPoint(x: 947.95, y: 2580.65),
        CGPoint(x: 935.14, y: 2609.97),
        CGPoint(x: 919.84, y: 2635.56),
        CGPoint(x: 885.88, y: 2692.37),
        CGPoint(x: 835.71, y: 2741.33),
        CGPoint(x: 785.47, y: 2783.84),
        CGPoint(x: 747.29, y: 2816.15),
        CGPoint(x: 707.38, y: 2846.29),
        CGPoint(x: 666.9, y: 2875.65),
        CGPoint(x: 643.69, y: 2892.48),
        CGPoint(x: 620.38, y: 2909.15),
        CGPoint(x: 596.94, y: 2925.67),
        CGPoint(x: 592.31, y: 2928.93),
        CGPoint(x: 587.61, y: 2932.09),
        CGPoint(x: 582.96, y: 2935.34),
        CGPoint(x: 577.23, y: 2939.35),
        CGPoint(x: 571.56, y: 2943.47),
        CGPoint(x: 565.81, y: 2947.45),
        CGPoint(x: 557.58, y: 2953.14),
        CGPoint(x: 549.32, y: 2958.77),
        CGPoint(x: 541.19, y: 2964.6),
        CGPoint(x: 493.82, y: 2998.63),
        CGPoint(x: 446.19, y: 3032.32),
        CGPoint(x: 398.68, y: 3066.16),
        CGPoint(x: 309.89, y: 3129.39),
        CGPoint(x: 221.11, y: 3192.62),
        CGPoint(x: 132.33, y: 3255.86)
    ]

    /// Width profiles, one value every `knotSpacing` points of arc length
    /// (Catmull-Rom interpolated).
    static let knotSpacing: CGFloat = 16
    /// Distance from the centreline to each asphalt edge.
    static let asphaltLeft: [CGFloat] = [
        0, 1.11, 5.55, 9.98, 14.26, 18.89, 24.04, 30.01, 37.22, 43.58, 45.05, 44.51,
        43.58, 41.82, 40.06, 38.73, 38.19, 37.98, 38.24, 38.83, 39.72, 40.92, 42.48, 44.5,
        47.2, 50.26, 54.05, 58.09, 62.02, 65.02, 66.1, 64.5, 61.36, 58.1, 54.76, 51.84,
        49.36, 47.36, 46.06, 45.27, 44.73, 44.57, 44.96, 45.64, 46.89, 48.97, 51.36, 54.23,
        57.53, 61.02, 64.14, 66.55, 68.29, 69, 69.05, 68.65, 67.59, 66.15, 64.61, 63.22,
        62.13, 61.38, 61.04, 60.96, 61.34, 62.25, 63.22, 64.57, 66.39, 68.62, 71.6, 75.06,
        79.03, 83.16, 87.31, 90.73, 92.59, 92.36, 90.66, 88.33, 85.65, 83.16, 80.77, 78.77,
        77.39, 76.12, 75.48, 74.99, 74.63, 74.59, 74.78, 75.14, 75.76, 76.57, 77.71, 79.09,
        80.87, 83.15, 85.82, 89.2, 93.19, 97.83, 102.55, 107.39, 112.76, 117.64, 121.33, 123.67,
        124.58, 124.69, 125.13, 125.6, 125.87, 126, 126, 126.01, 126.06, 126.02, 126.03, 126.15,
        126.35, 126.44, 126.65, 127.03, 127.23, 127.4, 127.7, 127.99, 128.22, 128.49, 128.89, 129.09,
        129.22, 129.45, 129.64, 129.93, 130.2, 130.37, 130.49, 130.63, 130.93, 131.27, 131.38, 131.5,
        131.73, 131.92, 132.14, 132.59, 132.91, 133.38, 133.97, 134.41, 134.82, 135.5, 135.92, 136.37,
        137.03, 137.63, 138.13, 138.61, 139.18, 139.79, 140.41, 141, 141.58, 142.06, 142.48, 143.17,
        143.79, 144.23, 144.6, 145.05, 145.5, 145.94, 146.39, 146.84, 147.29, 147.74, 147.8
    ]
    static let asphaltRight: [CGFloat] = [
        0, 1.15, 5.76, 10.37, 14.39, 19, 23.86, 29.29, 35.05, 40.57, 44.66, 45.34,
        43.57, 41.82, 40.15, 38.81, 37.99, 37.85, 38.16, 38.76, 39.69, 40.86, 42.35, 44.59,
        47.35, 50.8, 55.1, 59.79, 64.35, 67.76, 66.24, 65.81, 63.02, 59.11, 55.17, 52.04,
        49.5, 47.54, 46.1, 45.2, 44.76, 44.62, 44.96, 45.81, 47.19, 48.95, 51.23, 53.87,
        56.8, 60.02, 63.13, 65.85, 68.11, 69.22, 69.41, 68.76, 67.46, 66.08, 64.63, 63.28,
        62.28, 61.54, 61.28, 61.25, 61.54, 62.23, 63.18, 64.54, 66.49, 69.16, 72.73, 77.09,
        82.42, 88.07, 92.77, 95.33, 93.64, 93.24, 92.8, 90.13, 86.84, 83.78, 81.19, 79.19,
        77.44, 76.13, 75.29, 74.89, 74.6, 74.56, 74.76, 75.11, 75.76, 76.6, 77.67, 78.87,
        80.58, 82.65, 85.18, 88.17, 91.64, 95.43, 99.55, 103.9, 108.06, 112.11, 115.82, 119.17,
        121.64, 123.49, 124.88, 125.47, 125.89, 125.98, 126.23, 126.19, 126.24, 125.95, 125.98, 126.14,
        126.18, 126.34, 126.68, 126.9, 127.25, 127.46, 127.81, 128.05, 128.38, 128.65, 128.87, 129.09,
        129.45, 129.69, 129.89, 130.07, 130.26, 130.51, 130.73, 130.84, 130.92, 131.26, 131.5, 131.56,
        131.78, 131.91, 132.01, 131.99, 132, 132.02, 132.05, 132.09, 132.13, 132.18, 132.23, 132.28,
        132.33, 132.36, 132.4, 132.43, 132.47, 132.5, 132.54, 132.57, 132.61, 132.64, 132.68, 132.71,
        132.75, 132.78, 132.82, 132.85, 132.89, 132.92, 132.96, 132.99, 133.03, 133.06, 133.07
    ]
    /// Distance from the centreline to the outer edge of each pale verge.
    static let vergeLeft: [CGFloat] = [
        0, 4.95, 9.91, 14.86, 19.81, 25.16, 31.78, 38.04, 45.69, 52.03, 52.12, 50.94,
        50.28, 48.55, 46.44, 44.58, 43.99, 43.94, 44.2, 45.27, 46.14, 47.36, 49.09, 51.2,
        54.17, 57.55, 61.29, 65.47, 69.76, 73.1, 74.56, 72.89, 69.48, 65.94, 62.53, 59.35,
        56.71, 54.65, 53.13, 52.33, 52.03, 51.97, 52.32, 53.2, 55.01, 57.3, 59.92, 63.22,
        66.77, 70.33, 73.45, 75.75, 77.27, 77.65, 77.85, 77.46, 76.43, 75.04, 73.35, 71.7,
        70.5, 69.64, 69.18, 68.94, 69.44, 70.3, 71.46, 73.04, 74.88, 77.49, 80.32, 84.23,
        88.31, 92.73, 97.15, 101.36, 103.77, 103.63, 101.56, 98.99, 96.55, 93.97, 91.7, 89.58,
        88.06, 87.21, 86.18, 85.55, 85.37, 85.44, 85.56, 86.23, 87.07, 88.15, 89.53, 91.09,
        93.27, 96.06, 99.19, 103.16, 107.47, 112.3, 117.75, 123.25, 129.02, 133.88, 137.42, 139.42,
        139.55, 139.03, 139.31, 139.58, 139.78, 139.74, 139.61, 139.55, 139.54, 139.52, 139.45, 139.39,
        139.51, 139.66, 139.8, 139.91, 140.09, 140.45, 140.59, 140.84, 141.33, 141.78, 142.04, 142.33,
        142.56, 142.84, 143.23, 143.31, 143.58, 143.83, 144.28, 144.63, 144.96, 145.46, 145.96, 146.16,
        146.4, 146.54, 147, 147.7, 148.29, 148.72, 149.41, 150.23, 150.62, 151.04, 151.57, 152.21,
        152.8, 153.3, 153.94, 154.57, 155.04, 155.62, 156.23, 156.89, 157.39, 158.03, 158.6, 159.04,
        159.63, 160.27, 160.99, 161.56, 161.99, 162.54, 163.09, 163.64, 164.18, 164.73, 164.81
    ]
    static let vergeRight: [CGFloat] = [
        0, 4.48, 8.95, 13.43, 18.01, 23.22, 28.79, 34.89, 41.22, 46.98, 51.48, 51.58,
        50.2, 47.96, 46.17, 44.77, 43.74, 43.84, 44.33, 45.08, 45.98, 47.28, 48.96, 51.61,
        54.7, 58.36, 63.38, 68.44, 73.14, 76.37, 73.94, 73.94, 71.57, 67.5, 63.11, 59.63,
        57.16, 55.34, 53.79, 52.58, 51.86, 51.83, 52.3, 52.89, 54.62, 56.48, 58.9, 61.81,
        65.11, 68.19, 71.61, 74.46, 76.77, 78.12, 78.09, 77.56, 76.24, 74.38, 72.68, 71.26,
        70.15, 69.3, 69.22, 69.33, 69.46, 70.21, 71.56, 73.2, 75.75, 79.35, 83.9, 89.45,
        95.71, 101.92, 106.36, 108.07, 105.09, 104.6, 104.73, 102.22, 98.54, 94.9, 91.85, 89.52,
        87.71, 86.33, 85.2, 84.56, 84.3, 84.37, 84.46, 84.74, 85.32, 86.1, 87.02, 88.58,
        90.72, 92.87, 95.79, 99.05, 102.65, 106.75, 111.12, 115.71, 120.36, 124.53, 128.84, 132.32,
        135.55, 137.94, 139.06, 139.86, 140.64, 140.84, 140.93, 140.98, 141.17, 140.92, 141.05, 141.22,
        141.44, 141.64, 141.9, 142.31, 142.63, 142.93, 143.3, 143.84, 144.14, 144.39, 144.67, 144.85,
        145.09, 145.32, 145.56, 145.81, 146.07, 146.38, 146.65, 146.68, 146.85, 147.06, 147.33, 147.64,
        148.27, 148.81, 149.12, 149.39, 149.68, 149.98, 150.29, 150.61, 150.94, 151.27, 151.6, 151.93,
        152.25, 152.57, 152.88, 153.2, 153.51, 153.83, 154.14, 154.46, 154.77, 155.09, 155.4, 155.72,
        156.03, 156.35, 156.66, 156.98, 157.29, 157.61, 157.93, 158.24, 158.56, 158.87, 158.91
    ]

    static let dashes: [Dash] = [
        Dash(start: 46.49, end: 72.71, offset: -3.72, slope: 0.045, halfWidth: 1.26),
        Dash(start: 92.07, end: 111.5, offset: -0.53, slope: 0.089, halfWidth: 1.41),
        Dash(start: 135.05, end: 160.77, offset: 6.39, slope: 0.147, halfWidth: 2.04),
        Dash(start: 197.54, end: 233.27, offset: 0.38, slope: -0.093, halfWidth: 2.65),
        Dash(start: 273.56, end: 313.06, offset: -0.99, slope: -0.001, halfWidth: 2.84),
        Dash(start: 357.52, end: 396.32, offset: 0.55, slope: 0.058, halfWidth: 2.81),
        Dash(start: 432.81, end: 467.94, offset: -1.07, slope: -0.086, halfWidth: 2.87),
        Dash(start: 505.67, end: 541.28, offset: 3.95, slope: 0.094, halfWidth: 2.8),
        Dash(start: 582.16, end: 627.7, offset: 1.32, slope: -0.080, halfWidth: 2.99),
        Dash(start: 677.88, end: 726.45, offset: 1.56, slope: -0.005, halfWidth: 3.23),
        Dash(start: 774.99, end: 818.65, offset: 2.42, slope: 0.060, halfWidth: 3.28),
        Dash(start: 863.5, end: 909.78, offset: 5.43, slope: 0.013, halfWidth: 3.41),
        Dash(start: 956.08, end: 1001.77, offset: 3.76, slope: -0.017, halfWidth: 3.38),
        Dash(start: 1054.83, end: 1101.42, offset: 0.25, slope: 0.002, halfWidth: 3.56),
        Dash(start: 1148.28, end: 1194.43, offset: -1.22, slope: -0.086, halfWidth: 3.79),
        Dash(start: 1245.6, end: 1298.78, offset: -2.34, slope: 0.096, halfWidth: 3.89),
        Dash(start: 1360.58, end: 1423.91, offset: 0.33, slope: 0.006, halfWidth: 4.07),
        Dash(start: 1493.5, end: 1558.06, offset: 1.04, slope: -0.076, halfWidth: 4.29),
        Dash(start: 1622.73, end: 1679.37, offset: -4.04, slope: 0.037, halfWidth: 4.95),
        Dash(start: 1736, end: 1798.91, offset: 7.54, slope: 0.073, halfWidth: 5.1),
        Dash(start: 1866.99, end: 1941.92, offset: 14.35, slope: 0.035, halfWidth: 5.29),
        Dash(start: 2033.49, end: 2115.48, offset: 17.37, slope: 0.016, halfWidth: 5.47),
        Dash(start: 2215.24, end: 2305.14, offset: 10.78, slope: -0.054, halfWidth: 5.82),
        Dash(start: 2405.16, end: 2494.46, offset: -7.14, slope: -0.054, halfWidth: 5.99)
    ]

    static let asphalt = Color(hex: "535356")
    static let verge = Color(hex: "DAD4D0")
    static let marking = Color(hex: "FBF5EC")

    /// Centreline length in design points.
    static var length: CGFloat { table[table.count - 1].s }

    /// Point at `progress` (0 = far tip, 1 = end of the centreline below the frame).
    static func point(at progress: CGFloat) -> CGPoint {
        point(atDistance: progress * length)
    }

    static func point(atDistance s: CGFloat) -> CGPoint {
        frame(atDistance: s).point
    }

    static func draw(in context: inout GraphicsContext) {
        context.fill(vergePath, with: .color(verge))
        context.fill(asphaltPath, with: .color(asphalt))
        context.fill(dashPath, with: .color(marking))
    }

    // MARK: - Geometry

    private static let vergePath = ribbon(from: 0, to: length, step: 4) { s in
        (profile(vergeLeft, s), -profile(vergeRight, s))
    }

    private static let asphaltPath = ribbon(from: 0, to: length, step: 4) { s in
        (profile(asphaltLeft, s), -profile(asphaltRight, s))
    }

    private static let dashPath: Path = {
        var path = Path()
        for dash in dashes {
            let mid = (dash.start + dash.end) / 2
            path.addPath(ribbon(from: dash.start, to: dash.end, step: 2) { s in
                let centre = dash.offset + dash.slope * (s - mid)
                return (centre + dash.halfWidth, centre - dash.halfWidth)
            })
        }
        return path
    }()

    private struct Sample {
        let s: CGFloat
        let point: CGPoint
        let tangent: CGVector
    }

    /// Dense arc-length table, 64 samples per Bézier segment.
    private static let table: [Sample] = {
        var out: [Sample] = []
        var s: CGFloat = 0
        for i in stride(from: 0, to: centreline.count - 1, by: 3) {
            let p0 = centreline[i], p1 = centreline[i + 1], p2 = centreline[i + 2], p3 = centreline[i + 3]
            for k in (i == 0 ? 0 : 1)...64 {
                let t = CGFloat(k) / 64, mt = 1 - t
                let a = mt * mt * mt, b = 3 * mt * mt * t, c = 3 * mt * t * t, d = t * t * t
                let p = CGPoint(
                    x: a * p0.x + b * p1.x + c * p2.x + d * p3.x,
                    y: a * p0.y + b * p1.y + c * p2.y + d * p3.y
                )
                let dx = 3 * mt * mt * (p1.x - p0.x) + 6 * mt * t * (p2.x - p1.x) + 3 * t * t * (p3.x - p2.x)
                let dy = 3 * mt * mt * (p1.y - p0.y) + 6 * mt * t * (p2.y - p1.y) + 3 * t * t * (p3.y - p2.y)
                if let last = out.last {
                    s += hypot(p.x - last.point.x, p.y - last.point.y)
                }
                let len = max(hypot(dx, dy), .ulpOfOne)
                out.append(Sample(s: s, point: p, tangent: CGVector(dx: dx / len, dy: dy / len)))
            }
        }
        return out
    }()

    /// Position and unit normal (towards the left verge) at arc length `s`.
    private static func frame(atDistance s: CGFloat) -> (point: CGPoint, normal: CGVector) {
        let s = min(max(s, 0), length)
        var lo = 0, hi = table.count - 1
        while hi - lo > 1 {
            let mid = (lo + hi) / 2
            if table[mid].s <= s { lo = mid } else { hi = mid }
        }
        let a = table[lo], b = table[hi]
        let f = b.s > a.s ? (s - a.s) / (b.s - a.s) : 0
        let point = CGPoint(x: a.point.x + (b.point.x - a.point.x) * f, y: a.point.y + (b.point.y - a.point.y) * f)
        let tx = a.tangent.dx + (b.tangent.dx - a.tangent.dx) * f
        let ty = a.tangent.dy + (b.tangent.dy - a.tangent.dy) * f
        let len = max(hypot(tx, ty), .ulpOfOne)
        return (point, CGVector(dx: -ty / len, dy: tx / len))
    }

    /// Catmull-Rom interpolation of a width profile at arc length `s`.
    private static func profile(_ knots: [CGFloat], _ s: CGFloat) -> CGFloat {
        let u = min(max(s / knotSpacing, 0), CGFloat(knots.count - 1))
        let i = min(Int(u), knots.count - 2)
        let f = u - CGFloat(i)
        let p0 = knots[max(i - 1, 0)], p1 = knots[i], p2 = knots[i + 1], p3 = knots[min(i + 2, knots.count - 1)]
        return 0.5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (3 * p1 - p0 - 3 * p2 + p3) * f * f * f)
    }

    /// Band between two lateral offsets along the centreline, from arc length `a` to `b`.
    private static func ribbon(
        from a: CGFloat,
        to b: CGFloat,
        step: CGFloat,
        lateral: (CGFloat) -> (left: CGFloat, right: CGFloat)
    ) -> Path {
        let n = max(Int(((b - a) / step).rounded(.up)), 1)
        var left: [CGPoint] = [], right: [CGPoint] = []
        for k in 0...n {
            let s = a + (b - a) * CGFloat(k) / CGFloat(n)
            let (p, normal) = frame(atDistance: s)
            let (l, r) = lateral(s)
            left.append(CGPoint(x: p.x + normal.dx * l, y: p.y + normal.dy * l))
            right.append(CGPoint(x: p.x + normal.dx * r, y: p.y + normal.dy * r))
        }
        var path = Path()
        path.addLines(removingLoops(left) + removingLoops(right).reversed())
        path.closeSubpath()
        return path
    }

    /// Cuts out the small self-intersecting loops an offset curve forms on the
    /// inside of tight bends.
    private static func removingLoops(_ points: [CGPoint], window: Int = 160) -> [CGPoint] {
        guard points.count > 3 else { return points }
        var out: [CGPoint] = []
        var i = 0
        while i < points.count - 1 {
            out.append(points[i])
            var next = i + 1
            var j = min(i + window, points.count - 2)
            while j > i + 1 {
                if let x = intersection(points[i], points[i + 1], points[j], points[j + 1]) {
                    out.append(x)
                    next = j + 1
                    break
                }
                j -= 1
            }
            i = next
        }
        out.append(points[points.count - 1])
        return out
    }

    private static func intersection(_ a: CGPoint, _ b: CGPoint, _ c: CGPoint, _ d: CGPoint) -> CGPoint? {
        let r = CGVector(dx: b.x - a.x, dy: b.y - a.y), q = CGVector(dx: d.x - c.x, dy: d.y - c.y)
        let den = r.dx * q.dy - r.dy * q.dx
        guard abs(den) > 1e-9 else { return nil }
        let t = ((c.x - a.x) * q.dy - (c.y - a.y) * q.dx) / den
        let u = ((c.x - a.x) * r.dy - (c.y - a.y) * r.dx) / den
        guard (0...1).contains(t), (0...1).contains(u) else { return nil }
        return CGPoint(x: a.x + t * r.dx, y: a.y + t * r.dy)
    }
}
