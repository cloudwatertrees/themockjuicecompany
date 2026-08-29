import ImageIO
import UIKit

/// The single resolution path from a question image filename (e.g. `TS4035f.png`)
/// to pixels. Both stem images and answer-option images go through here, so
/// there is exactly one place where lookup can be right or wrong.
///
/// The images ship inside `mockjuice_images/`. Xcode's file-system synchronized
/// group may either flatten that folder into the bundle root or preserve it as
/// a directory, and the two cases need different `Bundle` lookups — a classic
/// cause of images silently failing to load. Rather than betting on one layout,
/// this tries both and records which one actually hit so the behaviour is
/// observable instead of guesswork.
nonisolated enum BundledImageResolver {
    static let imagesDirectory = "mockjuice_images"

    /// Where a filename was found, kept for diagnostics.
    nonisolated enum Location: Sendable {
        case subdirectory(URL)
        case bundleRoot(URL)

        var url: URL {
            switch self {
            case .subdirectory(let url), .bundleRoot(let url):
                return url
            }
        }
    }

    private static let lock = NSLock()
    nonisolated(unsafe) private static var urlCache: [String: Location?] = [:]
    /// Filenames already reported as broken, so one bad image logs once instead
    /// of on every redraw.
    nonisolated(unsafe) private static var reportedFailures: Set<String> = []

    private static let decodedCache: NSCache<NSString, UIImage> = {
        let cache = NSCache<NSString, UIImage>()
        cache.totalCostLimit = 48 * 1024 * 1024
        return cache
    }()

    // MARK: - Lookup

    /// Locates a bundled image, memoising both hits and misses.
    static func location(forImageNamed fileName: String) -> Location? {
        lock.lock()
        if let cached = urlCache[fileName] {
            lock.unlock()
            return cached
        }
        lock.unlock()

        let resolved = search(fileName: fileName)

        lock.lock()
        urlCache[fileName] = resolved
        let alreadyReported = resolved == nil && reportedFailures.contains(fileName)
        if resolved == nil { reportedFailures.insert(fileName) }
        lock.unlock()

        if resolved == nil && !alreadyReported {
            NSLog("[MJImage] MISS not in bundle: '\(fileName)' (searched \(imagesDirectory)/ and bundle root)")
        }
        return resolved
    }

    static func url(forImageNamed fileName: String) -> URL? {
        location(forImageNamed: fileName)?.url
    }

    private static func search(fileName: String) -> Location? {
        let name = (fileName as NSString).deletingPathExtension
        let ext = (fileName as NSString).pathExtension

        if !ext.isEmpty {
            // Preserved folder reference (blue folder) — needs the subdirectory.
            if let url = Bundle.main.url(forResource: name, withExtension: ext, subdirectory: imagesDirectory) {
                return .subdirectory(url)
            }
            // Flattened into the bundle root by the synchronized file group.
            if let url = Bundle.main.url(forResource: name, withExtension: ext) {
                return .bundleRoot(url)
            }
        }

        // Last resort: filenames containing dots that aren't extensions.
        if let url = Bundle.main.url(forResource: fileName, withExtension: nil, subdirectory: imagesDirectory) {
            return .subdirectory(url)
        }
        if let url = Bundle.main.url(forResource: fileName, withExtension: nil) {
            return .bundleRoot(url)
        }

        // Bundle lookup can be defeated by odd characters (spaces, '#'), so as a
        // final check hit the filesystem directly before declaring a miss.
        let direct = Bundle.main.bundleURL.appendingPathComponent(imagesDirectory).appendingPathComponent(fileName)
        if FileManager.default.fileExists(atPath: direct.path) {
            return .subdirectory(direct)
        }
        let directRoot = Bundle.main.bundleURL.appendingPathComponent(fileName)
        if FileManager.default.fileExists(atPath: directRoot.path) {
            return .bundleRoot(directRoot)
        }
        return nil
    }

    // MARK: - Decoding

    /// Decodes a bundled image, downsampled to `maxPixelSize` on its long edge.
    /// Several source files are 1500–2100px, far larger than they're ever drawn,
    /// so thumbnailing keeps memory sane while scrolling a 784-question bank.
    static func image(named fileName: String, maxPixelSize: Int) -> UIImage? {
        let key = "\(fileName)@\(maxPixelSize)" as NSString
        if let cached = decodedCache.object(forKey: key) { return cached }

        guard let location = location(forImageNamed: fileName) else { return nil }
        guard let image = decode(url: location.url, maxPixelSize: maxPixelSize) else {
            lock.lock()
            let alreadyReported = reportedFailures.contains(fileName)
            reportedFailures.insert(fileName)
            lock.unlock()
            if !alreadyReported {
                NSLog("[MJImage] DECODE FAILED: '\(fileName)' at \(location.url.path)")
            }
            return nil
        }

        let cost = Int(image.size.width * image.size.height * 4)
        decodedCache.setObject(image, forKey: key, cost: cost)
        return image
    }

    /// Synchronous cache peek, so a view that already has the image can show it
    /// in the same frame rather than flashing empty.
    static func cachedImage(named fileName: String, maxPixelSize: Int) -> UIImage? {
        decodedCache.object(forKey: "\(fileName)@\(maxPixelSize)" as NSString)
    }

    /// Loads off the main thread; disk I/O and JPEG decoding have no business
    /// blocking a scroll.
    static func loadImage(named fileName: String, maxPixelSize: Int) async -> UIImage? {
        if let cached = cachedImage(named: fileName, maxPixelSize: maxPixelSize) { return cached }
        return await Task.detached(priority: .userInitiated) {
            image(named: fileName, maxPixelSize: maxPixelSize)
        }.value
    }

    private static func decode(url: URL, maxPixelSize: Int) -> UIImage? {
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: maxPixelSize
        ]

        if let source = CGImageSourceCreateWithURL(url as CFURL, nil),
           let cgImage = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) {
            return UIImage(cgImage: cgImage)
        }

        // Some PNGs (16-bit, unusual color models) refuse to thumbnail; a plain
        // full decode still handles them.
        return UIImage(contentsOfFile: url.path)
    }

    // MARK: - Startup audit

    /// Resolves every image the question bank references and logs one summary.
    /// This is how image bundling is verified across all 784 questions rather
    /// than by tapping through the app hoping to spot a blank slot.
    ///
    /// `deepDecodeCheck` additionally decodes every file, which is far slower and
    /// so runs off the launch path.
    static func auditBundledImages(deepDecodeCheck: Bool = false) {
        logBundleLayout()

        let questions = TheoryQuestionBank.allQuestions
        var referenced: Set<String> = []
        var stemRefs = 0
        var optionRefs = 0

        for question in questions {
            if let stem = question.stemImageName {
                referenced.insert(stem)
                stemRefs += 1
            }
            for option in question.options where option.imageName != nil {
                referenced.insert(option.imageName ?? "")
                optionRefs += 1
            }
        }

        var viaSubdirectory = 0
        var viaBundleRoot = 0
        var missing: [String] = []

        for fileName in referenced.sorted() {
            switch location(forImageNamed: fileName) {
            case .subdirectory:
                viaSubdirectory += 1
            case .bundleRoot:
                viaBundleRoot += 1
            case nil:
                missing.append(fileName)
            }
        }

        NSLog("""
        [MJImageAudit] questions=\(questions.count) stemRefs=\(stemRefs) optionRefs=\(optionRefs) \
        uniqueFiles=\(referenced.count) resolved=\(viaSubdirectory + viaBundleRoot) \
        missing=\(missing.count) viaSubdirectory=\(viaSubdirectory) viaBundleRoot=\(viaBundleRoot)
        """)

        if !missing.isEmpty {
            NSLog("[MJImageAudit] missing sample: \(missing.prefix(12).joined(separator: ", "))")
        }

        guard deepDecodeCheck else { return }

        // Prove the bytes actually decode, not merely that a path exists.
        var decoded = 0
        var failed: [String] = []
        for fileName in referenced.sorted() {
            if image(named: fileName, maxPixelSize: 64) != nil {
                decoded += 1
            } else {
                failed.append(fileName)
            }
        }
        NSLog("[MJImageAudit] decodeCheck ok=\(decoded)/\(referenced.count) failed=\(failed.count)")
        if !failed.isEmpty {
            NSLog("[MJImageAudit] decode failures sample: \(failed.prefix(12).joined(separator: ", "))")
        }

        // Verification thumbnails were throwaway; don't keep them cached.
        decodedCache.removeAllObjects()
    }

    /// Logs what the bundle actually contains, which is the fastest way to tell
    /// a flattened layout from a preserved folder from "never copied at all".
    static func logBundleLayout() {
        let manager = FileManager.default
        let root = Bundle.main.bundleURL

        let rootEntries = (try? manager.contentsOfDirectory(atPath: root.path)) ?? []
        let rootImages = rootEntries.filter { $0.hasSuffix(".png") || $0.hasSuffix(".jpg") }

        let subURL = root.appendingPathComponent(imagesDirectory)
        let subEntries = (try? manager.contentsOfDirectory(atPath: subURL.path)) ?? []

        NSLog("""
        [MJImageAudit] bundle layout: root .png/.jpg=\(rootImages.count) \
        \(imagesDirectory)/ exists=\(manager.fileExists(atPath: subURL.path)) entries=\(subEntries.count) \
        questions.json present=\(Bundle.main.url(forResource: "questions", withExtension: "json") != nil)
        """)
    }
}
