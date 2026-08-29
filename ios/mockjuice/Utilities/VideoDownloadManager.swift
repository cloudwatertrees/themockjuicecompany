import Foundation

/// Downloads the 9 hazard-perception clips on demand instead of shipping them
/// inside the app bundle — bundling all ~300MB made the initial App Store
/// download far too slow. Clips are fetched once, the first time the learner
/// opens the theory section, and cached in Documents so every later watch is
/// instant and fully offline.
actor VideoDownloadManager {
    static let shared = VideoDownloadManager()

    /// Bundled filename -> Cloudinary public id. The 27 video questions come
    /// in groups of 3 sharing one of these 9 clips.
    private static let remotePublicIDs: [String: String] = [
        "vm2016.mp4": "VM2016_Box_Junction_ztt4ez",
        "vm2040.mp4": "VM2040_Rural_Railway_3V_Final_1_r79o8j",
        "vm2044.mp4": "2044_MASTER_220218_1_v3bkq8",
        "vm2052.mp4": "2052_MASTER_280218_1_xr7c5l",
        "vm2053.mp4": "2053_MASTER_230218_1_aovlql",
        "vm2063.mp4": "2063_MASTER_240318_nkriiv",
        "vm2067.mp4": "2067_MASTER_040518_1_prsqob",
        "vm2070.mp4": "VM2070_Roundabout_Bus_Master_yfjnkd",
        "vm2071.mp4": "VM2071_Loomies_4V_wdhqcn",
    ]

    private static let cloudinaryBase = URL(string: "https://res.cloudinary.com/dwz16u7m/video/upload/")!

    /// All 9 unique bundled filenames, in a stable order for progress reporting.
    nonisolated static let allFileNames: [String] = Array(remotePublicIDs.keys).sorted()

    /// Roughly how much needs to be fetched in total, shown on the intro
    /// screen so there are no surprises.
    nonisolated static let approximateTotalMegabytes = 320

    private init() {}

    nonisolated func remoteURL(for fileName: String) -> URL? {
        guard let publicID = Self.remotePublicIDs[fileName] else { return nil }
        return Self.cloudinaryBase.appendingPathComponent(publicID + ".mp4")
    }

    nonisolated func localURL(for fileName: String) -> URL {
        Self.videosDirectory.appendingPathComponent(fileName)
    }

    nonisolated func isDownloaded(_ fileName: String) -> Bool {
        FileManager.default.fileExists(atPath: localURL(for: fileName).path)
    }

    nonisolated var allDownloaded: Bool {
        Self.allFileNames.allSatisfy { isDownloaded($0) }
    }

    private nonisolated static var videosDirectory: URL {
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let directory = documents.appendingPathComponent("HazardClips", isDirectory: true)
        if !FileManager.default.fileExists(atPath: directory.path) {
            try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        return directory
    }

    /// Downloads every clip that isn't already cached, reporting coarse
    /// (per-file) progress back to the caller. Already-cached files are
    /// skipped instantly, so a second run of this after a partial failure
    /// only fetches what's missing.
    func downloadAll(onProgress: @escaping @MainActor @Sendable (Double) -> Void) async {
        let names = Self.allFileNames
        let total = names.count
        await onProgress(0)

        for (index, fileName) in names.enumerated() {
            if !isDownloaded(fileName) {
                await downloadOne(fileName)
            }
            await onProgress(Double(index + 1) / Double(total))
        }
    }

    /// Fetches a single clip with byte-level progress reporting, used when a
    /// learner skipped the bulk download and hits a video question — the only
    /// way to unlock that clip is to explicitly download it from the locked
    /// placeholder.
    func downloadSingle(
        _ fileName: String,
        onProgress: @escaping @MainActor @Sendable (Double) -> Void
    ) async {
        guard !isDownloaded(fileName) else {
            await onProgress(1)
            return
        }
        guard let remoteURL = remoteURL(for: fileName) else {
            NSLog("[VideoDownloadManager] no remote source mapped for \(fileName)")
            return
        }

        do {
            let (asyncBytes, response) = try await URLSession.shared.bytes(from: remoteURL)
            let expectedLength = (response as? HTTPURLResponse)?.expectedContentLength ?? 0

            let destination = localURL(for: fileName)
            FileManager.default.createFile(atPath: destination.path, contents: nil)
            let handle = try FileHandle(forWritingTo: destination)

            var received: Int64 = 0
            for try await byte in asyncBytes {
                try handle.write(contentsOf: [byte])
                received += 1
                if expectedLength > 0 {
                    await onProgress(Double(received) / Double(expectedLength))
                }
            }
            try handle.close()

            await onProgress(1)
        } catch {
            NSLog("[VideoDownloadManager] failed to download \(fileName): \(error.localizedDescription)")
            // Clean up partial file so a retry starts fresh.
            try? FileManager.default.removeItem(at: localURL(for: fileName))
        }
    }

    private func downloadOne(_ fileName: String) async {
        guard let remoteURL = remoteURL(for: fileName) else {
            NSLog("[VideoDownloadManager] no remote source mapped for \(fileName)")
            return
        }

        do {
            let (tempURL, response) = try await URLSession.shared.download(from: remoteURL)
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                NSLog("[VideoDownloadManager] unexpected response downloading \(fileName)")
                return
            }

            let destination = localURL(for: fileName)
            try? FileManager.default.removeItem(at: destination)
            try FileManager.default.moveItem(at: tempURL, to: destination)
        } catch {
            NSLog("[VideoDownloadManager] failed to download \(fileName): \(error.localizedDescription)")
        }
    }
}
