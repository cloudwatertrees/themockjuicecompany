import SwiftUI

/// One-time intro modal shown the first time a learner opens the theory
/// category. Explains what's here and how to revise effectively — the
/// filtering modes, flagging, and weakest-first ordering. After "don't show
/// again" it never returns (persisted via `hasSeenTheoryIntro`).
struct TheoryIntroView: View {
    let onContinue: () -> Void
    let onDontShowAgain: () -> Void

    @State private var appeared: Bool = false

    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 0) {
                    Spacer(minLength: 16)

                    iconBadge
                        .padding(.bottom, 20)

                    Text("welcome to the theory!")
                        .font(.mjRounded(size: 28, weight: .black))
                        .tracking(-0.5)
                        .textCase(.lowercase)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(MJTheme.deepForest)
                        .padding(.horizontal, 24)
                        .padding(.bottom, 14)

                    Text("784 real dvsa theory questions across 14 topics. here's how to get the most out of it.")
                        .font(.mjRounded(.subheadline, weight: .semibold))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.6))
                        .lineSpacing(4)
                        .padding(.horizontal, 28)
                        .padding(.bottom, 28)

                    VStack(spacing: 14) {
                        tipRow(
                            icon: "rectangle.stack.fill",
                            title: "all questions",
                            description: "work through every question in the bank, shuffled fresh each time."
                        )
                        tipRow(
                            icon: "eye.slash.fill",
                            title: "not seen yet",
                            description: "filter to only questions you've never answered — perfect for first passes."
                        )
                        tipRow(
                            icon: "flag.fill",
                            title: "flagged questions",
                            description: "tap the flag on any question you want to revisit. filter to just your flagged set anytime."
                        )
                        tipRow(
                            icon: "chart.bar.fill",
                            title: "weakest first",
                            description: "topics are sorted by your mastery score so the areas you're struggling with float to the top."
                        )
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 32)

                    VStack(spacing: 10) {
                        Button {
                            onContinue()
                        } label: {
                            Text("continue")
                                .font(.mjRounded(.headline, weight: .black))
                                .tracking(-0.2)
                                .textCase(.lowercase)
                                .foregroundStyle(MJTheme.innocentWhite)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 16)
                                .background(
                                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                                        .fill(MJTheme.cardinal)
                                )
                                .shadow(color: MJTheme.cardinal.opacity(0.3), radius: 10, y: 5)
                        }
                        .buttonStyle(MJPressScaleButtonStyle())

                        Button {
                            onDontShowAgain()
                        } label: {
                            Text("don't show again")
                                .font(.mjRounded(.footnote, weight: .bold))
                                .tracking(-0.2)
                                .textCase(.lowercase)
                                .foregroundStyle(MJTheme.deepForest.opacity(0.4))
                        }
                        .buttonStyle(.plain)
                    }
                    .padding(.horizontal, 24)
                    .padding(.bottom, 32)
                }
            }
        }
        .opacity(appeared ? 1 : 0)
        .offset(y: appeared ? 0 : 12)
        .onAppear {
            withAnimation(.easeOut(duration: 0.35)) {
                appeared = true
            }
        }
        .interactiveDismissDisabled()
    }

    private var iconBadge: some View {
        ZStack {
            Circle()
                .fill(MJTheme.spring.opacity(0.14))
                .frame(width: 84, height: 84)

            Circle()
                .stroke(MJTheme.spring.opacity(0.35), lineWidth: 1.5)
                .frame(width: 84, height: 84)

            Image("theory_icon_trial_bold")
                .resizable()
                .renderingMode(.template)
                .aspectRatio(contentMode: .fit)
                .frame(width: 52, height: 52)
                .foregroundStyle(MJTheme.deepForest)
        }
    }

    private func tipRow(icon: String, title: String, description: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(MJTheme.deepForest.opacity(0.08))
                    .frame(width: 38, height: 38)
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(MJTheme.deepForest)
            }

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.mjRounded(.subheadline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)

                Text(description)
                    .font(.mjRounded(.caption, weight: .semibold))
                    .tracking(-0.1)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
                    .lineSpacing(3)
            }
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
        )
    }
}
