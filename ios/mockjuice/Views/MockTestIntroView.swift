import SwiftUI

struct MockTestIntroView: View {
    @Bindable var progress: UserProgress
    let onStart: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("mock test")
                        .font(.mjRounded(.largeTitle, weight: .black))
                        .tracking(-0.5)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)

                    Text("50 mixed questions • 57 minutes")
                        .font(.mjRounded(.subheadline, weight: .bold))
                        .tracking(-0.2)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.55))
                }

                Spacer()

                AppLogoView(width: 54, height: 54)
            }

            VStack(alignment: .leading, spacing: 12) {
                introRow(icon: "timer", title: "timed exam", detail: "the clock runs for 57 minutes once you begin")
                introRow(icon: "chart.bar.fill", title: "weighted mix", detail: "questions are pulled proportionally from all theory topics")
                introRow(icon: "checkmark.seal.fill", title: "pass mark", detail: "you need 43 out of 50 to pass")
                introRow(icon: "text.book.closed.fill", title: "review later", detail: "explanations appear after you submit the test")
            }

            Button {
                onStart()
            } label: {
                Text("start mock test")
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.innocentWhite)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .fill(MJTheme.cardinal)
                    )
                    .shadow(color: MJTheme.cardinal.opacity(0.3), radius: 12, y: 6)
            }
            .buttonStyle(.plain)
            .sensoryFeedback(.impact(weight: .heavy), trigger: progress.mockTestHistory.count)
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 8, y: 4)
        )
    }

    private func introRow(icon: String, title: String, detail: String) -> some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(MJTheme.cardinal.opacity(0.12))
                    .frame(width: 40, height: 40)
                Image(systemName: icon)
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(MJTheme.cardinal)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.mjRounded(.subheadline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                Text(detail)
                    .font(.mjRounded(.caption, weight: .bold))
                    .tracking(-0.2)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
            }

            Spacer()
        }
    }
}
