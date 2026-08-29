import SwiftUI

struct LiquidProgressBar: View {
    let progress: Double
    var height: CGFloat = 20
    var foregroundColor: Color = MJTheme.cardinal
    var backgroundColor: Color = MJTheme.locked.opacity(0.3)

    var body: some View {
        GeometryReader { geometry in
            let width = geometry.size.width
            let fillWidth = width * min(max(progress, 0), 1)

            ZStack(alignment: .leading) {
                Capsule()
                    .fill(backgroundColor)

                Capsule()
                    .fill(foregroundColor)
                    .frame(width: max(fillWidth, 0))
            }
        }
        .frame(height: height)
    }
}
