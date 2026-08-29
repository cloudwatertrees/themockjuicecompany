import AVFoundation
import AVKit
import SwiftUI

/// Inline player for the 27 video questions.
///
/// Clips are downloaded once, up front, by `VideoDownloadIntroView` when the
/// learner first opens the theory section. If they skipped that download, the
/// clips are genuinely inaccessible here — no silent streaming fallback — and
/// the learner sees a locked placeholder with a button to grab just this one
/// clip. That's the only way in.
struct QuestionVideoPlayerView: View {
    /// Bundled filename, e.g. `vm2016.mp4`.
    let fileName: String

    @State private var player: AVPlayer?
    @State private var loopObserver: NSObjectProtocol?
    @State private var isDownloadingClip: Bool = false
    @State private var downloadProgress: Double = 0

    var body: some View {
        ZStack {
            if let player {
                FillingVideoPlayer(player: player)
                    .aspectRatio(16 / 9, contentMode: .fit)
                    .clipShape(.rect(cornerRadius: 16))
            } else if isDownloadingClip {
                downloadingState
            } else {
                lockedState
            }
        }
        .frame(maxWidth: .infinity)
        .task(id: fileName) {
            await prepareIfAvailable()
        }
        .onDisappear {
            cleanup()
        }
    }

    // MARK: - States

    private var lockedState: some View {
        RoundedRectangle(cornerRadius: 16, style: .continuous)
            .fill(MJTheme.deepForest.opacity(0.06))
            .aspectRatio(16 / 9, contentMode: .fit)
            .overlay {
                VStack(spacing: 10) {
                    Image(systemName: "lock.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(MJTheme.deepForest.opacity(0.3))

                    Text("clip not downloaded")
                        .font(.mjRounded(.caption, weight: .black))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.55))

                    Button {
                        downloadThisClip()
                    } label: {
                        Text("download clip")
                            .font(.mjRounded(.caption, weight: .black))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.innocentWhite)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(
                                Capsule().fill(MJTheme.cardinal)
                            )
                    }
                    .buttonStyle(MJPressScaleButtonStyle())
                }
            }
    }

    private var downloadingState: some View {
        RoundedRectangle(cornerRadius: 16, style: .continuous)
            .fill(MJTheme.deepForest.opacity(0.06))
            .aspectRatio(16 / 9, contentMode: .fit)
            .overlay {
                VStack(spacing: 8) {
                    ProgressView()
                        .tint(MJTheme.cardinal)
                    Text("\(Int(downloadProgress * 100))%")
                        .font(.mjRounded(.caption2, weight: .black))
                        .foregroundStyle(MJTheme.deepForest.opacity(0.5))
                }
            }
    }

    // MARK: - Playback

    private func prepareIfAvailable() async {
        let manager = VideoDownloadManager.shared
        guard manager.isDownloaded(fileName) else { return }
        await startPlayback()
    }

    private func startPlayback() async {
        let manager = VideoDownloadManager.shared
        let localURL = manager.localURL(for: fileName)

        let newPlayer = AVPlayer(url: localURL)
        newPlayer.actionAtItemEnd = .none
        player = newPlayer

        if let item = newPlayer.currentItem {
            loopObserver = NotificationCenter.default.addObserver(
                forName: .AVPlayerItemDidPlayToEndTime,
                object: item,
                queue: .main
            ) { _ in
                newPlayer.seek(to: .zero)
                newPlayer.play()
            }
        }

        newPlayer.play()
    }

    private func downloadThisClip() {
        isDownloadingClip = true
        Task {
            let manager = VideoDownloadManager.shared
            await manager.downloadSingle(fileName) { fraction in
                downloadProgress = fraction
            }
            isDownloadingClip = false
            if manager.isDownloaded(fileName) {
                await startPlayback()
            }
        }
    }

    private func cleanup() {
        if let loopObserver {
            NotificationCenter.default.removeObserver(loopObserver)
            self.loopObserver = nil
        }
        player?.pause()
    }
}

/// SwiftUI's `VideoPlayer` hard-codes `AVPlayerViewController.videoGravity` to
/// `.resizeAspect`, which is exactly the letterboxing/pillarboxing this needs
/// to eliminate — there is no SwiftUI-level way to override it. Wrapping the
/// controller directly and setting `.resizeAspectFill` is the only fix: the
/// clip now scales to cover its frame and any overflow is cropped, instead of
/// shrinking to fit inside black bars. Native playback controls (play/pause,
/// scrubber) are preserved since this still is a real `AVPlayerViewController`.
private struct FillingVideoPlayer: UIViewControllerRepresentable {
    let player: AVPlayer

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.videoGravity = .resizeAspectFill
        controller.showsPlaybackControls = true
        return controller
    }

    func updateUIViewController(_ controller: AVPlayerViewController, context: Context) {
        controller.player = player
        controller.videoGravity = .resizeAspectFill
    }
}
