import CoreText
import Foundation
import UIKit

/// Registers the bundled VAG Rounded font file with the system at launch so
/// it becomes available to SwiftUI's `Font.custom` lookups.
///
/// We don't hardcode a guessed PostScript name — font files can carry
/// multiple name-table entries across platforms, and guessing wrong makes
/// the lookup silently fail with zero visible error (the app just falls
/// back to the system font). Instead we register the file then *discover*
/// the resolved PostScript name straight from the font descriptor.
enum FontRegistrar {
    private static let fontResourceName = "VAGRoundedBlack"
    private static let fontResourceExtension = "otf"

    private(set) static var resolvedFontName: String?

    static var isVAGRoundedAvailable: Bool { resolvedFontName != nil }

    /// Call once, as early as possible (app init), before any view renders.
    static func registerFonts() {
        guard let url = Bundle.main.url(forResource: fontResourceName, withExtension: fontResourceExtension) else {
            NSLog("[FontRegistrar] \(fontResourceName).\(fontResourceExtension) not found in app bundle")
            resolvedFontName = discoverRegisteredName()
            return
        }

        var error: Unmanaged<CFError>?
        let didRegister = CTFontManagerRegisterFontsForURL(url as CFURL, .process, &error)
        if !didRegister, let error {
            NSLog("[FontRegistrar] registration error: \(error.takeRetainedValue())")
        }

        // Read the PostScript name straight off the just-registered font
        // descriptor instead of guessing — this is authoritative regardless
        // of which name-table entry CoreText decided to surface.
        if let descriptors = CTFontManagerCreateFontDescriptorsFromURL(url as CFURL) as? [CTFontDescriptor],
           let descriptor = descriptors.first {
            let font = CTFontCreateWithFontDescriptor(descriptor, 12, nil)
            let postScriptName = CTFontCopyPostScriptName(font) as String
            resolvedFontName = UIFont(name: postScriptName, size: 12) != nil ? postScriptName : discoverRegisteredName()
        } else {
            resolvedFontName = discoverRegisteredName()
        }

        NSLog("[FontRegistrar] resolved name = \(resolvedFontName ?? "nil")")
    }

    /// Scans every registered font family for one that looks like our bundled
    /// VAG Rounded cut, and returns the first concrete PostScript name found.
    private static func discoverRegisteredName() -> String? {
        for family in UIFont.familyNames where family.replacingOccurrences(of: " ", with: "").lowercased().contains("vagrounded") {
            if let name = UIFont.fontNames(forFamilyName: family).first(where: { $0.lowercased().contains("black") }) {
                return name
            }
            if let name = UIFont.fontNames(forFamilyName: family).first {
                return name
            }
        }
        // Fall back to known literal candidates as a last resort.
        for candidate in ["VAGRoundedStd-Black", "VAG-Rounded-Black", "VAGRoundedBlack", "VAG Rounded Std Black"] {
            if UIFont(name: candidate, size: 12) != nil {
                return candidate
            }
        }
        return nil
    }
}
