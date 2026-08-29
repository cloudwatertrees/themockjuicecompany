import SwiftUI

/// Press feedback used by the onboarding CTA and the floating tab bar:
/// instant dip to 0.97, quick spring back to 1.0.
struct MJPressScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1.0)
            .animation(
                configuration.isPressed ? nil : .spring(response: 0.25, dampingFraction: 0.55),
                value: configuration.isPressed
            )
    }
}

struct OnboardingView: View {
    let dismissAction: () -> Void

    /// Continuous page position (0...2). Driven directly by the drag so the
    /// mascot, road and text all move together instead of cutting between pages.
    @State private var pagePosition: CGFloat = 0
    @State private var dragStartPosition: CGFloat?
    @State private var entered: Bool = false

    /// Discrete page used only for the face/traffic-light swap. Kept separate
    /// from `pagePosition` and updated in its own untransacted step so the
    /// instant swap never rides along on (and cancels) the car's driving
    /// animation, which is the bug that made the whole transition feel sharp.
    @State private var displayedPage: Int = 0

    private static let pageCount: Int = 3
    private static let lastPage: CGFloat = CGFloat(pageCount - 1)

    private var currentPage: Int {
        min(Self.pageCount - 1, max(0, Int(pagePosition.rounded())))
    }

    /// One character, three faces: welcoming → focused → excited.
    /// Index maps 1:1 to the onboarding page.
    private static let mascotImageNames: [String] = [
        "MascotIntro",
        "MascotRoutine",
        "MascotReady",
    ]

    private let titles: [String] = [
        "mockjuice",
        "5 a day",
        "ready when you are",
    ]

    private let subtitles: [String] = [
        "your smoothie-powered driving theory companion",
        "daily practice across all 5 categories builds calm, steady confidence.",
        "submit your test date and we'll pace your practice leading up to it",
    ]

    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            GeometryReader { proxy in
                let width = proxy.size.width

                VStack(spacing: 0) {
                    Spacer(minLength: 8)

                    textPager(width: width)
                        .frame(height: 372)

                    pageIndicator
                        .padding(.top, 20)
                        .opacity(entered ? 1 : 0)
                        .animation(.easeOut(duration: 0.2).delay(0.25), value: entered)

                    Spacer(minLength: 16)

                    mascotBlock
                }
                .frame(width: width, height: proxy.size.height)
                .contentShape(Rectangle())
                .gesture(swipeGesture(width: width))
            }
            .safeAreaInset(edge: .bottom, spacing: 0) {
                continueButton
            }
        }
        .onChange(of: currentPage) { _, newValue in
            var transaction = Transaction(animation: nil)
            transaction.disablesAnimations = true
            withTransaction(transaction) {
                displayedPage = newValue
            }
        }
    }

    // MARK: - Paging

    private func swipeGesture(width: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 6)
            .onChanged { value in
                let start = dragStartPosition ?? pagePosition
                if dragStartPosition == nil { dragStartPosition = start }

                let raw = start - value.translation.width / max(1, width)
                // Soft rubber-band beyond the first/last page.
                if raw < 0 {
                    pagePosition = raw * 0.3
                } else if raw > Self.lastPage {
                    pagePosition = Self.lastPage + (raw - Self.lastPage) * 0.3
                } else {
                    pagePosition = raw
                }
            }
            .onEnded { value in
                let start = dragStartPosition ?? pagePosition
                dragStartPosition = nil

                let predicted = value.predictedEndTranslation.width / max(1, width)
                var target = Int(start.rounded())
                if predicted < -0.22 {
                    target = Int(start.rounded(.down)) + 1
                } else if predicted > 0.22 {
                    target = Int(start.rounded(.up)) - 1
                }
                target = min(Self.pageCount - 1, max(0, target))

                withAnimation(.timingCurve(0.2, 0.8, 0.2, 1.0, duration: 0.5)) {
                    pagePosition = CGFloat(target)
                }
            }
    }

    private func textPager(width: CGFloat) -> some View {
        HStack(alignment: .top, spacing: 0) {
            ForEach(0..<Self.pageCount, id: \.self) { index in
                textColumn(
                    title: titles[index],
                    subtitle: subtitles[index],
                    showsChips: index == 1
                )
                .frame(width: width, alignment: .top)
            }
        }
        .frame(width: width, alignment: .leading)
        .offset(x: -pagePosition * width)
        .frame(width: width, alignment: .leading)
        .clipped()
    }

    private func textColumn(
        title: String,
        subtitle: String,
        showsChips: Bool
    ) -> some View {
        VStack(spacing: 22) {
            AppLogoView(height: 150)
                .accessibilityHidden(true)
                .offset(y: entered ? 0 : -20)
                .opacity(entered ? 1 : 0)
                .animation(.spring(response: 0.15, dampingFraction: 0.72), value: entered)

            VStack(spacing: 12) {
                Text(title)
                    .font(.mjRounded(.largeTitle, weight: .black))
                    .tracking(-0.5)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                    .multilineTextAlignment(.center)
                    .offset(y: entered ? 0 : 12)
                    .opacity(entered ? 1 : 0)
                    .animation(.easeOut(duration: 0.2).delay(0.1), value: entered)

                Text(subtitle)
                    .font(.mjRounded(.title3, weight: .bold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.spring)
                    .multilineTextAlignment(.center)
                    .fixedSize(horizontal: false, vertical: true)
                    .offset(y: entered ? 0 : 12)
                    .opacity(entered ? 1 : 0)
                    .animation(.easeOut(duration: 0.2).delay(0.25), value: entered)

                if showsChips {
                    CategoryChipRow()
                        .padding(.top, 4)
                        // Fades with the swipe so it belongs to page two only.
                        .opacity(Double(max(0, 1 - min(1, abs(pagePosition - 1) * 1.6))))
                }
            }
        }
        .padding(.horizontal, 32)
        .frame(maxHeight: .infinity, alignment: .top)
    }

    /// Shared mascot + road: it never gets torn down or re-animated, it simply
    /// drives forward as `pagePosition` changes.
    private var mascotBlock: some View {
        VStack(spacing: 10) {
            Text("ready for the road")
                .font(.mjRounded(.subheadline, weight: .black))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)
                .opacity(Double(max(0, min(1, pagePosition - 1))))

            MascotRoadScene(
                progress: max(0, min(1, pagePosition / Self.lastPage)),
                signalStage: displayedPage,
                mascotImage: Self.mascotImageNames[displayedPage]
            )
            .frame(height: 150)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 4)
        .offset(x: entered ? 0 : -30)
        .opacity(entered ? 1 : 0)
        .animation(.easeOut(duration: 0.25).delay(0.35), value: entered)
        .onAppear { entered = true }
    }

    private var pageIndicator: some View {
        HStack(spacing: 8) {
            ForEach(0..<Self.pageCount, id: \.self) { index in
                Capsule()
                    .fill(index == currentPage ? MJTheme.cardinal : MJTheme.deepForest.opacity(0.28))
                    .frame(width: index == currentPage ? 26 : 8, height: 8)
                    .animation(.easeOut(duration: 0.25), value: currentPage)
            }
        }
    }

    /// Pinned CTA. Rendered as a bottom safe-area inset so the page content
    /// lays out inside the space above the button.
    private var continueButton: some View {
        Button {
            if currentPage < Self.pageCount - 1 {
                withAnimation(.timingCurve(0.2, 0.8, 0.2, 1.0, duration: 0.5)) {
                    pagePosition = CGFloat(currentPage + 1)
                }
            } else {
                withAnimation(.easeOut(duration: 0.3)) {
                    dismissAction()
                }
            }
        } label: {
            Text(currentPage == Self.pageCount - 1 ? "let's drive!" : "next")
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
                .shadow(color: MJTheme.cardinal.opacity(0.35), radius: 12, y: 6)
        }
        .buttonStyle(MJPressScaleButtonStyle())
        .padding(.horizontal, 32)
        .padding(.top, 12)
        .padding(.bottom, 28)
        .background(MJTheme.cartonCream)
        .sensoryFeedback(.impact(weight: .light), trigger: currentPage)
    }
}

// MARK: - Category chips (page 2)

/// The five words printed on the side of the juice carton, cycling one at a time
/// so the user passively absorbs the categories.
private struct CategoryChipRow: View {
    private struct Chip: Identifiable {
        let id: Int
        let title: String
        let symbol: String
    }

    private let chips: [Chip] = [
        Chip(id: 0, title: "theory", symbol: "text.book.closed.fill"),
        Chip(id: 1, title: "highway code", symbol: "road.lanes"),
        Chip(id: 2, title: "road signs", symbol: "exclamationmark.triangle.fill"),
        Chip(id: 3, title: "mock test", symbol: "list.clipboard.fill"),
        Chip(id: 4, title: "explore", symbol: "safari.fill"),
    ]

    @State private var activeIndex: Int = 0

    var body: some View {
        HStack(spacing: 6) {
            ForEach(chips) { chip in
                let isActive = chip.id == activeIndex

                VStack(spacing: 5) {
                    Image(systemName: chip.symbol)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(isActive ? MJTheme.innocentWhite : MJTheme.spring.opacity(0.55))
                        .frame(width: 30, height: 30)
                        .background(
                            Circle()
                                .fill(isActive ? MJTheme.cardinal : MJTheme.spring.opacity(0.15))
                        )

                    Text(chip.title)
                        .font(.mjRounded(size: 10, weight: .bold))
                        .tracking(-0.1)
                        .foregroundStyle(isActive ? MJTheme.deepForest : MJTheme.spring.opacity(0.6))
                        .lineLimit(1)
                        .minimumScaleFactor(0.75)
                }
                .frame(maxWidth: .infinity)
                .scaleEffect(isActive ? 1.0 : 0.94)
                .animation(.easeInOut(duration: 0.35), value: activeIndex)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("theory, practical, prep, confidence, excellence")
        .task {
            while !Task.isCancelled {
                try? await Task.sleep(for: .milliseconds(1100))
                if Task.isCancelled { return }
                activeIndex = (activeIndex + 1) % chips.count
            }
        }
    }
}

// MARK: - Mascot scene

/// The mockjuice mascot (apple character in a small car) travelling along a road
/// toward the traffic light. `progress` (0...1) is driven continuously by the
/// swipe, so the car tracks the finger and the road dashes scroll faster for
/// parallax. `signalStage` lights the traffic light red → amber → green.
private struct MascotRoadScene: View {
    let progress: CGFloat
    let signalStage: Int
    let mascotImage: String

    var body: some View {
        GeometryReader { proxy in
            let width = proxy.size.width
            let carWidth = min(170, width * 0.52)
            let signalLane: CGFloat = 52
            let travel = max(0, width - carWidth - signalLane)

            ZStack(alignment: .bottomLeading) {
                horizonGlow(width: width)
                    .frame(width: width, height: proxy.size.height, alignment: .bottomTrailing)

                roadStrip(width: width)

                AppleCarMascot(width: carWidth, imageName: mascotImage)
                    .offset(x: travel * progress, y: -14)

                TrafficLightMarker(stage: signalStage)
                    .frame(width: 34, height: 84)
                    .offset(x: width - 34, y: -18)
            }
            .frame(width: width, height: proxy.size.height, alignment: .bottomLeading)
        }
        .accessibilityHidden(true)
    }

    /// Soft distance/horizon wash behind the traffic light.
    private func horizonGlow(width: CGFloat) -> some View {
        Ellipse()
            .fill(
                LinearGradient(
                    colors: [
                        MJTheme.spring.opacity(0.16),
                        MJTheme.spring.opacity(0.04),
                        Color.clear,
                    ],
                    startPoint: .bottomTrailing,
                    endPoint: .topLeading
                )
            )
            .frame(width: min(240, width * 0.7), height: 120)
            .offset(x: 30, y: 34)
            .blur(radius: 12)
    }

    private func roadStrip(width: CGFloat) -> some View {
        ZStack {
            RoundedRectangle(cornerRadius: 9, style: .continuous)
                .fill(MJTheme.roadAsphalt)

            HStack(spacing: 14) {
                ForEach(0..<max(1, Int(width / 30) + 4), id: \.self) { _ in
                    Capsule()
                        .fill(MJTheme.roadMarking)
                        .frame(width: 16, height: 3)
                }
            }
            .frame(width: width, alignment: .leading)
            // Dashes travel further than the car for a parallax speed cue.
            .offset(x: -progress * 90)
            .frame(width: width, alignment: .leading)
            .clipped()
        }
        .frame(width: width, height: 22)
    }
}

/// The mockjuice mascot artwork: the red apple character riding in its green car.
private struct AppleCarMascot: View {
    let width: CGFloat
    /// Expression asset for the current page; swaps instantly on page change.
    let imageName: String

    /// Intrinsic aspect ratio of the mascot artwork (700 x 536).
    private let aspectRatio: CGFloat = 700 / 536

    var body: some View {
        Image(imageName)
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: width, height: width / aspectRatio)
            .accessibilityHidden(true)
    }
}

/// Traffic light at the end of the road. Mirrors page progress exactly:
/// red on page 1, amber on page 2, green on page 3.
private struct TrafficLightMarker: View {
    let stage: Int

    private let red = MJTheme.trafficRed
    private let amber = MJTheme.trafficAmber
    private let green = MJTheme.trafficGreen

    var body: some View {
        VStack(spacing: 0) {
            VStack(spacing: 4) {
                lamp(red, isOn: stage == 0)
                lamp(amber, isOn: stage == 1)
                lamp(green, isOn: stage == 2)
            }
            .padding(4)
            .background(
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .fill(MJTheme.deepForest)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 7, style: .continuous)
                    .stroke(MJTheme.deepForest.opacity(0.35), lineWidth: 1)
            )

            Capsule()
                .fill(MJTheme.deepForest.opacity(0.7))
                .frame(width: 4)
        }
        .frame(maxHeight: .infinity, alignment: .top)
        .animation(.easeOut(duration: 0.3), value: stage)
    }

    private func lamp(_ color: Color, isOn: Bool) -> some View {
        Circle()
            .fill(isOn ? color : color.opacity(0.18))
            .frame(width: 10, height: 10)
            .shadow(color: isOn ? color.opacity(0.85) : .clear, radius: 5)
    }
}
