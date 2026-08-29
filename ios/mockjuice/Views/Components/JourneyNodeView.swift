import SwiftUI

struct JourneyNodeView: View {
    let node: JourneyNode
    let isUnlocked: Bool
    let score: Int
    let isActive: Bool
    let action: () -> Void

    /// Theory is the app's flagship node, so it swaps the red circle for a
    /// road-colored glass circle that blends into the map itself — every
    /// other node keeps the original red-circle badge treatment.
    private var usesStickerStyle: Bool { node == .theory }

    var body: some View {
        Button(action: action) {
            if usesStickerStyle {
                stickerBadge
            } else {
                standardBadge
            }
        }
        .buttonStyle(.plain)
        .disabled(!isUnlocked)
    }

    /// Each category owns its own hue (see `DESIGN.md`) so the five nodes are
    /// distinguishable at a glance. Locked nodes keep the neutral treatment.
    private var badgeFill: Color {
        isUnlocked ? node.categoryColor : MJTheme.locked
    }

    private var badgeForeground: Color {
        isUnlocked ? node.categoryForeground : MJTheme.innocentWhite
    }

    private var standardBadge: some View {
        ZStack {
            Circle()
                .fill(badgeFill)
                .frame(width: 70, height: 70)
                .overlay {
                    // Keeps the cream `explore` node legible against the cream
                    // screen background, and adds definition to every other hue.
                    Circle()
                        .stroke(MJTheme.deepForest.opacity(0.15), lineWidth: 1.5)
                }
                .shadow(color: MJTheme.deepForest.opacity(isUnlocked ? 0.22 : 0.1), radius: isUnlocked ? 8 : 4, y: 3)

            VStack(spacing: 3) {
                nodeIcon

                if isUnlocked && score > 0 {
                    Text("\(score)%")
                        .font(.mjRounded(.caption2, weight: .black))
                        .foregroundStyle(badgeForeground.opacity(0.9))
                }
            }
        }
    }

    /// A circle tinted with the road's dark forest green at 60-70% opacity
    /// so the road lines barely show through it, letting the badge sit
    /// visually integrated into the map instead of floating above it. The
    /// book glyph is inset proportionally so the ring around it stays even.
    private var stickerBadge: some View {
        ZStack {
            Circle()
                .fill((isUnlocked ? MJTheme.deepForest : MJTheme.locked).opacity(isUnlocked ? 0.65 : 0.55))
                .frame(width: 78, height: 78)
                .shadow(color: MJTheme.deepForest.opacity(isUnlocked ? 0.25 : 0.1), radius: 8, x: 0, y: 4)
                .overlay {
                    Circle()
                        .stroke(MJTheme.innocentWhite.opacity(isUnlocked ? 0.25 : 0.15), lineWidth: 1.5)
                        .frame(width: 78, height: 78)
                }

            if isUnlocked {
                Image(node.icon)
                    .resizable()
                    .renderingMode(.template)
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 58, height: 58)
                    .foregroundStyle(MJTheme.innocentWhite)
            } else {
                Image(systemName: "lock.fill")
                    .font(.system(size: 26, weight: .bold))
                    .foregroundStyle(MJTheme.innocentWhite.opacity(0.8))
            }

            if isUnlocked && score > 0 {
                Text("\(score)%")
                    .font(.mjRounded(.caption2, weight: .black))
                    .foregroundStyle(MJTheme.innocentWhite)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(Capsule().fill(MJTheme.deepForest))
                    .overlay(Capsule().stroke(MJTheme.innocentWhite.opacity(0.2), lineWidth: 1))
                    .offset(x: 26, y: 26)
            }
        }
    }

    private var nodeIcon: some View {
        let iconName = isUnlocked ? node.icon : "lock.fill"
        let isAsset = UIImage(named: iconName) != nil

        return Group {
            if isAsset {
                Image(iconName)
                    .resizable()
                    .renderingMode(.template)
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 30, height: 30)
                    .foregroundStyle(badgeForeground)
            } else {
                Image(systemName: iconName)
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(badgeForeground)
            }
        }
    }
}

struct JourneyNodeLabel: View {
    let text: String
    let isUnlocked: Bool

    var body: some View {
        Text(text)
            .font(.mjRounded(.caption, weight: .heavy))
            .tracking(-0.2)
            .textCase(.lowercase)
            .foregroundStyle(MJTheme.deepForest.opacity(isUnlocked ? 1 : 0.5))
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .background(Capsule().fill(MJTheme.innocentWhite.opacity(0.85)))
    }
}
