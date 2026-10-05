import SwiftUI

struct HomeSceneView: View {
    var body: some View {
        GeometryReader { geo in
            ForestPathIllustration()
                .frame(width: geo.size.width, height: geo.size.height)
                .clipped()
        }
        .ignoresSafeArea()
    }
}
