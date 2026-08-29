import SwiftUI

/// The single source of truth for color across the app.
///
/// See `DESIGN.md` at the repo root for the canonical role of each token.
/// Never hardcode a color in a view file — add or reuse a token here instead.
enum MJTheme {
    // MARK: - Brand Palette

    /// Primary text color, used everywhere.
    static let deepForest = Color(hex: "182D09")
    /// Secondary background: input fields, selected states, subtle section grouping.
    static let spring = Color(hex: "7C9D45")
    /// Primary actions/links/CTAs: buttons, tappable text, active tab indicators.
    static let macaw = Color(hex: "1CB0F6")
    /// Highlights/rewards/badges only — streaks, achievement badges, notification
    /// dots. NEVER used for text.
    static let bee = Color(hex: "FFC800")
    /// Errors/destructive only: form validation, delete actions, failed states.
    static let cardinal = Color(hex: "C1121F")
    /// Primary background color, used everywhere as the default screen background.
    static let cartonCream = Color(hex: "F8F3E6")
    /// Secondary text color on non-cream surfaces (dark/colored backgrounds), and
    /// surface color for cards/sheets/elevated elements.
    static let innocentWhite = Color(hex: "FFFFFF")

    // MARK: - Derived Neutrals

    /// Forest-tinted neutral for locked/disabled affordances and progress-bar
    /// tracks. Kept opaque so callers can still apply their own `.opacity(_:)`
    /// without compounding alpha unexpectedly.
    static let locked = Color(hex: "C9CFC0")

    // MARK: - Illustration Colors
    //
    // These depict real-world objects (traffic lights, scenery, road signs) and
    // are deliberately exempt from the brand palette above. They are still named
    // tokens — never raw RGB in a view file.

    /// Traffic light lamps.
    static let trafficRed = Color(red: 226/255, green: 62/255, blue: 55/255)
    static let trafficAmber = Color(red: 240/255, green: 170/255, blue: 50/255)
    static let trafficGreen = Color(red: 86/255, green: 190/255, blue: 96/255)

    /// Roadside grass verges.
    static let grassLight = Color(red: 0.56, green: 0.76, blue: 0.41)
    static let grassDark = Color(red: 0.45, green: 0.68, blue: 0.33)

    /// Background hills.
    static let hillLight = Color(red: 0.5, green: 0.7, blue: 0.35)
    static let hillDark = Color(red: 0.42, green: 0.62, blue: 0.3)

    /// Trees along the path.
    static let treeFoliageDark = Color(red: 0.09, green: 0.18, blue: 0.04)
    static let treeFoliage = Color(red: 0.15, green: 0.35, blue: 0.1)
    static let treeTrunk = Color(red: 0.35, green: 0.22, blue: 0.1)

    /// Road surface and lane markings.
    static let roadAsphalt = Color(red: 60/255, green: 60/255, blue: 65/255)
    static let roadMarking = Color.white.opacity(0.9)

    /// Roadside traffic signs.
    static let signPost = Color(red: 0.55, green: 0.56, blue: 0.58)
    static let signFaceBlue = Color(red: 0.11, green: 0.38, blue: 0.72)
    static let signFaceWhite = Color(red: 0.97, green: 0.97, blue: 0.96)
}

extension Color {
    /// Builds a color from a 6-digit RRGGBB hex string. Falls back to black for
    /// malformed input rather than trapping, so a typo can never crash the app.
    init(hex: String) {
        let sanitized = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
        var value: UInt64 = 0
        guard sanitized.count == 6, Scanner(string: sanitized).scanHexInt64(&value) else {
            self = .black
            return
        }
        self.init(
            red: Double((value & 0xFF0000) >> 16) / 255,
            green: Double((value & 0x00FF00) >> 8) / 255,
            blue: Double(value & 0x0000FF) / 255
        )
    }
}

/// Per-category color identity for the journey path map. Each of the five major
/// categories gets its own hue so users can tell them apart at a glance.
extension JourneyNode {
    /// The node's dominant fill/badge color.
    var categoryColor: Color {
        switch self {
        case .theory: return MJTheme.spring
        case .highwayCode: return MJTheme.macaw
        case .roadSigns: return MJTheme.bee
        case .mockTest: return MJTheme.cardinal
        case .explore: return MJTheme.cartonCream
        }
    }

    /// Foreground color that reads correctly on top of `categoryColor`.
    var categoryForeground: Color {
        switch self {
        case .roadSigns, .explore: return MJTheme.deepForest
        case .theory, .highwayCode, .mockTest: return MJTheme.innocentWhite
        }
    }
}

struct MJFont: ViewModifier {
    let style: Font.TextStyle
    let weight: Font.Weight

    func body(content: Content) -> some View {
        content
            .font(.mjRounded(style, weight: weight))
            .tracking(-0.2)
    }
}

extension Font {
    /// The app's signature rounded typeface: VAG Rounded when the bundled
    /// font registers successfully, falling back to SF Rounded otherwise so
    /// the app never breaks if the font is ever removed. VAG Rounded only
    /// ships one cut (Bold) in this project, so every weight resolves to
    /// that single bold face — which matches the app's "always heavy/black"
    /// type spec anyway.
    static func mjRounded(_ style: Font.TextStyle, weight: Font.Weight = .black) -> Font {
        guard let name = FontRegistrar.resolvedFontName else {
            return .system(style, design: .rounded, weight: weight)
        }
        return .custom(name, size: style.mjBaseSize, relativeTo: style)
    }

    /// Fixed-size variant for one-off headers that specify a literal point
    /// size instead of a semantic text style.
    static func mjRounded(size: CGFloat, weight: Font.Weight = .black) -> Font {
        guard let name = FontRegistrar.resolvedFontName else {
            return .system(size: size, weight: weight, design: .rounded)
        }
        return .custom(name, fixedSize: size)
    }
}

private extension Font.TextStyle {
    /// Apple's default point sizes per text style, used as the base size fed
    /// into `Font.custom(_:size:relativeTo:)` so Dynamic Type scaling still
    /// works correctly with the custom font.
    var mjBaseSize: CGFloat {
        switch self {
        case .largeTitle: return 34
        case .title: return 28
        case .title2: return 22
        case .title3: return 20
        case .headline: return 17
        case .body: return 17
        case .callout: return 16
        case .subheadline: return 15
        case .footnote: return 13
        case .caption: return 12
        case .caption2: return 11
        default: return 17
        }
    }
}

extension View {
    func mjFont(_ style: Font.TextStyle = .body, weight: Font.Weight = .black) -> some View {
        modifier(MJFont(style: style, weight: weight))
    }
}
