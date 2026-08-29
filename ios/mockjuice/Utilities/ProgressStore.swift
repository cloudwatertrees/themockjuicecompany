import Foundation

/// On-device persistence for user progress. Writes a single JSON blob into
/// Application Support (not Caches — that can be purged by the OS, and progress
/// must survive relaunches).
///
/// Nothing here talks to a server: the app is fully local apart from first-time
/// video streaming.
nonisolated enum ProgressStore {
    private static let fileName = "mockjuice-progress.json"

    private static var fileURL: URL? {
        guard let directory = try? FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        ) else {
            NSLog("[ProgressStore] could not resolve Application Support directory")
            return nil
        }
        return directory.appendingPathComponent(fileName)
    }

    static func load() -> ProgressSnapshot {
        guard let fileURL, FileManager.default.fileExists(atPath: fileURL.path) else {
            return ProgressSnapshot()
        }

        do {
            let data = try Data(contentsOf: fileURL)
            return try JSONDecoder().decode(ProgressSnapshot.self, from: data)
        } catch {
            // A corrupt or schema-changed file shouldn't brick the app; start
            // clean but make the reason visible.
            NSLog("[ProgressStore] failed to load progress, starting fresh: \(error.localizedDescription)")
            return ProgressSnapshot()
        }
    }

    static func save(_ snapshot: ProgressSnapshot) {
        guard let fileURL else { return }

        do {
            let data = try JSONEncoder().encode(snapshot)
            try data.write(to: fileURL, options: .atomic)
        } catch {
            NSLog("[ProgressStore] failed to save progress: \(error.localizedDescription)")
        }
    }
}
