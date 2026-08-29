import SwiftUI

/// Shown exactly once, the first time the learner taps into any of the 16
/// theory topics. The video clips for theory questions aren't bundled with
/// the app — they're fetched here, once, so they're ready when needed.
struct VideoDownloadIntroView: View {
    let onContinue: () -> Void
    let onNeutralExit: () -> Void

    @State private var isDownloading: Bool = false
    @State private var progressValue: Double = 0
    @State private var didFinish: Bool = false
    @State private var appeared: Bool = false
    @State private var showSkipConfirmation: Bool = false

    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer(minLength: 80)

                iconBadge
                    .padding(.bottom, 28)

                Text("video clips")
                    .font(.mjRounded(.caption, weight: .heavy))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
                    .padding(.bottom, 8)

                Text("Go offline with video practice.")
                    .font(.mjRounded(size: 30, weight: .black))
                    .tracking(-0.5)
                    .textCase(.lowercase)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(MJTheme.deepForest)
                    .padding(.horizontal, 28)
                    .padding(.bottom, 14)

                Text("Download 9 short video clips once to play them instantly, anywhere — no buffering, no data usage on repeat watches")
                    .font(.mjRounded(.subheadline, weight: .semibold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.6))
                    .lineSpacing(4)
                    .padding(.horizontal, 32)

                Spacer(minLength: 28)

                sizeCard
                    .padding(.horizontal, 24)

                Spacer(minLength: 24)

                actionArea
                    .padding(.horizontal, 24)
                    .padding(.bottom, 20)

                if !isDownloading && !didFinish {
                    Button {
                        showSkipConfirmation = true
                    } label: {
                        Text("skip for now, i'm on the go")
                            .font(.mjRounded(.footnote, weight: .bold))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.deepForest.opacity(0.45))
                    }
                    .buttonStyle(.plain)
                    .padding(.bottom, 30)
                }
            }
            .opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 16)
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.4)) {
                appeared = true
            }
        }
        .interactiveDismissDisabled(isDownloading)
        .overlay(alignment: .topLeading) {
            invisibleExitButton
        }
        .overlay {
            if showSkipConfirmation {
                skipConfirmationOverlay
                    .transition(.opacity)
            }
        }
    }

    private var invisibleExitButton: some View {
        Button {
            onNeutralExit()
        } label: {
            Rectangle()
                .fill(Color.clear)
                .contentShape(Rectangle())
                .frame(width: 80, height: 80)
        }
        .buttonStyle(.plain)
        .disabled(isDownloading)
    }

    @ViewBuilder
    private var skipConfirmationOverlay: some View {
        ZStack {
            MJTheme.deepForest.opacity(0.45)
                .ignoresSafeArea()
                .onTapGesture {
                    withAnimation(.easeOut(duration: 0.2)) {
                        showSkipConfirmation = false
                    }
                }

            VStack(spacing: 0) {
                Image(systemName: "wifi.slash")
                    .font(.system(size: 32, weight: .bold))
                    .foregroundStyle(MJTheme.cardinal)
                    .padding(.top, 32)
                    .padding(.bottom, 16)

                Text("skip the download?")
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.3)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                    .padding(.bottom, 12)

                Text("you won't be able to watch video clips in theory questions until you download them. you can always come back and download later.")
                    .font(.mjRounded(.subheadline, weight: .semibold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.6))
                    .lineSpacing(4)
                    .padding(.horizontal, 28)
                    .padding(.bottom, 28)

                VStack(spacing: 10) {
                    Button {
                        onContinue()
                    } label: {
                        Text("skip for now")
                            .font(.mjRounded(.headline, weight: .black))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.innocentWhite)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 16)
                            .background(
                                RoundedRectangle(cornerRadius: 16, style: .continuous)
                                    .fill(MJTheme.cardinal)
                            )
                    }
                    .buttonStyle(MJPressScaleButtonStyle())

                    Button {
                        withAnimation(.easeOut(duration: 0.2)) {
                            showSkipConfirmation = false
                        }
                    } label: {
                        Text("stay and download")
                            .font(.mjRounded(.subheadline, weight: .bold))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.cardinal)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 28)
            }
            .background(
                RoundedRectangle(cornerRadius: 28, style: .continuous)
                    .fill(MJTheme.innocentWhite)
                    .overlay(
                        RoundedRectangle(cornerRadius: 28, style: .continuous)
                            .stroke(MJTheme.deepForest.opacity(0.08), lineWidth: 1)
                    )
            )
            .frame(maxWidth: 340)
            .padding(.horizontal, 24)
        }
    }

    private var iconBadge: some View {
        ZStack {
            Circle()
                .fill(MJTheme.cardinal.opacity(0.14))
                .frame(width: 96, height: 96)

            Circle()
                .stroke(MJTheme.cardinal.opacity(0.4), lineWidth: 1.5)
                .frame(width: 96, height: 96)

            Image(systemName: "arrow.down.circle.fill")
                .font(.system(size: 40, weight: .bold))
                .foregroundStyle(MJTheme.cardinal)
        }
    }

    private var sizeCard: some View {
        HStack(spacing: 16) {
            statBlock(value: "\(VideoDownloadManager.allFileNames.count)", label: "clips")
            Divider().overlay(MJTheme.deepForest.opacity(0.12)).frame(height: 34)
            statBlock(value: "offline", label: "after that")
        }
        .padding(.vertical, 18)
        .frame(maxWidth: .infinity)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(MJTheme.spring.opacity(0.12))
                .overlay(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .stroke(MJTheme.deepForest.opacity(0.08), lineWidth: 1)
                )
        )
    }

    private func statBlock(value: String, label: String) -> some View {
        VStack(spacing: 2) {
            Text(value)
                .font(.mjRounded(.title3, weight: .black))
                .tracking(-0.3)
                .foregroundStyle(MJTheme.deepForest)
            Text(label)
                .font(.mjRounded(.caption2, weight: .bold))
                .tracking(-0.1)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.5))
        }
        .frame(maxWidth: .infinity)
    }

    @ViewBuilder
    private var actionArea: some View {
        if didFinish {
            VStack(spacing: 14) {
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(MJTheme.spring)
                    Text("clips are ready")
                        .font(.mjRounded(.subheadline, weight: .black))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)
                }

                continueButton(title: "let's go")
            }
        } else if isDownloading {
            VStack(spacing: 12) {
                progressBar
                Text("\(Int((progressValue * 100).rounded()))% — downloading")
                    .font(.mjRounded(.caption, weight: .bold))
                    .tracking(-0.2)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
            }
        } else {
            continueButton(title: "start download") {
                startDownload()
            }
        }
    }

    private var progressBar: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(MJTheme.locked.opacity(0.45))
                Capsule()
                    .fill(MJTheme.cardinal)
                    .frame(width: max(geo.size.width * min(max(progressValue, 0), 1), 12))
                    .animation(.easeOut(duration: 0.25), value: progressValue)
            }
        }
        .frame(height: 12)
    }

    private func continueButton(title: String, action: (() -> Void)? = nil) -> some View {
        Button {
            if let action {
                action()
            } else {
                onContinue()
            }
        } label: {
            Text(title)
                .font(.mjRounded(.headline, weight: .black))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.innocentWhite)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 18)
                .background(
                    RoundedRectangle(cornerRadius: 20, style: .continuous)
                        .fill(MJTheme.cardinal)
                )
                .shadow(color: MJTheme.cardinal.opacity(0.3), radius: 14, y: 6)
        }
        .buttonStyle(MJPressScaleButtonStyle())
    }

    private func startDownload() {
        isDownloading = true
        Task {
            await VideoDownloadManager.shared.downloadAll { fraction in
                progressValue = fraction
            }
            withAnimation(.spring(response: 0.4)) {
                isDownloading = false
                didFinish = true
            }
            try? await Task.sleep(for: .milliseconds(700))
            onContinue()
        }
    }
}
