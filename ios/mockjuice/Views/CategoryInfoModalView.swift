import SwiftUI

struct CategoryInfoModalView: View {
    let category: QuizCategory
    let onStart: () -> Void
    @Environment(\.dismiss) private var dismiss

    @State private var appeared: Bool = false
    @State private var tapCount: Int = 0

    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()
            atmosphere

            VStack(spacing: 0) {
                closeBar

                ScrollView(.vertical, showsIndicators: false) {
                    VStack(alignment: .leading, spacing: 24) {
                        header
                            .staggered(appeared, index: 0)

                        bodyText
                            .staggered(appeared, index: 1)

                        tipsSection
                            .staggered(appeared, index: 2)
                    }
                    .padding(.horizontal, 24)
                    .padding(.top, 16)
                    .padding(.bottom, 40)
                }

                startButton
                    .staggered(appeared, index: 3)
            }
        }
        .sensoryFeedback(.impact(weight: .heavy), trigger: tapCount)
        .task {
            withAnimation(.spring(response: 0.55, dampingFraction: 0.82)) {
                appeared = true
            }
        }
    }

    // MARK: - Background

    private var atmosphere: some View {
        GeometryReader { geometry in
            ZStack {
                Circle()
                    .fill(MJTheme.spring.opacity(0.1))
                    .frame(width: geometry.size.width * 1.2)
                    .blur(radius: 80)
                    .offset(x: -geometry.size.width * 0.3, y: -geometry.size.height * 0.3)

                Circle()
                    .fill(MJTheme.cardinal.opacity(0.07))
                    .frame(width: geometry.size.width * 1.0)
                    .blur(radius: 80)
                    .offset(x: geometry.size.width * 0.5, y: geometry.size.height * 0.4)
            }
            .allowsHitTesting(false)
        }
        .ignoresSafeArea()
    }

    // MARK: - Chrome

    private var closeBar: some View {
        HStack {
            Spacer()
            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(MJTheme.deepForest.opacity(0.6))
                    .frame(width: 44, height: 44)
                    .background(Circle().fill(MJTheme.innocentWhite))
                    .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 6, y: 3)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 20)
        .padding(.top, 16)
        .padding(.bottom, 8)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 16) {
            TheoryIconGlyph(iconAsset: category.iconAsset, size: 72)
                .foregroundStyle(MJTheme.deepForest) // Apply deepForest color directly to the icon
            
            Text(category.title)
                .font(.mjRounded(size: 34, weight: .black))
                .tracking(-0.6)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)
                .lineLimit(2)
                .minimumScaleFactor(0.8)
        }
    }

    private var bodyText: some View {
        Text(category.info.body)
            .font(.mjRounded(size: 18, weight: .semibold))
            .tracking(-0.2)
            .lineSpacing(4)
            .foregroundStyle(MJTheme.deepForest) // Use deepForest for body text
            .lineLimit(2) // Ensure max 2 lines
    }

    private var tipsSection: some View {
        Group {
            if category.info.tips.count == 1 {
                tipCard(tip: category.info.tips[0])
            } else if category.info.tips.count == 2 {
                HStack(spacing: 16) {
                    tipCard(tip: category.info.tips[0])
                    tipCard(tip: category.info.tips[1])
                }
            }
        }
    }

    private func tipCard(tip: String) -> some View {
        Text(tip)
            .font(.mjRounded(size: 16, weight: .medium))
            .tracking(-0.1)
            .lineSpacing(2)
            .multilineTextAlignment(.center)
            .foregroundStyle(MJTheme.deepForest.opacity(0.75))
            .padding(16)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(MJTheme.innocentWhite)
                    .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 8, y: 4)
            )
    }

    private var startButton: some View {
        Button {
            tapCount += 1
            onStart()
        } label: {
            Text("got it")
                .font(.mjRounded(size: 20, weight: .black))
                .tracking(-0.3)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.innocentWhite)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
                .background(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .fill(MJTheme.deepForest)
                        .shadow(color: MJTheme.deepForest.opacity(0.3), radius: 12, y: 6)
                )
        }
        .buttonStyle(PressableScaleStyle())
        .padding(.horizontal, 24)
        .padding(.bottom, 32)
    }
}

private struct PressableScaleStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1)
            .animation(.spring(response: 0.3, dampingFraction: 0.7), value: configuration.isPressed)
    }
}

private extension View {
    func staggered(_ appeared: Bool, index: Int) -> some View {
        opacity(appeared ? 1 : 0)
            .offset(y: appeared ? 0 : 20)
            .animation(
                .spring(response: 0.5, dampingFraction: 0.82)
                    .delay(Double(index) * 0.06),
                value: appeared
            )
    }
}
